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

#: Default tolerance used when checking whether a quaternion is unit-norm.
#: Pass a custom *tolerance* to :func:`normalize_quaternion` to override.
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
    tolerance: float = _UNIT_NORM_TOLERANCE,
) -> tuple[float, float, float, float]:
    """Return a sign-canonical, unit-norm quaternion from (w, x, y, z).

    Unit-norm check
    ~~~~~~~~~~~~~~~
    When *allow_renormalization* is ``False`` (the default) the input is
    expected to be unit-norm within *tolerance*; a :exc:`ValueError` is raised
    if it is not.  This keeps validation strict so that callers cannot silently
    pass bad data.

    When *allow_renormalization* is ``True`` the quaternion is divided by its
    norm before being returned.  This is useful when dealing with numerical
    drift or external inputs that may have accumulated small floating-point
    errors.  The *tolerance* parameter controls how close to 1.0 the squared
    norm must be before rescaling is skipped.

    Sign canonicalization
    ~~~~~~~~~~~~~~~~~~~~~
    Because ``q`` and ``-q`` represent the same SU(2) element, the function
    enforces a unique representative by negating the quaternion whenever
    ``w < 0``.  This guarantees:

    * deterministic output — the same rotation always produces the same tuple,
    * stable comparisons — callers can use ``==`` instead of checking ``±q``.

    The sign flip is applied *after* renormalization.

    Args:
        w: Real (scalar) component.
        x: i-component.
        y: j-component.
        z: k-component.
        allow_renormalization: If ``True``, rescale to unit norm instead of
            raising on a non-unit input.
        tolerance: Maximum allowed deviation of ``‖q‖²`` from 1.0 before the
            quaternion is considered non-unit.  Defaults to ``1e-9``.

    Returns:
        A ``(w, x, y, z)`` tuple satisfying ``‖q‖ = 1`` and ``w ≥ 0``.

    Raises:
        ValueError: If the quaternion is not unit-norm and
            *allow_renormalization* is ``False``.
        ValueError: If the quaternion is the zero vector (cannot be
            normalized regardless of *allow_renormalization*).
    """
    norm_sq = w * w + x * x + y * y + z * z

    if abs(norm_sq - 1.0) > tolerance:
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
        w, x, y, z = w / norm, x / norm, y / norm, z / norm

    # Sign canonicalization: enforce w >= 0 so that q and -q collapse to the
    # same representative.
    if w < 0.0:
        w, x, y, z = -w, -x, -y, -z

    return (w, x, y, z)
