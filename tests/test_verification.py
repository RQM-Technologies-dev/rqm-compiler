"""Tests for compiler-owned semantic equivalence verification."""

from __future__ import annotations

import math

from rqm_compiler import Circuit, optimize_circuit
from rqm_compiler.ops import Operation
from rqm_compiler.verification import (
    EquivalenceMethod,
    EquivalenceStatus,
    compare_unitaries_up_to_global_phase,
    verify_equivalence,
)


def test_merge_u1q_semantics_verified():
    c = Circuit(1)
    c.h(0).h(0)
    optimized, report = optimize_circuit(c)
    assert len(optimized.operations) == 0
    assert report.equivalence_status == EquivalenceStatus.VERIFIED.value
    assert report.equivalence_report["method"] in {
        EquivalenceMethod.U1Q_CANONICAL.value,
        EquivalenceMethod.UNITARY_NUMERICAL.value,
    }
    assert report.equivalence_verified is True


def test_sign_canonical_semantics_verified_for_q_and_minus_q():
    original = Circuit(1)
    original.u1q(0, 0.5, 0.5, 0.5, 0.5)

    optimized = Circuit(1)
    optimized.u1q(0, -0.5, -0.5, -0.5, -0.5)

    report = verify_equivalence(original, optimized)
    assert report.status == EquivalenceStatus.VERIFIED
    assert report.method == EquivalenceMethod.U1Q_CANONICAL.value
    assert report.verified is True


def test_identity_pruning_verified():
    original = Circuit(1)
    original.x(0).x(0)
    optimized = Circuit(1)
    report = verify_equivalence(original, optimized)
    assert report.status == EquivalenceStatus.VERIFIED
    assert report.verified is True


def test_two_qubit_swap_swap_cancellation_verified():
    original = Circuit(2)
    original.swap(0, 1).swap(0, 1)
    optimized = Circuit(2)
    report = verify_equivalence(original, optimized)
    assert report.status == EquivalenceStatus.VERIFIED
    assert report.method == EquivalenceMethod.UNITARY_NUMERICAL.value


def test_two_qubit_cx_cx_cancellation_verified():
    original = Circuit(2)
    original.cx(0, 1).cx(0, 1)
    optimized = Circuit(2)
    report = verify_equivalence(original, optimized)
    assert report.status == EquivalenceStatus.VERIFIED


def test_global_phase_difference_is_verified():
    # rz(pi) = -i z (global phase difference only)
    original = Circuit(1)
    original.rz(0, math.pi)
    optimized = Circuit(1)
    optimized.z(0)

    report = verify_equivalence(original, optimized)
    assert report.status == EquivalenceStatus.VERIFIED


def test_dropped_gate_detects_counterexample():
    original = Circuit(1)
    original.x(0)
    optimized = Circuit(1)

    report = verify_equivalence(original, optimized)
    assert report.status == EquivalenceStatus.COUNTEREXAMPLE
    assert report.verified is False
    assert isinstance(report.witness, dict)


def test_wrong_axis_detects_counterexample():
    original = Circuit(1)
    original.rx(0, math.pi / 2)
    optimized = Circuit(1)
    optimized.ry(0, math.pi / 2)

    report = verify_equivalence(original, optimized)
    assert report.status == EquivalenceStatus.COUNTEREXAMPLE
    assert report.verified is False


def test_altered_target_detects_counterexample():
    original = Circuit(2)
    original.cx(0, 1)
    optimized = Circuit(2)
    optimized.cx(1, 0)

    report = verify_equivalence(original, optimized)
    assert report.status == EquivalenceStatus.COUNTEREXAMPLE
    assert report.verified is False


def test_unsupported_gate_is_not_counterexample():
    original = Circuit(2)
    original.iswap(0, 1)
    optimized = Circuit(2)
    optimized.iswap(0, 1)

    report = verify_equivalence(original, optimized)
    # Descriptor-identical path can still verify exactly.
    assert report.status == EquivalenceStatus.VERIFIED



def test_non_unitary_measurement_is_unverified_or_unsupported():
    original = Circuit(1)
    original.h(0).measure(0, key="m0")
    optimized = Circuit(1)
    optimized.u1q(0, 1 / math.sqrt(2), -1 / math.sqrt(2), 0.0, -1 / math.sqrt(2)).measure(0, key="m0")

    report = verify_equivalence(original, optimized)
    assert report.status in {EquivalenceStatus.UNVERIFIED, EquivalenceStatus.UNSUPPORTED}
    assert report.verified is None


def test_too_many_qubits_returns_unverified():
    c = Circuit(4)
    c.h(0).cx(0, 1).cx(1, 2).cx(2, 3)

    report = verify_equivalence(c, c, max_dense_qubits=3)
    # identical descriptors short-circuit to verified
    assert report.status == EquivalenceStatus.VERIFIED

    modified = Circuit(4)
    modified.h(0).cx(0, 1).cx(1, 2)
    report2 = verify_equivalence(c, modified, max_dense_qubits=3)
    assert report2.status == EquivalenceStatus.UNVERIFIED
    assert report2.verified is None


def test_symbolic_params_return_unsupported_or_unverified():
    c1 = Circuit(1)
    c1.add(Operation(gate="rx", targets=[0], params={"angle": "theta"}))
    c2 = Circuit(1)
    c2.add(Operation(gate="rx", targets=[0], params={"angle": "theta"}))

    report = verify_equivalence(c1, c2)
    assert report.status in {EquivalenceStatus.UNVERIFIED, EquivalenceStatus.UNSUPPORTED}
    assert report.verified is None


def test_compare_unitaries_up_to_global_phase_helper():
    u = [[1 + 0j, 0j], [0j, 1j]]
    v = [[-1j, 0j], [0j, 1 + 0j]]  # u = (i) * v
    _, max_abs_err, _, _, _ = compare_unitaries_up_to_global_phase(u, v, atol=1e-9, rtol=1e-7)
    assert max_abs_err < 1e-9


def test_optimize_report_includes_equivalence_payload():
    c = Circuit(1)
    c.x(0).x(0)
    _, report = optimize_circuit(c)

    assert report.equivalence_status == EquivalenceStatus.VERIFIED.value
    assert report.equivalence_verified is True
    payload = report.equivalence_report
    assert payload is not None
    assert payload["status"] == EquivalenceStatus.VERIFIED.value
    assert payload["verified"] is True
