"""Tests for roundtrip stability: circuit → descriptors → circuit → descriptors."""

import math
import json
import pytest

from rqm_compiler import Circuit, compile_circuit
from rqm_compiler.io import circuit_to_dict, circuit_from_dict
from rqm_compiler.ops import Operation


def _build_bell_circuit() -> Circuit:
    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0, key="m0")
    c.measure(1, key="m1")
    return c


def _build_full_gate_circuit() -> Circuit:
    c = Circuit(4)
    c.i(0)
    c.x(0)
    c.y(1)
    c.z(2)
    c.h(3)
    c.s(0)
    c.t(1)
    c.rx(0, math.pi / 2)
    c.ry(1, math.pi / 4)
    c.rz(2, math.pi)
    c.phaseshift(3, math.pi / 8)
    c.cx(0, 1)
    c.cy(1, 2)
    c.cz(2, 3)
    c.swap(0, 3)
    c.iswap(1, 2)
    c.measure(0, key="m0")
    c.measure(1, key="m1")
    c.measure(2, key="m2")
    c.measure(3, key="m3")
    return c


# ---------------------------------------------------------------------------
# compile_circuit roundtrip
# ---------------------------------------------------------------------------

def test_bell_circuit_compiles():
    c = _build_bell_circuit()
    compiled = compile_circuit(c)
    assert compiled.num_qubits == 2
    assert len(compiled.descriptors) == 4


def test_compiled_descriptor_schema():
    c = _build_bell_circuit()
    compiled = compile_circuit(c)
    for d in compiled.descriptors:
        assert "gate" in d
        assert "targets" in d
        assert "controls" in d
        assert "params" in d
        assert isinstance(d["gate"], str)
        assert isinstance(d["targets"], list)
        assert isinstance(d["controls"], list)
        assert isinstance(d["params"], dict)


def test_compiled_descriptors_lowercase_gates():
    c = Circuit(1)
    # Manually add uppercase gate (bypasses builder normalisation)
    c.add(Operation(gate="H", targets=[0]))
    compiled = compile_circuit(c)
    assert compiled.descriptors[0]["gate"] == "h"


def test_full_gate_circuit_compiles():
    c = _build_full_gate_circuit()
    compiled = compile_circuit(c)
    assert compiled.num_qubits == 4
    assert len(compiled.descriptors) == len(c.operations)


def test_compile_circuit_is_deterministic():
    c = _build_bell_circuit()
    compiled_a = compile_circuit(c)
    compiled_b = compile_circuit(c)
    assert compiled_a.descriptors == compiled_b.descriptors


def test_compiled_circuit_metadata():
    c = _build_bell_circuit()
    compiled = compile_circuit(c)
    assert compiled.metadata["num_operations"] == len(compiled.descriptors)


# ---------------------------------------------------------------------------
# IO serialization roundtrip: circuit → dict → circuit → descriptors
# ---------------------------------------------------------------------------

def test_circuit_to_dict_shape():
    c = _build_bell_circuit()
    data = circuit_to_dict(c)
    assert data["num_qubits"] == 2
    assert len(data["operations"]) == 4


def test_circuit_to_dict_is_json_serializable():
    c = _build_bell_circuit()
    data = circuit_to_dict(c)
    serialized = json.dumps(data)
    assert isinstance(serialized, str)


def test_circuit_from_dict_roundtrip():
    c = _build_bell_circuit()
    data = circuit_to_dict(c)
    restored = circuit_from_dict(data)
    assert restored.num_qubits == c.num_qubits
    assert len(restored) == len(c)
    assert restored.to_descriptors() == c.to_descriptors()


def test_full_circuit_io_roundtrip():
    c = _build_full_gate_circuit()
    data = circuit_to_dict(c)
    restored = circuit_from_dict(data)
    assert restored.to_descriptors() == c.to_descriptors()


def test_compile_after_io_roundtrip():
    """A circuit that survives dict serialization should still compile correctly."""
    c = _build_bell_circuit()
    data = circuit_to_dict(c)
    restored = circuit_from_dict(data)
    compiled_original = compile_circuit(c)
    compiled_restored = compile_circuit(restored)
    assert compiled_original.descriptors == compiled_restored.descriptors


# ---------------------------------------------------------------------------
# compile_circuit rejects invalid circuits
# ---------------------------------------------------------------------------

def test_compile_rejects_invalid_circuit():
    from rqm_compiler.validate import CircuitValidationError
    c = Circuit(1)
    c.add(Operation(gate="h", targets=[5]))  # qubit 5 out of range for 1-qubit circuit
    with pytest.raises(CircuitValidationError):
        compile_circuit(c)


# ---------------------------------------------------------------------------
# u1q gate: quaternion-form single-qubit unitary
# ---------------------------------------------------------------------------

def test_u1q_compiles():
    """u1q with a valid unit quaternion should compile without error."""
    c = Circuit(1)
    c.u1q(0, 1.0, 0.0, 0.0, 0.0)  # identity quaternion
    compiled = compile_circuit(c)
    assert compiled.num_qubits == 1
    assert len(compiled.descriptors) == 1
    d = compiled.descriptors[0]
    assert d["gate"] == "u1q"
    assert d["targets"] == [0]
    assert d["params"] == {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}


def test_u1q_descriptor_schema():
    """Compiled u1q descriptor must have the canonical four fields."""
    c = Circuit(1)
    c.u1q(0, 0.5, 0.5, 0.5, 0.5)
    compiled = compile_circuit(c)
    d = compiled.descriptors[0]
    assert {"gate", "targets", "controls", "params"} <= d.keys()
    assert isinstance(d["params"], dict)
    assert set(d["params"]) == {"w", "x", "y", "z"}


def test_u1q_io_roundtrip():
    """u1q gate must survive circuit → dict → circuit → descriptors roundtrip."""
    c = Circuit(1)
    c.u1q(0, 0.5, 0.5, 0.5, 0.5)
    data = circuit_to_dict(c)
    restored = circuit_from_dict(data)
    assert restored.to_descriptors() == c.to_descriptors()


def test_u1q_rejects_non_unit_quaternion():
    """compile_circuit must reject a u1q op whose quaternion is not unit."""
    from rqm_compiler.validate import CircuitValidationError
    c = Circuit(1)
    c.add(Operation(gate="u1q", targets=[0], params={"w": 0.0, "x": 0.0, "y": 0.0, "z": 0.0}))
    with pytest.raises(CircuitValidationError, match="not unit"):
        compile_circuit(c)


# ---------------------------------------------------------------------------
# Circuit.from_descriptors
# ---------------------------------------------------------------------------

def test_from_descriptors_basic():
    """from_descriptors reconstructs a circuit identical to to_descriptors output."""
    c = Circuit(2)
    c.h(0).cx(0, 1).measure_all()
    descriptors = c.to_descriptors()
    restored = Circuit.from_descriptors(descriptors, num_qubits=2)
    assert restored.num_qubits == 2
    assert restored.to_descriptors() == descriptors


def test_from_descriptors_is_inverse_of_to_descriptors():
    """to_descriptors → from_descriptors → to_descriptors must be stable."""
    c = _build_full_gate_circuit()
    d1 = c.to_descriptors()
    restored = Circuit.from_descriptors(d1, num_qubits=c.num_qubits)
    d2 = restored.to_descriptors()
    assert d1 == d2


def test_from_descriptors_empty():
    """An empty descriptor list produces an empty circuit."""
    c = Circuit.from_descriptors([], num_qubits=3)
    assert c.num_qubits == 3
    assert len(c) == 0


def test_from_descriptors_single_op():
    d = [{"gate": "h", "targets": [0], "controls": [], "params": {}}]
    c = Circuit.from_descriptors(d, num_qubits=1)
    assert len(c) == 1
    assert c.operations[0].gate == "h"


def test_from_descriptors_preserves_operation_order():
    c = Circuit(2)
    c.h(0).cx(0, 1).measure(0, key="m0").measure(1, key="m1")
    descriptors = c.to_descriptors()
    restored = Circuit.from_descriptors(descriptors, num_qubits=2)
    assert [op.gate for op in restored.operations] == [op.gate for op in c.operations]


def test_from_descriptors_with_metadata():
    descriptors = [{"gate": "h", "targets": [0], "controls": [], "params": {}}]
    c = Circuit.from_descriptors(descriptors, num_qubits=1, metadata={"label": "test"})
    assert c.metadata["label"] == "test"


def test_from_descriptors_metadata_defaults_empty():
    descriptors = [{"gate": "h", "targets": [0], "controls": [], "params": {}}]
    c = Circuit.from_descriptors(descriptors, num_qubits=1)
    assert c.metadata == {}


def test_from_descriptors_compiles_cleanly():
    """A circuit built via from_descriptors must pass compile_circuit."""
    c = Circuit(2)
    c.h(0).cx(0, 1).measure_all()
    descriptors = c.to_descriptors()
    restored = Circuit.from_descriptors(descriptors, num_qubits=2)
    compiled = compile_circuit(restored)
    assert compiled.num_qubits == 2
    assert compiled.descriptors == descriptors


def test_from_descriptors_optimized_roundtrip():
    """optimize_circuit output can be reconstructed via from_descriptors."""
    from rqm_compiler import optimize_circuit
    c = Circuit(2)
    c.h(0).cx(0, 1).measure_all()
    optimized, _ = optimize_circuit(c)
    desc = optimized.to_descriptors()
    restored = Circuit.from_descriptors(desc, num_qubits=optimized.num_qubits)
    assert restored.to_descriptors() == desc


def test_from_descriptors_returns_circuit_instance():
    c = Circuit.from_descriptors([], num_qubits=1)
    assert isinstance(c, Circuit)
