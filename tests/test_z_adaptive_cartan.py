import math

import numpy as np

from rqm_compiler import (
    AdaptiveCartanPolicy,
    Circuit,
    CompilationWorkBudget,
    optimize_circuit,
    verify_equivalence,
)
from rqm_compiler.su4_blocks import _window_unitary


def _profitable_window() -> Circuit:
    circuit = Circuit(2)
    for index in range(9):
        circuit.rzz(0, 1, 0.11 + index * 0.01)
        circuit.rx(0, 0.03 + index * 0.001)
        circuit.ry(1, -0.02 - index * 0.001)
    return circuit


def test_safe_policy_performs_no_kak() -> None:
    optimized, report = optimize_circuit(
        _profitable_window(), adaptive_policy=AdaptiveCartanPolicy.safe()
    )
    assert report.adaptive_routing["kak_invocations"] == 0
    assert all(operation.gate != "su4q" for operation in optimized.operations)


def test_selective_policy_emits_proof_carried_internal_window() -> None:
    policy = AdaptiveCartanPolicy(
        mode="selective",
        budget=CompilationWorkBudget(max_kak_windows=1, max_dense_operations=64),
    )
    source = _profitable_window()
    optimized, report = optimize_circuit(source, adaptive_policy=policy)
    assert report.adaptive_routing["kak_invocations"] == 1
    assert len(report.adaptive_routing["selected_windows"]) == 1
    block_operation = next(op for op in optimized.operations if op.gate == "su4q")
    assert block_operation.params["fallback_operations"]
    assert block_operation.params["routing"]["predicted_savings"] >= 3
    assert verify_equivalence(source, optimized).verified is True


def test_low_benefit_window_is_rejected_without_kak() -> None:
    source = Circuit(2).cx(0, 1).cx(0, 1).rzz(0, 1, math.pi / 7)
    policy = AdaptiveCartanPolicy(
        mode="selective",
        budget=CompilationWorkBudget(max_kak_windows=4, max_dense_operations=256),
    )
    optimized, report = optimize_circuit(source, adaptive_policy=policy)
    assert report.adaptive_routing["kak_invocations"] == 0
    assert not report.adaptive_routing["selected_windows"]
    assert all(operation.gate != "su4q" for operation in optimized.operations)


def test_exact_rotation_inverse_cancels_without_kak() -> None:
    source = Circuit(2).rzz(0, 1, 0.25).rzz(0, 1, -0.25)
    optimized, report = optimize_circuit(
        source, adaptive_policy=AdaptiveCartanPolicy.safe()
    )
    assert len(optimized.operations) == 0
    assert report.adaptive_routing["kak_invocations"] == 0


def test_balanced_and_aggressive_quotas_are_deterministic() -> None:
    balanced = AdaptiveCartanPolicy.balanced(1024)
    aggressive = AdaptiveCartanPolicy.aggressive(1024)
    assert balanced.budget.max_kak_windows == 16
    assert aggressive.budget.max_kak_windows == 64


def test_two_qubit_window_uses_qiskit_little_endian_order() -> None:
    angle = 0.37
    rx = np.asarray(
        [
            [math.cos(angle / 2), -1j * math.sin(angle / 2)],
            [-1j * math.sin(angle / 2), math.cos(angle / 2)],
        ],
        dtype=np.complex128,
    )
    q0_rotation = Circuit(2).rx(0, angle)
    assert np.allclose(
        _window_unitary(q0_rotation.operations, (0, 1)),
        np.kron(np.eye(2), rx),
        atol=1e-12,
        rtol=0.0,
    )
    q0_controls_q1 = Circuit(2).cx(0, 1)
    expected_cx = np.asarray(
        [[1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 1, 0, 0]],
        dtype=np.complex128,
    )
    assert np.array_equal(
        _window_unitary(q0_controls_q1.operations, (0, 1)),
        expected_cx,
    )
