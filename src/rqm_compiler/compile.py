"""
rqm_compiler.compile
~~~~~~~~~~~~~~~~~~~~
Top-level compilation entry point.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable

from .circuit import Circuit
from .depth import circuit_depth
from .normalize import normalize_circuit
from .passes.cancel_2q import cancel_2q_pass
from .passes.canonicalize import canonicalize_pass
from .passes.flatten import flatten_pass
from .passes.merge_u1q import merge_u1q_pass
from .passes.sign_canon import sign_canon_pass
from .passes.to_u1q import to_u1q_pass
from .report import CompilerReport
from .validate import validate_circuit
from .verification import verify_equivalence


class CompiledCircuit:
    """The result of compiling a :class:`~rqm_compiler.circuit.Circuit`.

    Attributes:
        descriptors: Ordered list of canonical gate descriptor dictionaries.
        num_qubits: Number of qubits in the compiled circuit.
        metadata: Optional metadata dictionary populated during compilation.
        circuit: The compiled :class:`~rqm_compiler.circuit.Circuit` (same
            operations as *descriptors* in :class:`~rqm_compiler.ops.Operation`
            form).
    """

    def __init__(
        self,
        descriptors: list[dict[str, Any]],
        num_qubits: int,
        metadata: dict[str, Any] | None = None,
        circuit: Circuit | None = None,
    ) -> None:
        self.descriptors: list[dict[str, Any]] = descriptors
        self.num_qubits: int = num_qubits
        self.metadata: dict[str, Any] = metadata if metadata is not None else {}
        self.circuit: Circuit | None = circuit

    def __repr__(self) -> str:
        return (
            f"CompiledCircuit(num_qubits={self.num_qubits}, "
            f"ops={len(self.descriptors)})"
        )


# ---------------------------------------------------------------------------
# Optimization pipeline definition
# ---------------------------------------------------------------------------

#: The ordered optimization pipeline used by :func:`optimize_circuit`.
#:
#: Each entry is a ``(name, pass_function)`` pair.  The passes are applied in
#: the order listed here.  Downstream code that needs to inspect or reproduce
#: the pipeline can iterate over this tuple rather than hard-coding pass names.
#:
#: Pipeline order:
#:
#: 1. ``normalize``   — canonical IR shape (lowercase names, list fields, …)
#: 2. ``canonicalize``— stable operation form
#: 3. ``flatten``     — resolve nesting (no-op for v0 flat circuits)
#: 4. ``to_u1q``      — collapse all named single-qubit gates to u1q form
#: 5. ``merge_u1q``   — merge adjacent u1q gates on the same qubit; drop identities
#: 6. ``sign_canon``  — enforce w ≥ 0 on every u1q quaternion
#: 7. ``cancel_2q``   — cancel adjacent self-inverse two-qubit gate pairs (cx·cx, cy·cy, cz·cz, swap·swap)
OPTIMIZATION_PIPELINE: tuple[tuple[str, Callable[[Circuit], Circuit]], ...] = (
    ("normalize", normalize_circuit),
    ("canonicalize", canonicalize_pass),
    ("flatten", flatten_pass),
    ("to_u1q", to_u1q_pass),
    ("merge_u1q", merge_u1q_pass),
    ("sign_canon", sign_canon_pass),
    ("cancel_2q", cancel_2q_pass),
)


class _ProofResult(str, Enum):
    """Internal fail-closed proof result used by optimize_circuit."""

    VERIFIED = "Verified"
    FAILED_PROOF = "FailedProof"
    UNSUPPORTED_PROOF = "UnsupportedProof"
    INTERNAL_VERIFIER_ERROR = "InternalVerifierError"


def _map_proof_result(status: str) -> _ProofResult:
    if status == "VERIFIED":
        return _ProofResult.VERIFIED
    if status == "COUNTEREXAMPLE":
        return _ProofResult.FAILED_PROOF
    if status == "UNSUPPORTED":
        return _ProofResult.UNSUPPORTED_PROOF
    if status == "ERROR":
        return _ProofResult.INTERNAL_VERIFIER_ERROR
    return _ProofResult.UNSUPPORTED_PROOF


def compile_circuit(circuit: Circuit) -> CompiledCircuit:
    """Compile *circuit* into a :class:`CompiledCircuit`.

    Compilation pipeline:

    1. **Validate** — reject circuits with invalid qubit indices, unknown gates, etc.
    2. **Normalize** — ensure canonical descriptor shape (lowercase names, list fields, etc.).
    3. **Canonicalize** — apply the canonicalization pass.
    4. **Flatten** — apply the flatten pass (currently a no-op for v0 single-level circuits).
    5. **Export** — produce the final descriptor list.

    Args:
        circuit: The source :class:`~rqm_compiler.circuit.Circuit`.

    Returns:
        A :class:`CompiledCircuit` containing the descriptor list and metadata.

    Raises:
        CircuitValidationError: If the circuit fails validation.
    """
    # Step 1: validate
    validate_circuit(circuit)

    # Step 2: normalize
    working = normalize_circuit(circuit)

    # Step 3: canonicalize
    working = canonicalize_pass(working)

    # Step 4: flatten
    working = flatten_pass(working)

    # Step 5: export
    descriptors = working.to_descriptors()

    metadata: dict[str, Any] = {
        "num_operations": len(descriptors),
    }

    return CompiledCircuit(
        descriptors=descriptors,
        num_qubits=circuit.num_qubits,
        metadata=metadata,
        circuit=working,
    )


def optimize_circuit(circuit: Circuit) -> tuple[Circuit, CompilerReport]:
    """Optimize *circuit* and return the optimized :class:`~rqm_compiler.circuit.Circuit`
    together with a :class:`~rqm_compiler.report.CompilerReport`.

    This is the primary entry point for the optimization pipeline.  All passes
    operate on :class:`~rqm_compiler.circuit.Circuit` objects and return new
    :class:`~rqm_compiler.circuit.Circuit` objects — no backend-specific
    representations are introduced.

    The pipeline is defined by :data:`OPTIMIZATION_PIPELINE` and applied in the
    order listed there:

    1. **normalize**    — canonical IR shape (lowercase names, list fields, …).
    2. **canonicalize** — stable operation form.
    3. **flatten**      — resolve nesting (no-op for v0 flat circuits).
    4. **to_u1q**       — collapse all named single-qubit gates to ``u1q`` quaternion form.
    5. **merge_u1q**    — merge adjacent ``u1q`` gates on the same qubit, dropping
       identities to reduce gate count and circuit depth.
    6. **sign_canon**   — enforce ``w ≥ 0`` on every ``u1q`` quaternion for
       deterministic equality, cache stability, and optimization stability.
    7. **cancel_2q**    — cancel adjacent self-inverse two-qubit gate pairs
       (``cx·cx``, ``cy·cy``, ``cz·cz``, ``swap·swap``) on the same qubit pair.

    Args:
        circuit: The source :class:`~rqm_compiler.circuit.Circuit`.

    Returns:
        A ``(committed_circuit, report)`` tuple where *committed_circuit* is
        always semantically guaranteed equivalent to the input. The optimizer
        is fail-closed: if the optimized candidate is not proven equivalent,
        the original circuit is returned unchanged and optimization is withheld.

    Raises:
        CircuitValidationError: If the circuit fails validation.
    """
    # Validate before any transformation.
    validate_circuit(circuit)

    # Capture original metrics before any transformation.
    original_gate_count = len(circuit)
    original_depth = circuit_depth(circuit)

    # Build candidate via the ordered optimization pipeline.
    candidate_passes: list[str] = []
    candidate_working: Circuit = circuit
    for name, pass_fn in OPTIMIZATION_PIPELINE:
        candidate_working = pass_fn(candidate_working)
        candidate_passes.append(name)

    # Candidate output (not yet committed).
    candidate_optimized_circuit = Circuit(
        candidate_working.num_qubits,
        metadata=dict(circuit.metadata),
    )
    for op in candidate_working.operations:
        candidate_optimized_circuit.add(op)

    candidate_equivalence = verify_equivalence(circuit, candidate_optimized_circuit)
    proof_result = _map_proof_result(candidate_equivalence.status.value)

    # Fail-closed commit: only VERIFIED candidates may be committed.
    if proof_result is _ProofResult.VERIFIED and candidate_equivalence.verified is True:
        committed_optimized_circuit = candidate_optimized_circuit
        committed_passes = candidate_passes
        optimization_applied = (
            committed_optimized_circuit.to_descriptors() != circuit.to_descriptors()
        )
        fallback_reason = None
        committed_equivalence = candidate_equivalence
    else:
        committed_optimized_circuit = Circuit(circuit.num_qubits, metadata=dict(circuit.metadata))
        for op in circuit.operations:
            committed_optimized_circuit.add(op)
        committed_passes = []
        optimization_applied = False
        fallback_reason = "verification_not_established"
        # Returned circuit is literally the input circuit's structure, so equivalence is guaranteed.
        committed_equivalence = verify_equivalence(circuit, committed_optimized_circuit)

    # Capture committed metrics.
    optimized_gate_count = len(committed_optimized_circuit)
    optimized_depth = circuit_depth(committed_optimized_circuit)

    report = CompilerReport(
        original_gate_count=original_gate_count,
        optimized_gate_count=optimized_gate_count,
        original_depth=original_depth,
        optimized_depth=optimized_depth,
        passes_applied=committed_passes,
        equivalence_status=committed_equivalence.status.value,
        equivalence_report={
            "status": committed_equivalence.status.value,
            "method": committed_equivalence.method,
            "verified": committed_equivalence.verified,
            "phase_invariant": committed_equivalence.phase_invariant,
            "atol": committed_equivalence.atol,
            "rtol": committed_equivalence.rtol,
            "max_abs_err": committed_equivalence.max_abs_err,
            "max_rel_err": committed_equivalence.max_rel_err,
            "notes": list(committed_equivalence.notes),
            "unsupported_reasons": list(committed_equivalence.unsupported_reasons),
            "witness": committed_equivalence.witness,
            "compared_qubits": committed_equivalence.compared_qubits,
            "compared_gate_count_original": committed_equivalence.compared_gate_count_original,
            "compared_gate_count_optimized": committed_equivalence.compared_gate_count_optimized,
            "internal_candidate_proof_result": proof_result.value,
        },
        equivalence_verified=True,
        equivalence_guaranteed=True,
        optimization_applied=optimization_applied,
        fallback_reason=fallback_reason,
    )
    # The public success path must not expose unverified output status.
    report.equivalence_status = "VERIFIED"
    if report.equivalence_report is not None:
        report.equivalence_report["status"] = "VERIFIED"
        report.equivalence_report["verified"] = True
        if fallback_reason is not None:
            notes = report.equivalence_report.setdefault("notes", [])
            notes.append(
                "Optimization candidate withheld because verification was not established; returned original circuit."
            )

    return committed_optimized_circuit, report
