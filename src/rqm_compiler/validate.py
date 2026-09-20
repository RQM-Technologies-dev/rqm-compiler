"""
rqm_compiler.validate
~~~~~~~~~~~~~~~~~~~~~
Circuit and operation validation.
"""

from __future__ import annotations

import math
from numbers import Integral
from typing import Any, Iterable

from .circuit import Circuit
from .descriptors import (
    PARAMETRIC_SINGLE_QUBIT_GATES,
    PARAMETRIC_TWO_QUBIT_GATES,
    SINGLE_QUBIT_GATES,
    SUPPORTED_GATES,
    TWO_QUBIT_GATES,
)
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
    _validate_qubit_count(n)
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
    if num_qubits is not None:
        _validate_qubit_count(num_qubits)
    op = Operation.from_descriptor(descriptor)
    _validate_operation(op, num_qubits=num_qubits, op_index=None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_qubit_count(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
        raise CircuitValidationError("num_qubits must be a positive integer.")


def _finite_real(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def validate_observable_query(
    circuit: Circuit, pauli: str | Iterable[str], *, max_terms: int,
) -> tuple[str, ...]:
    """Validate before routing, including empty circuits and cheap invariants.

    Return materialized symbols so one-shot iterables are consumed only once.
    Measurement remains valid circuit IR, but is not a unitary-query input.
    """
    validate_circuit(circuit)
    if isinstance(max_terms, bool) or not isinstance(max_terms, Integral) or max_terms < 1:
        raise ValueError("max_terms must be a finite positive integer.")
    try:
        labels = tuple(pauli)
    except TypeError as exc:
        raise TypeError("Pauli observable must be a string or iterable of symbols.") from exc
    if len(labels) != circuit.num_qubits:
        raise ValueError("Pauli string length must equal circuit.num_qubits")
    if any(not isinstance(label, str) or label not in ("I", "X", "Y", "Z") for label in labels):
        raise ValueError("Pauli string may contain only I, X, Y, Z")
    if any(op.gate == "measure" for op in circuit.operations):
        raise ValueError("Observable evaluator requires a unitary circuit")
    return labels

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

    for role, indices in (("target", op.targets), ("control", op.controls)):
        if any(isinstance(q, bool) or not isinstance(q, Integral) for q in indices):
            raise CircuitValidationError(f"{prefix}: {role} indices must be integers (not bool).")
        if any(q < 0 for q in indices):
            raise CircuitValidationError(f"{prefix}: {role} qubit index is out of range (must be non-negative).")
        if len(set(indices)) != len(indices):
            raise CircuitValidationError(f"{prefix}: duplicate {role} qubit indices are not allowed.")

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

    controlled_gates = {"cx", "cy", "cz"}
    symmetric_two_target_gates = (
        TWO_QUBIT_GATES - controlled_gates
    ) | set(PARAMETRIC_TWO_QUBIT_GATES)
    single_target_gates = SINGLE_QUBIT_GATES | set(PARAMETRIC_SINGLE_QUBIT_GATES) | {"measure"}

    if op.controls and op.gate == "u1q":
        raise CircuitValidationError(
            f"{prefix}: controlled 'u1q' is not supported; refusing to discard "
            "a phase that may become observable under coherent control."
        )

    if op.controls and op.gate not in controlled_gates:
        raise CircuitValidationError(
            f"{prefix}: controls are only supported for {sorted(controlled_gates)}; "
            f"gate {op.gate!r} must not carry controls."
        )

    if op.gate in controlled_gates:
        if len(op.controls) != 1 or len(op.targets) != 1:
            raise CircuitValidationError(
                f"{prefix}: controlled gate {op.gate!r} requires exactly one control and one target."
            )
    elif op.gate in symmetric_two_target_gates:
        if len(op.targets) != 2:
            raise CircuitValidationError(
                f"{prefix}: gate {op.gate!r} requires exactly two targets."
            )
    elif op.gate in single_target_gates:
        if len(op.targets) != 1:
            raise CircuitValidationError(
                f"{prefix}: gate {op.gate!r} requires exactly one target."
            )

    # Measurement must have a key param.
    if op.gate == "measure":
        if "key" not in op.params:
            raise CircuitValidationError(
                f"{prefix}: 'measure' operation must include a 'key' in params."
            )

    # Parametric single-qubit gates must have all required params.
    if op.gate in PARAMETRIC_SINGLE_QUBIT_GATES:
        required = PARAMETRIC_SINGLE_QUBIT_GATES[op.gate]
        for param_name in required:
            if param_name not in op.params:
                raise CircuitValidationError(
                    f"{prefix}: gate {op.gate!r} requires param {param_name!r}."
                )

    if op.gate in PARAMETRIC_TWO_QUBIT_GATES:
        required = PARAMETRIC_TWO_QUBIT_GATES[op.gate]
        for param_name in required:
            if param_name not in op.params:
                raise CircuitValidationError(
                    f"{prefix}: gate {op.gate!r} requires param {param_name!r}."
                )

    if op.gate in {"rx", "ry", "rz", "phaseshift", "rxx", "ryy", "rzz"}:
        angle = op.params.get("angle")
        if not _finite_real(angle):
            raise CircuitValidationError(f"{prefix}: angle must be a finite real number.")

    if op.gate == "su4q":
        from rqm_entanglement import QuaternionCartanBlock

        payload = op.params.get("block")
        if not isinstance(payload, dict):
            raise CircuitValidationError(f"{prefix}: block must be a JSON-compatible object.")
        try:
            block = QuaternionCartanBlock.from_dict(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise CircuitValidationError(f"{prefix}: invalid quaternion-Cartan block: {exc}") from exc
        if not block.validate()["valid"]:
            raise CircuitValidationError(f"{prefix}: quaternion-Cartan block validation failed.")

    # u1q gates must represent a unit quaternion: w² + x² + y² + z² = 1.
    if op.gate == "u1q":
        w = op.params.get("w", 0.0)
        x = op.params.get("x", 0.0)
        y = op.params.get("y", 0.0)
        z = op.params.get("z", 0.0)
        if not all(_finite_real(value) for value in (w, x, y, z)):
            raise CircuitValidationError(f"{prefix}: u1q components must be finite real numbers.")
        norm = math.hypot(w, x, y, z)
        norm_sq = norm * norm
        if abs(norm_sq - 1.0) > 1e-9:
            raise CircuitValidationError(
                f"{prefix}: u1q quaternion (w={w}, x={x}, y={y}, z={z}) is not unit "
                f"(\u2016q\u2016\u00b2 = {norm_sq:.6g}, expected 1)."
            )
