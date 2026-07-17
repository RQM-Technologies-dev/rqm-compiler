"""Lower canonical ``u1q`` gates to named single-qubit gate sequences.

This pass is intended for backend-targeted export paths that cannot consume the
compiler's canonical ``u1q`` representation directly.

Policy in this module:

* Input IR may contain ``u1q`` gates.
* Output IR contains only named 1Q gates for lowered operations.
* Default decomposition is deterministic ``rz -> ry -> rz`` in circuit order.
* If the middle angle is (numerically) zero, the sequence is simplified to one
  ``rz`` with combined angle.
"""

from __future__ import annotations

import math

from rqm_core.su2 import quaternion_to_zyz

from ..circuit import Circuit
from ..ops import Operation

_ZERO_TOL: float = 1e-12


def _wrap_angle(theta: float) -> float:
    """Map angle to (-pi, pi] with deterministic zero snapping."""
    out = (theta + math.pi) % (2.0 * math.pi) - math.pi
    if math.isclose(out, -math.pi, abs_tol=_ZERO_TOL):
        out = math.pi
    if math.isclose(out, 0.0, abs_tol=_ZERO_TOL):
        out = 0.0
    return out


def _quaternion_to_zyz(
    w: float,
    x: float,
    y: float,
    z: float,
) -> tuple[float, float, float]:
    """Delegate canonical quaternion decomposition to ``rqm-core``."""
    alpha, beta, gamma = quaternion_to_zyz(w, x, y, z, atol=_ZERO_TOL)
    return _wrap_angle(alpha), _wrap_angle(beta), _wrap_angle(gamma)


def lower_u1q_named_1q_pass(circuit: Circuit) -> Circuit:
    """Lower all eligible ``u1q`` ops to named 1Q gates.

    Non-u1q operations pass through unchanged.
    """
    out = Circuit(circuit.num_qubits)
    for op in circuit.operations:
        if op.gate == "u1q" and len(op.targets) == 1 and not op.controls:
            qubit = op.targets[0]
            alpha, beta, gamma = _quaternion_to_zyz(
                op.params["w"],
                op.params["x"],
                op.params["y"],
                op.params["z"],
            )

            # Axis-aligned simplification: Rz(a) Ry(0) Rz(g) -> Rz(a+g).
            if math.isclose(beta, 0.0, abs_tol=_ZERO_TOL):
                theta = _wrap_angle(alpha + gamma)
                if not math.isclose(theta, 0.0, abs_tol=_ZERO_TOL):
                    out.add(Operation(gate="rz", targets=[qubit], params={"angle": theta}))
                continue

            # rqm-core returns angles for the matrix product
            # RZ(alpha) @ RY(beta) @ RZ(gamma).  Circuit descriptors are
            # applied sequentially to the state vector, so emit the reverse
            # order to realize that product.
            if not math.isclose(gamma, 0.0, abs_tol=_ZERO_TOL):
                out.add(Operation(gate="rz", targets=[qubit], params={"angle": gamma}))
            out.add(Operation(gate="ry", targets=[qubit], params={"angle": beta}))
            if not math.isclose(alpha, 0.0, abs_tol=_ZERO_TOL):
                out.add(Operation(gate="rz", targets=[qubit], params={"angle": alpha}))
        else:
            out.add(op)
    return out
