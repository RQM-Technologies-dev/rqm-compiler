"""Tests for circuit normalization."""

import math
import pytest

from rqm_compiler import Circuit, Operation
from rqm_compiler.normalize import normalize_circuit, normalize_operation, normalize_descriptor, normalize_quaternion


# ---------------------------------------------------------------------------
# normalize_operation
# ---------------------------------------------------------------------------

def test_normalize_gate_name_lowercased():
    op = Operation(gate="H", targets=[0])
    # Operation.__post_init__ already lowercases, but we test normalize_operation too
    norm = normalize_operation(op)
    assert norm.gate == "h"


def test_normalize_uppercase_gate_via_raw_dict():
    """Verify normalize_descriptor lowercases the gate."""
    raw = {"gate": "RX", "targets": [0], "controls": [], "params": {"angle": 1.0}}
    norm = normalize_descriptor(raw)
    assert norm["gate"] == "rx"


def test_normalize_operation_returns_new_object():
    op = Operation(gate="x", targets=[0])
    norm = normalize_operation(op)
    assert norm is not op


def test_normalize_operation_copies_lists():
    op = Operation(gate="cx", targets=[1], controls=[0])
    norm = normalize_operation(op)
    norm.targets.append(99)
    assert op.targets == [1]  # original unchanged


def test_normalize_operation_copies_params():
    op = Operation(gate="rx", targets=[0], params={"angle": 1.0})
    norm = normalize_operation(op)
    norm.params["angle"] = 99.0
    assert op.params["angle"] == 1.0  # original unchanged


# ---------------------------------------------------------------------------
# normalize_circuit
# ---------------------------------------------------------------------------

def test_normalize_circuit_returns_new_circuit():
    c = Circuit(2)
    c.h(0)
    normed = normalize_circuit(c)
    assert normed is not c


def test_normalize_circuit_preserves_ops():
    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    normed = normalize_circuit(c)
    assert len(normed) == 2
    assert normed.operations[0].gate == "h"
    assert normed.operations[1].gate == "cx"


def test_normalize_circuit_does_not_mutate_original():
    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    original_len = len(c)
    normalize_circuit(c)
    assert len(c) == original_len


# ---------------------------------------------------------------------------
# normalize_descriptor
# ---------------------------------------------------------------------------

def test_normalize_descriptor_fills_missing_fields():
    raw = {"gate": "H"}  # missing targets, controls, params
    norm = normalize_descriptor(raw)
    assert norm["gate"] == "h"
    assert norm["targets"] == []
    assert norm["controls"] == []
    assert norm["params"] == {}


def test_normalize_descriptor_is_copy():
    raw = {"gate": "x", "targets": [0], "controls": [], "params": {}}
    norm = normalize_descriptor(raw)
    norm["targets"].append(1)
    assert raw["targets"] == [0]


# ---------------------------------------------------------------------------
# normalize_quaternion
# ---------------------------------------------------------------------------

def test_normalize_quaternion_already_unit():
    """An already-unit quaternion is returned unchanged."""
    result = normalize_quaternion(1.0, 0.0, 0.0, 0.0)
    assert result == (1.0, 0.0, 0.0, 0.0)


def test_normalize_quaternion_identity_passes():
    """Identity quaternion (1,0,0,0) must pass without allow_renormalization."""
    w, x, y, z = normalize_quaternion(1.0, 0.0, 0.0, 0.0)
    assert math.isclose(w * w + x * x + y * y + z * z, 1.0, rel_tol=1e-9)


def test_normalize_quaternion_general_unit():
    """Any unit quaternion (0.5, 0.5, 0.5, 0.5) passes through untouched."""
    result = normalize_quaternion(0.5, 0.5, 0.5, 0.5)
    assert result == (0.5, 0.5, 0.5, 0.5)


def test_normalize_quaternion_non_unit_raises_by_default():
    """Non-unit quaternion raises ValueError without allow_renormalization."""
    with pytest.raises(ValueError, match="not unit"):
        normalize_quaternion(1.0, 1.0, 0.0, 0.0)


def test_normalize_quaternion_zero_raises():
    """Zero quaternion cannot be normalized and always raises ValueError."""
    with pytest.raises(ValueError, match="zero quaternion"):
        normalize_quaternion(0.0, 0.0, 0.0, 0.0, allow_renormalization=True)


def test_normalize_quaternion_renormalization_scales_to_unit():
    """allow_renormalization=True must return a unit quaternion."""
    # (2, 0, 0, 0) has norm 2 → should return (1, 0, 0, 0)
    w, x, y, z = normalize_quaternion(2.0, 0.0, 0.0, 0.0, allow_renormalization=True)
    assert math.isclose(w * w + x * x + y * y + z * z, 1.0, rel_tol=1e-9)
    assert math.isclose(w, 1.0, rel_tol=1e-9)


def test_normalize_quaternion_renormalization_general():
    """allow_renormalization=True correctly normalizes a general vector."""
    # (1, 1, 1, 1) has norm 2
    w, x, y, z = normalize_quaternion(1.0, 1.0, 1.0, 1.0, allow_renormalization=True)
    assert math.isclose(w * w + x * x + y * y + z * z, 1.0, rel_tol=1e-9)
    assert math.isclose(w, 0.5, rel_tol=1e-9)
    assert math.isclose(x, 0.5, rel_tol=1e-9)


def test_normalize_quaternion_near_unit_passes():
    """Quaternion within 1e-9 tolerance of unit norm passes without renormalization."""
    eps = 1e-12
    result = normalize_quaternion(1.0 + eps, 0.0, 0.0, 0.0)
    assert result == (1.0 + eps, 0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Sign canonicalization
# ---------------------------------------------------------------------------

def test_normalize_quaternion_sign_canonical_negative_w_flipped():
    """When w < 0 the quaternion is negated to enforce the w >= 0 representative."""
    # (-0.5, 0.5, 0.5, 0.5) is already unit-norm; w < 0 so all components flip.
    w, x, y, z = normalize_quaternion(-0.5, 0.5, 0.5, 0.5)
    assert math.isclose(w, 0.5, rel_tol=1e-12)
    assert math.isclose(x, -0.5, rel_tol=1e-12)
    assert math.isclose(y, -0.5, rel_tol=1e-12)
    assert math.isclose(z, -0.5, rel_tol=1e-12)


def test_normalize_quaternion_sign_canonical_positive_w_unchanged():
    """When w > 0 the quaternion is returned as-is (no sign flip)."""
    w, x, y, z = normalize_quaternion(0.5, -0.5, -0.5, -0.5)
    assert math.isclose(w, 0.5, rel_tol=1e-12)
    assert math.isclose(x, -0.5, rel_tol=1e-12)
    assert math.isclose(y, -0.5, rel_tol=1e-12)
    assert math.isclose(z, -0.5, rel_tol=1e-12)


def test_normalize_quaternion_sign_canonical_zero_w_unchanged():
    """When w == 0 the quaternion is returned unchanged (no sign flip)."""
    # (0, 0, 0, 1) represents a π rotation around Z.
    w, x, y, z = normalize_quaternion(0.0, 0.0, 0.0, 1.0)
    assert w == 0.0
    assert z == 1.0


def test_normalize_quaternion_sign_canonical_q_and_minus_q_agree():
    """q and -q must map to the same canonical representative."""
    q1 = normalize_quaternion(0.5, 0.5, 0.5, 0.5)
    q2 = normalize_quaternion(-0.5, -0.5, -0.5, -0.5)
    assert q1 == q2


def test_normalize_quaternion_sign_canonical_after_renormalization():
    """Sign canonicalization is applied after renormalization."""
    # (-2, 0, 0, 0) renormalizes to (-1, 0, 0, 0), then sign flips to (1, 0, 0, 0).
    w, x, y, z = normalize_quaternion(-2.0, 0.0, 0.0, 0.0, allow_renormalization=True)
    assert math.isclose(w, 1.0, rel_tol=1e-12)
    assert math.isclose(x, 0.0, abs_tol=1e-12)
    assert math.isclose(y, 0.0, abs_tol=1e-12)
    assert math.isclose(z, 0.0, abs_tol=1e-12)


def test_normalize_quaternion_sign_canonical_general_renorm_negative_w():
    """(-1, -1, -1, -1) renormalizes then sign-flips to (0.5, 0.5, 0.5, 0.5)."""
    w, x, y, z = normalize_quaternion(-1.0, -1.0, -1.0, -1.0, allow_renormalization=True)
    assert math.isclose(w, 0.5, rel_tol=1e-12)
    assert math.isclose(x, 0.5, rel_tol=1e-12)
    assert math.isclose(y, 0.5, rel_tol=1e-12)
    assert math.isclose(z, 0.5, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# Configurable tolerance
# ---------------------------------------------------------------------------

def test_normalize_quaternion_custom_tolerance_strict_rejects_near_unit():
    """A stricter tolerance causes a slightly-off-unit quaternion to raise."""
    # w = 1 + 1e-10  →  norm_sq - 1 ≈ 2e-10  (inside default 1e-9 window)
    eps = 1e-10
    # Default tolerance (1e-9): no raise
    normalize_quaternion(1.0 + eps, 0.0, 0.0, 0.0)
    # Stricter tolerance (1e-11): norm_sq deviation ≈ 2e-10 > 1e-11 → raises
    with pytest.raises(ValueError, match="not unit"):
        normalize_quaternion(1.0 + eps, 0.0, 0.0, 0.0, tolerance=1e-11)


def test_normalize_quaternion_custom_tolerance_loose_accepts_drifted_input():
    """A looser tolerance allows a quaternion with larger accumulated drift through."""
    # norm_sq ≈ 1 + 5e-7, outside the default 1e-9 window.
    # With allow_renormalization=False but a loose tolerance it must pass.
    slightly_off = math.sqrt(1.0 + 5e-7)  # norm slightly above 1
    # Verify default raises
    with pytest.raises(ValueError):
        normalize_quaternion(slightly_off, 0.0, 0.0, 0.0)
    # With looser tolerance the same input passes and the output is unit-norm.
    w, x, y, z = normalize_quaternion(slightly_off, 0.0, 0.0, 0.0, tolerance=1e-5)
    assert math.isclose(w * w + x * x + y * y + z * z, slightly_off ** 2, rel_tol=1e-12)
