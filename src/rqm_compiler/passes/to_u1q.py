"""
rqm_compiler.passes.to_u1q
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pass that collapses all single-qubit named gates to the canonical u1q form.

After this pass the only single-qubit gate in the circuit is ``u1q``, giving
an IR of the form::

    two-qubit ops  +  u1q

This is the minimal, complete, and geometrically elegant target representation
described in the Q² compiler vision.

Supported single-qubit gates (collapsed to u1q)
------------------------------------------------
* ``i``            — identity
* ``x``            — Pauli X  (π rotation around X axis)
* ``y``            — Pauli Y  (π rotation around Y axis)
* ``z``            — Pauli Z  (π rotation around Z axis)
* ``h``            — Hadamard (π rotation around (X+Z)/√2 axis)
* ``s``            — S gate   (π/2 rotation around Z axis)
* ``t``            — T gate   (π/4 rotation around Z axis)
* ``rx(angle)``    — rotation around X by *angle*
* ``ry(angle)``    — rotation around Y by *angle*
* ``rz(angle)``    — rotation around Z by *angle*
* ``phaseshift(angle)`` — phase shift (equivalent to rz up to global phase)

Quaternion convention
---------------------
A unit quaternion ``q = (w, x, y, z)`` represents the SU(2) element
``U = w·I − i(x·σ_x + y·σ_y + z·σ_z)``.  For a rotation by angle *θ* around
unit axis *(n_x, n_y, n_z)* this gives::

    w = cos(θ/2),  x = −n_x·sin(θ/2),  y = −n_y·sin(θ/2),  z = −n_z·sin(θ/2)

Passes that are not collapsed
------------------------------
Two-qubit gates (cx, cy, cz, swap, iswap), ``measure``, ``barrier``, and any
operation that is already ``u1q`` are left unchanged.
"""

from __future__ import annotations

import math
from typing import Any

from ..circuit import Circuit
from ..descriptors import CANONICAL_SINGLE_QUBIT_GATE
from ..normalize import normalize_quaternion
from ..ops import Operation

# ---------------------------------------------------------------------------
# Single-qubit gates that this pass collapses to u1q
# ---------------------------------------------------------------------------

_COLLAPSIBLE_SINGLE_QUBIT_GATES: frozenset[str] = frozenset(
    {"i", "x", "y", "z", "h", "s", "t", "rx", "ry", "rz", "phaseshift"}
)

_SQRT2_INV: float = 1.0 / math.sqrt(2.0)
_COS_PI_8: float = math.cos(math.pi / 8.0)
_SIN_PI_8: float = math.sin(math.pi / 8.0)


def _gate_to_quaternion(gate: str, params: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return the unit quaternion ``(w, x, y, z)`` for a single-qubit gate.

    Args:
        gate: Lowercase gate name.
        params: Gate parameter dict (used for parametric gates).

    Returns:
        ``(w, x, y, z)`` tuple representing a unit quaternion in SU(2).

    Raises:
        KeyError: If a required parameter is missing from *params*.
    """
    if gate == "i":
        return (1.0, 0.0, 0.0, 0.0)

    if gate == "x":
        # π rotation around X: (cos(π/2), −sin(π/2)·(1,0,0)) = (0,−1,0,0)
        return (0.0, -1.0, 0.0, 0.0)

    if gate == "y":
        # π rotation around Y: (cos(π/2), −sin(π/2)·(0,1,0)) = (0,0,−1,0)
        return (0.0, 0.0, -1.0, 0.0)

    if gate == "z":
        # π rotation around Z: (cos(π/2), −sin(π/2)·(0,0,1)) = (0,0,0,−1)
        return (0.0, 0.0, 0.0, -1.0)

    if gate == "h":
        # π rotation around (X+Z)/√2 axis: (0, −1/√2, 0, −1/√2)
        return (0.0, -_SQRT2_INV, 0.0, -_SQRT2_INV)

    if gate == "s":
        # π/2 rotation around Z: (cos(π/4), 0, 0, −sin(π/4)) = (1/√2, 0, 0, −1/√2)
        return (_SQRT2_INV, 0.0, 0.0, -_SQRT2_INV)

    if gate == "t":
        # π/4 rotation around Z: (cos(π/8), 0, 0, −sin(π/8))
        return (_COS_PI_8, 0.0, 0.0, -_SIN_PI_8)

    if gate == "rx":
        angle = params["angle"]
        return (math.cos(angle / 2.0), -math.sin(angle / 2.0), 0.0, 0.0)

    if gate == "ry":
        angle = params["angle"]
        return (math.cos(angle / 2.0), 0.0, -math.sin(angle / 2.0), 0.0)

    if gate in ("rz", "phaseshift"):
        angle = params["angle"]
        return (math.cos(angle / 2.0), 0.0, 0.0, -math.sin(angle / 2.0))

    raise ValueError(f"Internal error: unexpected gate {gate!r} in _gate_to_quaternion.")  # pragma: no cover


def to_u1q_pass(circuit: Circuit) -> Circuit:
    """Return a new circuit with all collapsible single-qubit gates converted to u1q.

    Any single-qubit gate in ``{i, x, y, z, h, s, t, rx, ry, rz, phaseshift}``
    is replaced with an equivalent ``u1q`` operation whose quaternion parameters
    represent the same SU(2) element (up to global phase, which is unobservable).

    Two-qubit gates (cx, cy, cz, swap, iswap), ``measure``, ``barrier``, and
    operations that are already ``u1q`` are passed through unchanged.

    Args:
        circuit: Source circuit (not mutated).

    Returns:
        A new :class:`~rqm_compiler.circuit.Circuit` where every single-qubit
        gate has been replaced by a ``u1q`` descriptor.

    Example::

        from rqm_compiler import Circuit
        from rqm_compiler.passes import to_u1q_pass

        c = Circuit(2)
        c.h(0).rx(0, 1.5707963).cx(0, 1)

        u1q_circuit = to_u1q_pass(c)
        # u1q_circuit now contains: u1q(0), u1q(0), cx(0,1)
    """
    out = Circuit(circuit.num_qubits)
    for op in circuit.operations:
        if op.gate in _COLLAPSIBLE_SINGLE_QUBIT_GATES:
            w, x, y, z = _gate_to_quaternion(op.gate, op.params)
            w, x, y, z = normalize_quaternion(w, x, y, z, allow_renormalization=True)
            out.add(
                Operation(
                    gate=CANONICAL_SINGLE_QUBIT_GATE,
                    targets=list(op.targets),
                    controls=list(op.controls),
                    params={"w": w, "x": x, "y": y, "z": z},
                )
            )
        else:
            out.add(op)
    return out
