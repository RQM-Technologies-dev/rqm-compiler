"""
rqm_compiler.compile
~~~~~~~~~~~~~~~~~~~~
Top-level compilation entry point.
"""

from __future__ import annotations

from typing import Any, Callable

from .circuit import Circuit
from .depth import circuit_depth
from .normalize import normalize_circuit
from .passes.canonicalize import canonicalize_pass
from .passes.flatten import flatten_pass
from .passes.merge_u1q import merge_u1q_pass
from .passes.sign_canon import sign_canon_pass
from .passes.to_u1q import to_u1q_pass
from .report import CompilerReport
from .validate import validate_circuit


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
OPTIMIZATION_PIPELINE: tuple[tuple[str, Callable[[Circuit], Circuit]], ...] = (
    ("normalize", normalize_circuit),
    ("canonicalize", canonicalize_pass),
    ("flatten", flatten_pass),
    ("to_u1q", to_u1q_pass),
    ("merge_u1q", merge_u1q_pass),
    ("sign_canon", sign_canon_pass),
)


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

    Args:
        circuit: The source :class:`~rqm_compiler.circuit.Circuit`.

    Returns:
        A ``(optimized_circuit, report)`` tuple where *optimized_circuit* is a
        new :class:`~rqm_compiler.circuit.Circuit` with the same ``num_qubits``
        and preserved ``metadata``, and *report* is a
        :class:`~rqm_compiler.report.CompilerReport` with gate-count and depth
        metrics.

    Raises:
        CircuitValidationError: If the circuit fails validation.
    """
    # Validate before any transformation.
    validate_circuit(circuit)

    # Capture original metrics before any transformation.
    original_gate_count = len(circuit)
    original_depth = circuit_depth(circuit)

    # Apply the ordered optimization pipeline.
    passes_applied: list[str] = []
    working: Circuit = circuit
    for name, pass_fn in OPTIMIZATION_PIPELINE:
        working = pass_fn(working)
        passes_applied.append(name)

    # Build the output circuit, carrying the original metadata forward.
    # This is done at the compile layer rather than inside individual passes,
    # keeping pass logic focused solely on gate transformations.
    output = Circuit(working.num_qubits, metadata=dict(circuit.metadata))
    for op in working.operations:
        output.add(op)

    # Capture optimized metrics.
    optimized_gate_count = len(output)
    optimized_depth = circuit_depth(output)

    report = CompilerReport(
        original_gate_count=original_gate_count,
        optimized_gate_count=optimized_gate_count,
        original_depth=original_depth,
        optimized_depth=optimized_depth,
        passes_applied=passes_applied,
        equivalence_verified=False,
    )

    return output, report
