"""Tests for compiler passes, with emphasis on the to_u1q_pass."""

import math
import pytest

from rqm_compiler import Circuit, Operation, compile_circuit
from rqm_compiler.passes import sign_canon_pass, to_u1q_pass
from rqm_compiler.descriptors import CANONICAL_SINGLE_QUBIT_GATE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_unit(w: float, x: float, y: float, z: float, tol: float = 1e-9) -> bool:
    return abs(w * w + x * x + y * y + z * z - 1.0) <= tol


def _u1q_params(circuit: Circuit, op_index: int) -> tuple[float, float, float, float]:
    d = circuit.to_descriptors()[op_index]
    p = d["params"]
    return p["w"], p["x"], p["y"], p["z"]


# ---------------------------------------------------------------------------
# Gate identity: to_u1q_pass collapses each gate to a unit quaternion
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("build", [
    lambda c: c.i(0),
    lambda c: c.x(0),
    lambda c: c.y(0),
    lambda c: c.z(0),
    lambda c: c.h(0),
    lambda c: c.s(0),
    lambda c: c.t(0),
    lambda c: c.rx(0, math.pi / 3),
    lambda c: c.ry(0, math.pi / 4),
    lambda c: c.rz(0, math.pi / 5),
    lambda c: c.phaseshift(0, math.pi / 6),
])
def test_single_qubit_gate_collapses_to_unit_u1q(build):
    c = Circuit(1)
    build(c)
    out = to_u1q_pass(c)
    assert len(out) == 1
    d = out.to_descriptors()[0]
    assert d["gate"] == CANONICAL_SINGLE_QUBIT_GATE
    assert _is_unit(d["params"]["w"], d["params"]["x"], d["params"]["y"], d["params"]["z"])


def test_to_u1q_pass_all_named_single_qubit_gates():
    """All collapsible single-qubit gates appear in one circuit; all become u1q."""
    c = Circuit(2)
    c.i(0).x(0).y(0).z(0).h(0).s(0).t(0)
    c.rx(0, 1.0).ry(0, 1.0).rz(0, 1.0).phaseshift(0, 1.0)
    out = to_u1q_pass(c)
    assert len(out) == 11
    for d in out.to_descriptors():
        assert d["gate"] == CANONICAL_SINGLE_QUBIT_GATE
        assert _is_unit(d["params"]["w"], d["params"]["x"], d["params"]["y"], d["params"]["z"])


# ---------------------------------------------------------------------------
# Specific gate quaternion values
# ---------------------------------------------------------------------------

def test_i_quaternion_is_identity():
    c = Circuit(1)
    c.i(0)
    out = to_u1q_pass(c)
    w, x, y, z = _u1q_params(out, 0)
    assert (w, x, y, z) == (1.0, 0.0, 0.0, 0.0)


def test_x_quaternion_is_pi_rotation_around_x():
    c = Circuit(1)
    c.x(0)
    out = to_u1q_pass(c)
    w, x, y, z = _u1q_params(out, 0)
    assert math.isclose(w, 0.0, abs_tol=1e-12)
    assert math.isclose(abs(x), 1.0, rel_tol=1e-12)
    assert math.isclose(y, 0.0, abs_tol=1e-12)
    assert math.isclose(z, 0.0, abs_tol=1e-12)


def test_h_quaternion_encodes_diagonal_axis():
    """H = π rotation around (X+Z)/√2: x and z components should be ±1/√2."""
    c = Circuit(1)
    c.h(0)
    out = to_u1q_pass(c)
    w, x, y, z = _u1q_params(out, 0)
    sqrt2_inv = 1.0 / math.sqrt(2.0)
    assert math.isclose(w, 0.0, abs_tol=1e-12)
    assert math.isclose(abs(x), sqrt2_inv, rel_tol=1e-12)
    assert math.isclose(y, 0.0, abs_tol=1e-12)
    assert math.isclose(abs(z), sqrt2_inv, rel_tol=1e-12)


def test_rx_angle_zero_gives_identity_quaternion():
    c = Circuit(1)
    c.rx(0, 0.0)
    out = to_u1q_pass(c)
    w, x, y, z = _u1q_params(out, 0)
    assert math.isclose(w, 1.0, rel_tol=1e-12)
    assert math.isclose(x, 0.0, abs_tol=1e-12)


def test_rx_angle_pi_gives_x_quaternion():
    """rx(π) should agree with the X gate quaternion up to sign."""
    c_rx = Circuit(1)
    c_rx.rx(0, math.pi)
    c_x = Circuit(1)
    c_x.x(0)

    out_rx = to_u1q_pass(c_rx)
    out_x = to_u1q_pass(c_x)

    w_rx, x_rx, y_rx, z_rx = _u1q_params(out_rx, 0)
    w_x, x_x, y_x, z_x = _u1q_params(out_x, 0)

    # The two quaternions represent the same rotation (may differ by global sign ±q).
    same_or_negated = all(
        math.isclose(a, b, abs_tol=1e-9) for a, b in [(w_rx, w_x), (x_rx, x_x), (y_rx, y_x), (z_rx, z_x)]
    ) or all(
        math.isclose(a, -b, abs_tol=1e-9) for a, b in [(w_rx, w_x), (x_rx, x_x), (y_rx, y_x), (z_rx, z_x)]
    )
    assert same_or_negated


def test_phaseshift_same_quaternion_as_rz():
    """phaseshift(θ) and rz(θ) should produce the same quaternion (identical up to global phase)."""
    angle = math.pi / 3
    c_ps = Circuit(1)
    c_ps.phaseshift(0, angle)
    c_rz = Circuit(1)
    c_rz.rz(0, angle)

    out_ps = to_u1q_pass(c_ps)
    out_rz = to_u1q_pass(c_rz)

    w_ps, x_ps, y_ps, z_ps = _u1q_params(out_ps, 0)
    w_rz, x_rz, y_rz, z_rz = _u1q_params(out_rz, 0)

    assert math.isclose(w_ps, w_rz, rel_tol=1e-12)
    assert math.isclose(x_ps, x_rz, abs_tol=1e-12)
    assert math.isclose(y_ps, y_rz, abs_tol=1e-12)
    assert math.isclose(z_ps, z_rz, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# Pass-through gates (not collapsed)
# ---------------------------------------------------------------------------

def test_two_qubit_gates_are_unchanged():
    c = Circuit(2)
    c.cx(0, 1).cy(0, 1).cz(0, 1).swap(0, 1).iswap(0, 1)
    out = to_u1q_pass(c)
    for orig, result in zip(c.to_descriptors(), out.to_descriptors()):
        assert orig == result


def test_measure_and_barrier_are_unchanged():
    c = Circuit(2)
    c.barrier().measure(0, key="m0").measure(1, key="m1")
    out = to_u1q_pass(c)
    for orig, result in zip(c.to_descriptors(), out.to_descriptors()):
        assert orig == result


def test_u1q_already_passes_through_unchanged():
    """An existing u1q op should not be re-wrapped."""
    c = Circuit(1)
    c.u1q(0, 1.0, 0.0, 0.0, 0.0)
    out = to_u1q_pass(c)
    assert len(out) == 1
    d = out.to_descriptors()[0]
    assert d == c.to_descriptors()[0]


# ---------------------------------------------------------------------------
# Mixed circuit: single-qubit + two-qubit + measurement
# ---------------------------------------------------------------------------

def test_mixed_circuit_partial_collapse():
    """h, cx, measure → u1q, cx, measure."""
    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0, key="m0")
    c.measure(1, key="m1")

    out = to_u1q_pass(c)
    descriptors = out.to_descriptors()
    assert descriptors[0]["gate"] == "u1q"
    assert descriptors[1]["gate"] == "cx"
    assert descriptors[2]["gate"] == "measure"
    assert descriptors[3]["gate"] == "measure"


def test_to_u1q_does_not_mutate_original():
    c = Circuit(1)
    c.h(0)
    original_descriptors = c.to_descriptors()
    to_u1q_pass(c)
    assert c.to_descriptors() == original_descriptors


def test_to_u1q_returns_new_circuit():
    c = Circuit(1)
    c.h(0)
    out = to_u1q_pass(c)
    assert out is not c


# ---------------------------------------------------------------------------
# Compile pipeline + to_u1q_pass: the resulting circuit validates cleanly
# ---------------------------------------------------------------------------

def test_to_u1q_output_compiles():
    """The output of to_u1q_pass should be accepted by compile_circuit."""
    c = Circuit(2)
    c.h(0).cx(0, 1).measure(0, key="m0").measure(1, key="m1")
    u1q_circuit = to_u1q_pass(c)
    compiled = compile_circuit(u1q_circuit)
    assert compiled.num_qubits == 2
    assert len(compiled.descriptors) == 4


def test_to_u1q_is_deterministic():
    """to_u1q_pass must produce the same output every time."""
    c = Circuit(1)
    c.h(0).rx(0, 1.23)
    out_a = to_u1q_pass(c)
    out_b = to_u1q_pass(c)
    assert out_a.to_descriptors() == out_b.to_descriptors()


def test_to_u1q_preserves_qubit_count():
    c = Circuit(4)
    c.h(0).x(1).y(2).z(3)
    out = to_u1q_pass(c)
    assert out.num_qubits == 4


def test_to_u1q_preserves_targets():
    c = Circuit(3)
    c.h(2)
    out = to_u1q_pass(c)
    assert out.to_descriptors()[0]["targets"] == [2]


# ---------------------------------------------------------------------------
# Sign canonicalization in to_u1q_pass
# ---------------------------------------------------------------------------

def test_to_u1q_w_always_nonnegative():
    """Every u1q quaternion produced by to_u1q_pass must have w >= 0."""
    c = Circuit(1)
    c.i(0).x(0).y(0).z(0).h(0).s(0).t(0)
    c.rx(0, math.pi).ry(0, math.pi).rz(0, math.pi).phaseshift(0, math.pi)
    out = to_u1q_pass(c)
    for d in out.to_descriptors():
        assert d["params"]["w"] >= 0.0, f"w < 0 for gate: {d}"


def test_to_u1q_sign_canonicalization_q_and_minus_q_agree():
    """Equivalent gates that differ only by global quaternion sign produce the same output.

    rx(π) and x both represent a π rotation around X.  Before sign canonicalization
    they could produce (w, x, y, z) and -(w, x, y, z).  After canonicalization they
    must be identical.
    """
    c_rx = Circuit(1)
    c_rx.rx(0, math.pi)
    c_x = Circuit(1)
    c_x.x(0)

    w_rx, x_rx, y_rx, z_rx = _u1q_params(to_u1q_pass(c_rx), 0)
    w_x, x_x, y_x, z_x = _u1q_params(to_u1q_pass(c_x), 0)

    assert math.isclose(w_rx, w_x, abs_tol=1e-9)
    assert math.isclose(x_rx, x_x, abs_tol=1e-9)
    assert math.isclose(y_rx, y_x, abs_tol=1e-9)
    assert math.isclose(z_rx, z_x, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# sign_canon_pass: sign-canonicalization pass for u1q gates
# ---------------------------------------------------------------------------


def test_sign_canon_flips_negative_w():
    """A u1q with w < 0 must be negated to w > 0."""
    c = Circuit(1)
    c.u1q(0, -1.0, 0.0, 0.0, 0.0)   # w = -1 (non-canonical identity)
    out = sign_canon_pass(c)
    d = out.to_descriptors()[0]
    assert d["params"]["w"] >= 0.0
    assert math.isclose(d["params"]["w"], 1.0, rel_tol=1e-12)
    assert math.isclose(d["params"]["x"], 0.0, abs_tol=1e-12)


def test_sign_canon_preserves_positive_w():
    """A u1q with w > 0 must not be altered."""
    c = Circuit(1)
    c.u1q(0, 1.0, 0.0, 0.0, 0.0)
    out = sign_canon_pass(c)
    assert out.to_descriptors() == c.to_descriptors()


def test_sign_canon_result_is_unit():
    """After sign_canon, every u1q must still be a unit quaternion."""
    c = Circuit(1)
    c.u1q(0, -1.0, 0.0, 0.0, 0.0)
    out = sign_canon_pass(c)
    d = out.to_descriptors()[0]
    p = d["params"]
    assert _is_unit(p["w"], p["x"], p["y"], p["z"])


def test_sign_canon_all_w_nonneg_after_flip():
    """Every u1q in the output must satisfy w >= 0."""
    c = Circuit(2)
    # Manually create non-canonical quaternions (w < 0)
    c.add(Operation(gate="u1q", targets=[0], params={"w": -0.5, "x": 0.5, "y": 0.5, "z": 0.5}))
    c.add(Operation(gate="u1q", targets=[1], params={"w": -0.5, "x": -0.5, "y": -0.5, "z": -0.5}))
    out = sign_canon_pass(c)
    for d in out.to_descriptors():
        assert d["params"]["w"] >= 0.0, f"w < 0 for {d}"


def test_sign_canon_non_u1q_gates_pass_through():
    """Non-u1q gates must be unchanged by sign_canon_pass."""
    c = Circuit(2)
    c.cx(0, 1)
    c.measure(0, key="m0")
    c.barrier()
    out = sign_canon_pass(c)
    assert out.to_descriptors() == c.to_descriptors()


def test_sign_canon_does_not_mutate_input():
    c = Circuit(1)
    c.u1q(0, -1.0, 0.0, 0.0, 0.0)
    original = c.to_descriptors()
    sign_canon_pass(c)
    assert c.to_descriptors() == original


def test_sign_canon_returns_new_circuit():
    c = Circuit(1)
    c.u1q(0, 1.0, 0.0, 0.0, 0.0)
    out = sign_canon_pass(c)
    assert out is not c


def test_sign_canon_preserves_num_qubits():
    c = Circuit(5)
    out = sign_canon_pass(c)
    assert out.num_qubits == 5


def test_sign_canon_idempotent():
    """Applying sign_canon_pass twice must produce the same result as applying it once."""
    c = Circuit(1)
    c.u1q(0, -1.0, 0.0, 0.0, 0.0)
    once = sign_canon_pass(c)
    twice = sign_canon_pass(once)
    assert once.to_descriptors() == twice.to_descriptors()


def test_sign_canon_mixed_circuit():
    """A circuit with mixed gate types: only u1q gates are affected."""
    c = Circuit(2)
    c.u1q(0, -1.0, 0.0, 0.0, 0.0)   # will be flipped
    c.cx(0, 1)                          # unchanged
    c.u1q(1, 1.0, 0.0, 0.0, 0.0)    # already canonical, unchanged
    c.measure(0, key="m0")              # unchanged

    out = sign_canon_pass(c)
    descs = out.to_descriptors()

    assert descs[0]["gate"] == "u1q"
    assert descs[0]["params"]["w"] >= 0.0   # was -1 → now 1
    assert descs[1]["gate"] == "cx"
    assert descs[2]["gate"] == "u1q"
    assert descs[2]["params"]["w"] >= 0.0
    assert descs[3]["gate"] == "measure"


def test_sign_canon_after_to_u1q_all_w_nonneg():
    """to_u1q already sign-canonicalizes, so sign_canon is idempotent on its output."""
    c = Circuit(1)
    c.i(0).x(0).y(0).z(0).h(0).s(0).t(0)
    c.rx(0, math.pi).ry(0, math.pi).rz(0, math.pi)
    after_to_u1q = to_u1q_pass(c)
    after_sign_canon = sign_canon_pass(after_to_u1q)
    assert after_to_u1q.to_descriptors() == after_sign_canon.to_descriptors()
