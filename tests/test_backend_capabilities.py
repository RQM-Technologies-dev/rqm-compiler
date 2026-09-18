import pytest
from rqm_compiler import (
 BackendCapabilityModel,Circuit,get_backend_capability_model,lower_circuit_for_backend,
)

def test_initial_capability_models_are_public_and_gate_model():
 for name in ("qiskit","braket_gate_model","pennylane"):
  m=get_backend_capability_model(name)
  assert isinstance(m,BackendCapabilityModel)
  assert m.modality=="gate_model"
  assert "u1q" in m.internal_operations_requiring_materialization
  assert {"rxx","ryy","rzz"} <= m.structured_operations

def test_braket_capability_preserves_existing_lowering_output():
 c=Circuit(1);c.u1q(0,.9238795325,0,0,-.3826834324)
 lowered=lower_circuit_for_backend(c,backend_family="braket_gate_model")
 assert all(op.gate!="u1q" for op in lowered.operations)
 assert [op.gate for op in lowered.operations] == ["rz"]

def test_described_qiskit_does_not_silently_gain_new_lowering_behavior():
 c=Circuit(1);c.h(0)
 with pytest.raises(ValueError,match="no lower_circuit_for_backend behavior"):
  lower_circuit_for_backend(c,backend_family="qiskit")

def test_described_pennylane_does_not_silently_gain_new_lowering_behavior():
 c=Circuit(1);c.h(0)
 with pytest.raises(ValueError,match="no lower_circuit_for_backend behavior"):
  lower_circuit_for_backend(c,backend_family="pennylane")

def test_unknown_backend_fails_closed():
 with pytest.raises(ValueError,match="Unknown backend capability model"):
  get_backend_capability_model("unknown")
