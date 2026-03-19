"""Tests for Circuit construction and builder API."""

import math
import pytest

from rqm_compiler import Circuit, Operation


def test_circuit_creation():
    c = Circuit(3)
    assert c.num_qubits == 3
    assert len(c) == 0


def test_circuit_invalid_num_qubits():
    with pytest.raises(ValueError):
        Circuit(0)
    with pytest.raises(ValueError):
        Circuit(-1)


def test_circuit_add_returns_self():
    c = Circuit(1)
    op = Operation(gate="x", targets=[0])
    result = c.add(op)
    assert result is c


def test_circuit_add_wrong_type():
    c = Circuit(1)
    with pytest.raises(TypeError):
        c.add({"gate": "x"})  # type: ignore[arg-type]


def test_circuit_add_ops():
    c = Circuit(2)
    c.add(Operation(gate="h", targets=[0]))
    c.add(Operation(gate="cx", targets=[1], controls=[0]))
    assert len(c) == 2
    ops = c.operations
    assert ops[0].gate == "h"
    assert ops[1].gate == "cx"


def test_builder_single_qubit_gates():
    c = Circuit(1)
    c.i(0).x(0).y(0).z(0).h(0).s(0).t(0)
    gates = [op.gate for op in c.operations]
    assert gates == ["i", "x", "y", "z", "h", "s", "t"]


def test_builder_parametric_gates():
    c = Circuit(1)
    angle = math.pi / 2
    c.rx(0, angle).ry(0, angle).rz(0, angle).phaseshift(0, angle)
    for op in c.operations:
        assert op.params["angle"] == angle
        assert op.targets == [0]


def test_builder_u1q_identity():
    """Identity quaternion (w=1, x=y=z=0) should be accepted."""
    c = Circuit(1)
    c.u1q(0, 1.0, 0.0, 0.0, 0.0)
    op = c.operations[0]
    assert op.gate == "u1q"
    assert op.targets == [0]
    assert op.params == {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}


def test_builder_u1q_x_pi_rotation():
    """Quaternion for 180° rotation about X: (0, 1, 0, 0)."""
    c = Circuit(1)
    c.u1q(0, 0.0, 1.0, 0.0, 0.0)
    op = c.operations[0]
    assert op.gate == "u1q"
    assert op.params["x"] == 1.0


def test_builder_u1q_general():
    """General unit quaternion with all non-zero components."""
    c = Circuit(1)
    c.u1q(0, 0.5, 0.5, 0.5, 0.5)
    op = c.operations[0]
    assert op.params == {"w": 0.5, "x": 0.5, "y": 0.5, "z": 0.5}


def test_builder_two_qubit_gates():
    c = Circuit(2)
    c.cx(0, 1).cy(0, 1).cz(0, 1)
    for op in c.operations:
        assert op.controls == [0]
        assert op.targets == [1]


def test_builder_swap():
    c = Circuit(2)
    c.swap(0, 1)
    op = c.operations[0]
    assert op.gate == "swap"
    assert op.targets == [0, 1]
    assert op.controls == []


def test_builder_iswap():
    c = Circuit(2)
    c.iswap(0, 1)
    op = c.operations[0]
    assert op.gate == "iswap"


def test_builder_measure_default_key():
    c = Circuit(2)
    c.measure(0).measure(1)
    assert c.operations[0].params["key"] == "m0"
    assert c.operations[1].params["key"] == "m1"


def test_builder_measure_custom_key():
    c = Circuit(1)
    c.measure(0, key="result")
    assert c.operations[0].params["key"] == "result"


def test_builder_barrier_explicit():
    c = Circuit(3)
    c.barrier(0, 2)
    op = c.operations[0]
    assert op.gate == "barrier"
    assert op.targets == [0, 2]


def test_builder_barrier_all_qubits():
    c = Circuit(3)
    c.barrier()
    op = c.operations[0]
    assert op.targets == [0, 1, 2]


def test_to_descriptors_shape():
    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    descriptors = c.to_descriptors()
    assert len(descriptors) == 2
    for d in descriptors:
        assert "gate" in d
        assert "targets" in d
        assert "controls" in d
        assert "params" in d


def test_circuit_repr():
    c = Circuit(2)
    c.h(0)
    assert "Circuit(num_qubits=2, ops=1)" in repr(c)


def test_operations_returns_copy():
    """Mutating the returned list must not affect the circuit."""
    c = Circuit(2)
    c.h(0)
    ops = c.operations
    ops.clear()
    assert len(c) == 1
