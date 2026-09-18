import pytest
from rqm_compiler import (
 BackendCapabilityModel,Circuit,compile_for_backend,get_backend_capability_model,lower_circuit_for_backend,plan_backend_materialization,
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


def test_materialization_plan_identifies_internal_u1q_without_mutating_circuit():
 c=Circuit(2);c.u1q(0,1,0,0,0);c.rxx(0,1,.2)
 before=c.to_descriptors()
 p=plan_backend_materialization(c,"braket_gate_model")
 assert p.materialize_operations==("u1q",)
 assert p.unsupported_operations==()
 assert c.to_descriptors()==before

def test_compile_for_backend_records_capability_and_materialization():
 c=Circuit(1);c.h(0)
 lowered,report=compile_for_backend(c,backend_family="braket_gate_model")
 assert all(op.gate!="u1q" for op in lowered.operations)
 d=report.to_dict()
 assert d["backend_capability_model"]=="braket_gate_model"
 assert d["backend_framework"]=="amazon_braket"
 assert d["backend_modality"]=="gate_model"
 assert d["backend_lowering_profile"]=="named_1q"
 assert d["backend_materializations"]==["u1q"]
 assert d["backend_unsupported_operations"]==[]

def test_braket_lowering_matches_direct_pre_capability_contract():
 c=Circuit(2);c.h(0);c.cx(0,1);c.rz(1,.2)
 optimized,_=__import__("rqm_compiler").optimize_circuit(c)
 direct=lower_circuit_for_backend(optimized,backend_family="braket_gate_model")
 compiled,_=compile_for_backend(c,backend_family="braket_gate_model")
 assert compiled.to_descriptors()==direct.to_descriptors()
