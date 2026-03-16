"""
rqm_compiler.validate
~~~~~~~~~~~~~~~~~~~~~
Circuit and operation validation.
"""

from __future__ import annotations

from typing import Any

from .circuit import Circuit
from .descriptors import SUPPORTED_GATES
from .ops import Operation


class CircuitValidationError(ValueError):
    """Raised when a circuit fails validation."""


def validate_circuit(circuit: Circuit) -> None:
    """Validate *circuit* and raise :class:`CircuitValidationError` on the first problem.

    Checks performed:

    * Every target qubit index is within ``[0, num_qubits)``.
    * Every control qubit index is within ``[0, num_qubits)``.
    * No qubit index appears in both *targets* and *controls* for the same operation.
    * Gate names are in the supported canonical gate set.
    * Required params are present for parametric gates.
    * For ``measure`` operations, a ``key`` param is present.

    Args:
        circuit: The :class:`~rqm_compiler.circuit.Circuit` to validate.

    Raises:
        CircuitValidationError: If any validation rule is violated.
    """
    n = circuit.num_qubits
    for idx, op in enumerate(circuit.operations):
        _validate_operation(op, num_qubits=n, op_index=idx)


def validate_descriptor(descriptor: dict[str, Any], *, num_qubits: int | None = None) -> None:
    """Validate a single canonical descriptor dictionary.

    Args:
        descriptor: The descriptor to validate.
        num_qubits: Optional circuit qubit count; if provided, qubit indices are checked.

    Raises:
        CircuitValidationError: If any validation rule is violated.
    """
    op = Operation.from_descriptor(descriptor)
    _validate_operation(op, num_qubits=num_qubits, op_index=None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_operation(
    op: Operation,
    *,
    num_qubits: int | None,
    op_index: int | None,
) -> None:
    prefix = f"Operation[{op_index}] ({op.gate!r})" if op_index is not None else f"Gate {op.gate!r}"

    # Gate name must be a recognised canonical gate.
    if op.gate not in SUPPORTED_GATES:
        raise CircuitValidationError(
            f"{prefix}: unsupported gate name {op.gate!r}. "
            f"Supported gates: {sorted(SUPPORTED_GATES)}"
        )

    # Target list must not be empty for non-barrier operations.
    if op.gate != "barrier" and not op.targets:
        raise CircuitValidationError(f"{prefix}: targets list must not be empty.")

    # Validate qubit index bounds when num_qubits is known.
    if num_qubits is not None:
        for q in op.targets:
            if not (0 <= q < num_qubits):
                raise CircuitValidationError(
                    f"{prefix}: target qubit index {q} is out of range [0, {num_qubits})."
                )
        for q in op.controls:
            if not (0 <= q < num_qubits):
                raise CircuitValidationError(
                    f"{prefix}: control qubit index {q} is out of range [0, {num_qubits})."
                )

    # No qubit should appear in both targets and controls.
    overlap = set(op.targets) & set(op.controls)
    if overlap:
        raise CircuitValidationError(
            f"{prefix}: qubit(s) {sorted(overlap)} appear in both targets and controls."
        )

    # Measurement must have a key param.
    if op.gate == "measure":
        if "key" not in op.params:
            raise CircuitValidationError(
                f"{prefix}: 'measure' operation must include a 'key' in params."
            )

    # Parametric single-qubit gates must have an 'angle' param.
    from .descriptors import PARAMETRIC_SINGLE_QUBIT_GATES
    if op.gate in PARAMETRIC_SINGLE_QUBIT_GATES:
        required = PARAMETRIC_SINGLE_QUBIT_GATES[op.gate]
        for param_name in required:
            if param_name not in op.params:
                raise CircuitValidationError(
                    f"{prefix}: gate {op.gate!r} requires param {param_name!r}."
                )
