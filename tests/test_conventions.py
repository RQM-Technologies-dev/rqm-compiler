"""Cross-package quaternion/SU(2) convention tests."""

from __future__ import annotations

import math

import numpy as np
import pytest

from rqm_core.quaternion import Quaternion
from rqm_core.su2 import quaternion_to_su2
from rqm_compiler import Circuit
from rqm_compiler.ops import Operation
from rqm_compiler.passes.to_u1q import to_u1q_pass
from rqm_compiler.verification import (
    EquivalenceStatus,
    _single_qubit_matrix,
    compare_unitaries_up_to_global_phase,
    verify_equivalence,
)


def _u1q_matrix_after_to_u1q(circuit: Circuit) -> np.ndarray:
    out = to_u1q_pass(circuit)
    descriptors = out.to_descriptors()
    assert len(descriptors) == 1
    assert descriptors[0]["gate"] == "u1q"
    p = descriptors[0]["params"]
    return quaternion_to_su2(Quaternion(p["w"], p["x"], p["y"], p["z"]))


def _verifier_matrix(op: Operation) -> np.ndarray:
    return np.asarray(_single_qubit_matrix(op), dtype=np.complex128)


def _assert_equal_up_to_global_phase(a: np.ndarray, b: np.ndarray) -> None:
    _, max_abs_err, _, _, _ = compare_unitaries_up_to_global_phase(
        a.tolist(),
        b.tolist(),
        atol=1e-9,
        rtol=1e-7,
    )
    assert max_abs_err < 1e-9


@pytest.mark.parametrize(
    ("name", "build", "expected_op", "exact_su2"),
    [
        (
            "rx",
            lambda c: c.rx(0, 0.73),
            Operation(gate="rx", targets=[0], params={"angle": 0.73}),
            True,
        ),
        (
            "ry",
            lambda c: c.ry(0, -0.41),
            Operation(gate="ry", targets=[0], params={"angle": -0.41}),
            True,
        ),
        (
            "rz",
            lambda c: c.rz(0, 1.19),
            Operation(gate="rz", targets=[0], params={"angle": 1.19}),
            True,
        ),
        ("h", lambda c: c.h(0), Operation(gate="h", targets=[0]), False),
        ("s", lambda c: c.s(0), Operation(gate="s", targets=[0]), False),
        ("t", lambda c: c.t(0), Operation(gate="t", targets=[0]), False),
        (
            "phaseshift",
            lambda c: c.phaseshift(0, 0.62),
            Operation(gate="phaseshift", targets=[0], params={"angle": 0.62}),
            False,
        ),
        (
            "u1q",
            lambda c: c.u1q(0, 0.5, 0.5, 0.5, 0.5),
            Operation(
                gate="u1q",
                targets=[0],
                params={"w": 0.5, "x": 0.5, "y": 0.5, "z": 0.5},
            ),
            True,
        ),
    ],
)
def test_to_u1q_matches_rqm_core_and_verifier_named_matrices(
    name: str,
    build,
    expected_op: Operation,
    exact_su2: bool,
) -> None:
    circuit = Circuit(1)
    build(circuit)

    u1q_matrix = _u1q_matrix_after_to_u1q(circuit)
    expected = _verifier_matrix(expected_op)

    if exact_su2:
        assert np.allclose(u1q_matrix, expected, atol=1e-9), name
    else:
        assert not np.allclose(u1q_matrix, expected, atol=1e-9), name
        _assert_equal_up_to_global_phase(u1q_matrix, expected)


@pytest.mark.parametrize(
    ("axis", "angle", "build"),
    [
        ("x", 0.73, lambda c: c.rx(0, 0.73)),
        ("y", -0.41, lambda c: c.ry(0, -0.41)),
        ("z", 1.19, lambda c: c.rz(0, 1.19)),
    ],
)
def test_compiler_axis_rotations_emit_rqm_core_axis_angle(
    axis: str,
    angle: float,
    build,
) -> None:
    circuit = Circuit(1)
    build(circuit)
    expected = quaternion_to_su2(Quaternion.from_axis_angle(axis, angle))
    assert np.allclose(_u1q_matrix_after_to_u1q(circuit), expected, atol=1e-9)


def test_rqm_circuits_metadata_uses_rqm_core_quaternion_signs() -> None:
    rqm_circuits = pytest.importorskip("rqm_circuits")

    gates = rqm_circuits.STANDARD_GATES
    assert "cos(angle/2) + i" in gates["rx"].quaternion_form
    assert "cos(angle/2) + j" in gates["ry"].quaternion_form
    assert "cos(angle/2) + k" in gates["rz"].quaternion_form
    assert "(i+k)" in gates["h"].quaternion_form
    assert "up to global phase" in gates["phaseshift"].quaternion_form


def test_q_and_minus_q_are_bloch_equivalent_not_identical_su2() -> None:
    q = Quaternion.from_axis_angle_vec((1.0, 2.0, 3.0), 0.79)
    neg_q = Quaternion(-q.w, -q.x, -q.y, -q.z)

    assert np.allclose(q.to_rotation_matrix(), neg_q.to_rotation_matrix(), atol=1e-9)
    assert not np.allclose(quaternion_to_su2(q), quaternion_to_su2(neg_q), atol=1e-9)
    _assert_equal_up_to_global_phase(quaternion_to_su2(q), quaternion_to_su2(neg_q))

    original = Circuit(1)
    original.u1q(0, q.w, q.x, q.y, q.z)
    optimized = Circuit(1)
    optimized.u1q(0, neg_q.w, neg_q.x, neg_q.y, neg_q.z)

    report = verify_equivalence(original, optimized)
    assert report.status == EquivalenceStatus.VERIFIED
    assert report.comparison["exact_su2_equality"] is False
    assert report.comparison["equal_up_to_global_phase"] is True
    assert report.comparison["so3_bloch_equivalent_quaternion_sign"] is True
