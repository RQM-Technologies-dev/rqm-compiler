"""
rqm_compiler.passes.merge_u1q
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pass that merges adjacent u1q gates on the same qubit.

After :func:`~rqm_compiler.passes.to_u1q.to_u1q_pass`, consecutive ``u1q``
gates on the same qubit can be combined into a single ``u1q`` gate whose
quaternion is the product of the individual quaternions.  When the result is
the identity rotation it is dropped entirely, reducing the gate count.

Quaternion product
------------------
For two SU(2) elements applied in sequence (q1 first, q2 second) the
combined rotation is ``q2 ⊗ q1`` where::

    (w, x, y, z) = (
        w2·w1 − x2·x1 − y2·y1 − z2·z1,
        w2·x1 + x2·w1 + y2·z1 − z2·y1,
        w2·y1 − x2·z1 + y2·w1 + z2·x1,
        w2·z1 + x2·y1 − y2·x1 + z2·w1,
    )
"""

from __future__ import annotations

import math

from ..circuit import Circuit
from ..normalize import normalize_quaternion
from ..ops import Operation

_IDENTITY_TOL: float = 1e-9


def _mul_quaternion(
    w1: float, x1: float, y1: float, z1: float,
    w2: float, x2: float, y2: float, z2: float,
) -> tuple[float, float, float, float]:
    """Return ``q2 ⊗ q1`` (apply *q1* first, then *q2*)."""
    return (
        w2 * w1 - x2 * x1 - y2 * y1 - z2 * z1,
        w2 * x1 + x2 * w1 + y2 * z1 - z2 * y1,
        w2 * y1 - x2 * z1 + y2 * w1 + z2 * x1,
        w2 * z1 + x2 * y1 - y2 * x1 + z2 * w1,
    )


def _is_identity(w: float, x: float, y: float, z: float) -> bool:
    """Return ``True`` if the quaternion is ±identity within tolerance."""
    return (
        abs(abs(w) - 1.0) <= _IDENTITY_TOL
        and math.isclose(abs(x), 0.0, abs_tol=_IDENTITY_TOL)
        and math.isclose(abs(y), 0.0, abs_tol=_IDENTITY_TOL)
        and math.isclose(abs(z), 0.0, abs_tol=_IDENTITY_TOL)
    )


def merge_u1q_pass(circuit: Circuit) -> Circuit:
    """Return a new circuit with adjacent u1q gates on the same qubit merged.

    Consecutive ``u1q`` gates on the same qubit (with no intervening gate that
    touches that qubit) are replaced by a single ``u1q`` gate whose quaternion
    is the product of the individual quaternions.  Identity results (up to
    :data:`_IDENTITY_TOL`) are dropped to further reduce the gate count.

    This pass is designed to operate on circuits that have already been through
    :func:`~rqm_compiler.passes.to_u1q.to_u1q_pass`.  Non-u1q gates and
    multi-qubit gates are passed through unchanged.

    Args:
        circuit: Source circuit (not mutated).

    Returns:
        A new :class:`~rqm_compiler.circuit.Circuit` with merged u1q gates.

    Example::

        from rqm_compiler import Circuit
        from rqm_compiler.passes import to_u1q_pass, merge_u1q_pass

        c = Circuit(1)
        c.x(0).x(0)  # two X gates → identity

        merged = merge_u1q_pass(to_u1q_pass(c))
        assert len(merged) == 0  # identity dropped
    """
    # pending[qubit] = accumulated (w, x, y, z) for a run of consecutive u1q
    # gates on that qubit, or None if there is no pending gate.
    pending: dict[int, tuple[float, float, float, float] | None] = {
        q: None for q in range(circuit.num_qubits)
    }

    output_ops: list[Operation] = []

    def _flush(qubit: int) -> None:
        """Emit the pending u1q gate for *qubit* (if any) to output_ops."""
        if pending[qubit] is None:
            return
        w, x, y, z = pending[qubit]
        pending[qubit] = None
        if not _is_identity(w, x, y, z):
            w, x, y, z = normalize_quaternion(w, x, y, z, allow_renormalization=True)
            output_ops.append(
                Operation(
                    gate="u1q",
                    targets=[qubit],
                    params={"w": w, "x": x, "y": y, "z": z},
                )
            )

    for op in circuit.operations:
        if op.gate == "u1q" and len(op.targets) == 1 and not op.controls:
            qubit = op.targets[0]
            p = op.params
            w2, x2, y2, z2 = p["w"], p["x"], p["y"], p["z"]

            if pending[qubit] is None:
                pending[qubit] = (w2, x2, y2, z2)
            else:
                w1, x1, y1, z1 = pending[qubit]
                pending[qubit] = _mul_quaternion(w1, x1, y1, z1, w2, x2, y2, z2)
        else:
            # Flush any pending u1q on qubits touched by this operation.
            for q in set(op.targets) | set(op.controls):
                _flush(q)
            output_ops.append(op)

    # Flush any pending u1q gates at the end of the circuit.
    for q in range(circuit.num_qubits):
        _flush(q)

    out = Circuit(circuit.num_qubits)
    for op in output_ops:
        out.add(op)
    return out
