"""
rqm_compiler.compile
~~~~~~~~~~~~~~~~~~~~
Top-level compilation entry point.
"""

from __future__ import annotations

from typing import Any

from .circuit import Circuit
from .normalize import normalize_circuit
from .passes.canonicalize import canonicalize_pass
from .passes.flatten import flatten_pass
from .validate import validate_circuit


class CompiledCircuit:
    """The result of compiling a :class:`~rqm_compiler.circuit.Circuit`.

    Attributes:
        descriptors: Ordered list of canonical gate descriptor dictionaries.
        num_qubits: Number of qubits in the compiled circuit.
        metadata: Optional metadata dictionary populated during compilation.
    """

    def __init__(
        self,
        descriptors: list[dict[str, Any]],
        num_qubits: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.descriptors: list[dict[str, Any]] = descriptors
        self.num_qubits: int = num_qubits
        self.metadata: dict[str, Any] = metadata if metadata is not None else {}

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
    )
