"""
rqm_compiler.normalize
~~~~~~~~~~~~~~~~~~~~~~
Normalization utilities that ensure operations conform to the canonical IR shape.
"""

from __future__ import annotations

import math
from typing import Any

from .circuit import Circuit
from .ops import Operation

# Tolerance used when checking whether a quaternion is already unit-norm.
_UNIT_NORM_TOLERANCE: float = 1e-9


def normalize_operation(op: Operation) -> Operation:
    """Return a new :class:`Operation` with a fully normalised canonical shape.

    Normalisation steps:

    * Gate name is lowercased.
    * ``targets`` is guaranteed to be a list.
    * ``controls`` is guaranteed to be a list.
    * ``params`` is guaranteed to be a dict.

    The original operation is not mutated.
    """
    return Operation(
        gate=op.gate.lower(),
        targets=list(op.targets),
        controls=list(op.controls),
        params=dict(op.params),
    )


def normalize_circuit(circuit: Circuit) -> Circuit:
    """Return a new :class:`Circuit` with all operations normalised.

    The original circuit is not mutated.

    Args:
        circuit: The source circuit.

    Returns:
        A new :class:`Circuit` containing normalised copies of all operations.
    """
    normalised = Circuit(circuit.num_qubits)
    for op in circuit.operations:
        normalised.add(normalize_operation(op))
    return normalised


def normalize_descriptor(descriptor: dict[str, Any]) -> dict[str, Any]:
    """Return a normalised copy of a canonical descriptor dictionary.

    Args:
        descriptor: A raw descriptor (possibly with mixed-case gate name, etc.).

    Returns:
        A new descriptor dictionary with all fields in canonical form.
    """
    return {
        "gate": str(descriptor.get("gate", "")).lower(),
        "targets": list(descriptor.get("targets", [])),
        "controls": list(descriptor.get("controls", [])),
        "params": dict(descriptor.get("params", {})),
    }


def normalize_quaternion(
    w: float,
    x: float,
    y: float,
    z: float,
    *,
    allow_renormalization: bool = False,
) -> tuple[float, float, float, float]:
    """Return a unit-norm quaternion from (w, x, y, z).

    When *allow_renormalization* is ``False`` (the default) the input is
    expected to be unit-norm within a tolerance of ``1e-9``; a
    :exc:`ValueError` is raised if it is not.  This keeps validation strict so
    that callers cannot silently pass bad data.

    When *allow_renormalization* is ``True`` the quaternion is divided by its
    norm before being returned.  This is useful when dealing with numerical
    drift or external inputs that may have accumulated small floating-point
    errors.

    Args:
        w: Real (scalar) component.
        x: i-component.
        y: j-component.
        z: k-component.
        allow_renormalization: If ``True``, rescale to unit norm instead of
            raising on a non-unit input.

    Returns:
        A ``(w, x, y, z)`` tuple with ``‖q‖ = 1``.

    Raises:
        ValueError: If the quaternion is not unit-norm and
            *allow_renormalization* is ``False``.
        ValueError: If the quaternion is the zero vector (cannot be
            normalized regardless of *allow_renormalization*).
    """
    norm_sq = w * w + x * x + y * y + z * z
    if abs(norm_sq - 1.0) <= _UNIT_NORM_TOLERANCE:
        return (w, x, y, z)

    if not allow_renormalization:
        raise ValueError(
            f"Quaternion (w={w}, x={x}, y={y}, z={z}) is not unit "
            f"(\u2016q\u2016\u00b2 = {norm_sq:.6g}, expected 1). "
            "Pass allow_renormalization=True to rescale automatically."
        )

    norm = math.sqrt(norm_sq)
    if norm == 0.0:
        raise ValueError(
            "Cannot normalize the zero quaternion (w=0, x=0, y=0, z=0)."
        )
    return (w / norm, x / norm, y / norm, z / norm)
