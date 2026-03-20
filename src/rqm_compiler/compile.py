"""
rqm_compiler.compile
~~~~~~~~~~~~~~~~~~~~
Top-level compilation entry point.
"""

from __future__ import annotations

from typing import Any

from .circuit import Circuit
from .depth import circuit_depth
from .normalize import normalize_circuit
from .passes.canonicalize import canonicalize_pass
from .passes.flatten import flatten_pass
from .passes.merge_u1q import merge_u1q_pass
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

    Optimization pipeline:

    1. **Validate** — reject invalid circuits before any work is done.
    2. **Normalize** — ensure canonical IR shape (lowercase names, list fields).
    3. **Canonicalize** — apply the canonicalization pass.
    4. **Flatten** — resolve any nesting (no-op for v0 flat circuits).
    5. **to_u1q** — collapse all named single-qubit gates to ``u1q`` quaternion form.
    6. **merge_u1q** — merge adjacent ``u1q`` gates on the same qubit, dropping
       identities to reduce gate count and circuit depth.

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
    # Step 1: validate
    validate_circuit(circuit)

    # Capture original metrics before any transformation.
    original_gate_count = len(circuit)
    original_depth = circuit_depth(circuit)

    passes_applied: list[str] = []

    # Step 2: normalize
    working = normalize_circuit(circuit)
    passes_applied.append("normalize")

    # Step 3: canonicalize
    working = canonicalize_pass(working)
    passes_applied.append("canonicalize")

    # Step 4: flatten
    working = flatten_pass(working)
    passes_applied.append("flatten")

    # Step 5: collapse named single-qubit gates to u1q quaternion form.
    working = to_u1q_pass(working)
    passes_applied.append("to_u1q")

    # Step 6: merge adjacent u1q gates on the same qubit (reduces gate count).
    working = merge_u1q_pass(working)
    passes_applied.append("merge_u1q")

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
