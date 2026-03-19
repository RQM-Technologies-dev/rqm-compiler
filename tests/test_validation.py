"""Tests for circuit validation logic."""

import math
import pytest

from rqm_compiler import Circuit, Operation
from rqm_compiler.validate import validate_circuit, validate_descriptor, CircuitValidationError


# ---------------------------------------------------------------------------
# Valid circuits should pass without error
# ---------------------------------------------------------------------------

def test_valid_simple_circuit():
    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0, key="m0")
    c.measure(1, key="m1")
    validate_circuit(c)  # should not raise


def test_valid_parametric_gates():
    c = Circuit(1)
    c.rx(0, math.pi / 2)
    validate_circuit(c)


def test_valid_barrier():
    c = Circuit(3)
    c.barrier(0, 1, 2)
    validate_circuit(c)


def test_valid_barrier_no_qubits():
    c = Circuit(2)
    c.barrier()
    validate_circuit(c)


# ---------------------------------------------------------------------------
# Invalid qubit indices
# ---------------------------------------------------------------------------

def test_invalid_target_qubit_too_high():
    c = Circuit(2)
    c.add(Operation(gate="h", targets=[2]))  # valid qubits: 0, 1
    with pytest.raises(CircuitValidationError, match="out of range"):
        validate_circuit(c)


def test_invalid_target_qubit_negative():
    c = Circuit(2)
    c.add(Operation(gate="x", targets=[-1]))
    with pytest.raises(CircuitValidationError, match="out of range"):
        validate_circuit(c)


def test_invalid_control_qubit_too_high():
    c = Circuit(2)
    c.add(Operation(gate="cx", targets=[0], controls=[3]))
    with pytest.raises(CircuitValidationError, match="out of range"):
        validate_circuit(c)


# ---------------------------------------------------------------------------
# Overlapping control and target
# ---------------------------------------------------------------------------

def test_overlapping_control_target():
    c = Circuit(2)
    c.add(Operation(gate="cx", targets=[0], controls=[0]))
    with pytest.raises(CircuitValidationError, match="appear in both"):
        validate_circuit(c)


# ---------------------------------------------------------------------------
# Unknown gate
# ---------------------------------------------------------------------------

def test_unknown_gate():
    c = Circuit(1)
    c.add(Operation(gate="toffoli", targets=[0]))
    with pytest.raises(CircuitValidationError, match="unsupported gate"):
        validate_circuit(c)


# ---------------------------------------------------------------------------
# Missing required params
# ---------------------------------------------------------------------------

def test_rx_missing_angle():
    c = Circuit(1)
    c.add(Operation(gate="rx", targets=[0], params={}))
    with pytest.raises(CircuitValidationError, match="requires param 'angle'"):
        validate_circuit(c)


def test_measure_missing_key():
    c = Circuit(1)
    c.add(Operation(gate="measure", targets=[0], params={}))
    with pytest.raises(CircuitValidationError, match="must include a 'key'"):
        validate_circuit(c)


# ---------------------------------------------------------------------------
# u1q: quaternion-form gate
# ---------------------------------------------------------------------------

def test_u1q_valid_identity_quaternion():
    """Identity quaternion (w=1) should pass validation."""
    c = Circuit(1)
    c.u1q(0, 1.0, 0.0, 0.0, 0.0)
    validate_circuit(c)  # must not raise


def test_u1q_valid_x_rotation_pi():
    """Quaternion (0,1,0,0) represents a 180° rotation about X."""
    c = Circuit(1)
    c.u1q(0, 0.0, 1.0, 0.0, 0.0)
    validate_circuit(c)


def test_u1q_valid_general_unit_quaternion():
    """Quaternion (0.5, 0.5, 0.5, 0.5) is unit."""
    c = Circuit(1)
    c.u1q(0, 0.5, 0.5, 0.5, 0.5)
    validate_circuit(c)


def test_u1q_invalid_zero_quaternion():
    """Zero quaternion is not unit and must be rejected."""
    c = Circuit(1)
    c.add(Operation(gate="u1q", targets=[0], params={"w": 0.0, "x": 0.0, "y": 0.0, "z": 0.0}))
    with pytest.raises(CircuitValidationError, match="not unit"):
        validate_circuit(c)


def test_u1q_invalid_non_unit_quaternion():
    """Non-unit quaternion (w=1, x=1) has ‖q‖²=2 and must be rejected."""
    c = Circuit(1)
    c.add(Operation(gate="u1q", targets=[0], params={"w": 1.0, "x": 1.0, "y": 0.0, "z": 0.0}))
    with pytest.raises(CircuitValidationError, match="not unit"):
        validate_circuit(c)


def test_u1q_missing_param():
    """Missing a quaternion component param must be rejected."""
    c = Circuit(1)
    c.add(Operation(gate="u1q", targets=[0], params={"w": 1.0, "x": 0.0, "y": 0.0}))
    with pytest.raises(CircuitValidationError, match="requires param 'z'"):
        validate_circuit(c)


# ---------------------------------------------------------------------------
# Empty targets
# ---------------------------------------------------------------------------

def test_empty_targets_non_barrier():
    c = Circuit(2)
    c.add(Operation(gate="h", targets=[]))
    with pytest.raises(CircuitValidationError, match="targets list must not be empty"):
        validate_circuit(c)


# ---------------------------------------------------------------------------
# validate_descriptor
# ---------------------------------------------------------------------------

def test_validate_descriptor_valid():
    d = {"gate": "h", "targets": [0], "controls": [], "params": {}}
    validate_descriptor(d, num_qubits=1)


def test_validate_descriptor_invalid_index():
    d = {"gate": "h", "targets": [5], "controls": [], "params": {}}
    with pytest.raises(CircuitValidationError, match="out of range"):
        validate_descriptor(d, num_qubits=3)


def test_validate_descriptor_without_num_qubits():
    """Without num_qubits, qubit bounds are not checked."""
    d = {"gate": "h", "targets": [999], "controls": [], "params": {}}
    validate_descriptor(d)  # should not raise
