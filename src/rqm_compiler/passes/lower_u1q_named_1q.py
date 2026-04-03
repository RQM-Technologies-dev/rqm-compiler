"""Lower canonical ``u1q`` gates to named single-qubit gate sequences.

This pass is intended for backend-targeted export paths that cannot consume the
compiler's canonical ``u1q`` representation directly.

Policy in this module:

* Input IR may contain ``u1q`` gates.
* Output IR contains only named 1Q gates for lowered operations.
* Default decomposition is deterministic ``rz -> ry -> rz``.
* If the middle angle is (numerically) zero, the sequence is simplified to one
  ``rz`` with combined angle.
"""

from __future__ import annotations

import cmath
import math
from typing import Callable

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


def _quaternion_to_zyz_fallback(
    w: float,
    x: float,
    y: float,
    z: float,
) -> tuple[float, float, float]:
    """Return deterministic ``(alpha, beta, gamma)`` for ``Rz(alpha)Ry(beta)Rz(gamma)``.

    This fallback is used only when a reusable helper is not available from
    ``rqm-core``.
    """
    # SU(2) matrix from quaternion convention used by this compiler:
    # U = w I - i(xX + yY + zZ)
    a = complex(w, -z)
    c = complex(y, -x)

    beta = 2.0 * math.atan2(abs(c), abs(a))
    beta = _wrap_angle(beta)

    if math.isclose(abs(beta), 0.0, abs_tol=_ZERO_TOL):
        # Pure Z rotation (up to global phase): choose alpha=0 deterministically.
        alpha = 0.0
        gamma = _wrap_angle(-2.0 * cmath.phase(a))
        return alpha, 0.0, gamma

    if math.isclose(abs(abs(beta) - math.pi), 0.0, abs_tol=1e-10):
        # cos(beta/2)=0 branch; choose gamma=0 deterministically.
        alpha = _wrap_angle(2.0 * cmath.phase(c))
        return alpha, math.pi, 0.0

    phase_a = cmath.phase(a)
    phase_c = cmath.phase(c)
    alpha = _wrap_angle(phase_c - phase_a)
    gamma = _wrap_angle(-(phase_a + phase_c))
    return alpha, _wrap_angle(beta), gamma


def _resolve_rqm_core_decomposer() -> Callable[[float, float, float, float], tuple[float, float, float]] | None:
    """Return an ``rqm-core`` decomposition helper if available."""
    candidate_imports = (
        ("rqm_core.su2", "quaternion_to_zyz"),
        ("rqm_core.su2", "u1q_to_zyz"),
        ("rqm_core.quaternion", "quaternion_to_zyz"),
    )

    for module_name, symbol_name in candidate_imports:
        try:
            module = __import__(module_name, fromlist=[symbol_name])
            fn = getattr(module, symbol_name)
            if callable(fn):
                return fn
        except Exception:
            continue
    return None


def _quaternion_to_zyz(
    w: float,
    x: float,
    y: float,
    z: float,
) -> tuple[float, float, float]:
    """Delegate to ``rqm-core`` if available, else use deterministic fallback."""
    core_decomposer = _resolve_rqm_core_decomposer()
    if core_decomposer is not None:
        alpha, beta, gamma = core_decomposer(w, x, y, z)
        return _wrap_angle(alpha), _wrap_angle(beta), _wrap_angle(gamma)
    return _quaternion_to_zyz_fallback(w, x, y, z)


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

            if not math.isclose(alpha, 0.0, abs_tol=_ZERO_TOL):
                out.add(Operation(gate="rz", targets=[qubit], params={"angle": alpha}))
            out.add(Operation(gate="ry", targets=[qubit], params={"angle": beta}))
            if not math.isclose(gamma, 0.0, abs_tol=_ZERO_TOL):
                out.add(Operation(gate="rz", targets=[qubit], params={"angle": gamma}))
        else:
            out.add(op)
    return out
