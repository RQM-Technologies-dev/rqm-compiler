"""Backend/modality capability descriptions for RQM Compiler 0.4.

The model describes target constraints without moving backend-specific execution
logic into the representation planner. Initial built-ins intentionally preserve
existing lowering behavior.
"""
from __future__ import annotations
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

@dataclass(frozen=True)
class BackendCapabilityModel:
    name:str
    framework:str
    modality:str
    native_operations:frozenset[str]
    structured_operations:frozenset[str]
    internal_operations_requiring_materialization:frozenset[str]
    supports_arbitrary_unitary:bool
    supports_mid_circuit_measurement:bool
    supports_dynamic_circuits:bool
    connectivity:str
    lowering_profile:str

    def supports_operation(self,gate:str)->bool:
        g=gate.lower()
        return g in self.native_operations or g in self.structured_operations

_COMMON_1Q=frozenset({"i","x","y","z","h","s","t","rx","ry","rz","phaseshift"})
_COMMON_2Q=frozenset({"cx","cy","cz","swap","iswap"})
_PAIR_ROT=frozenset({"rxx","ryy","rzz"})

_BUILTINS={
 "qiskit":BackendCapabilityModel("qiskit","qiskit","gate_model",_COMMON_1Q|_COMMON_2Q,_PAIR_ROT,frozenset({"u1q","su4q"}),True,True,True,"backend_defined","standard_descriptors"),
 "braket_gate_model":BackendCapabilityModel("braket_gate_model","amazon_braket","gate_model",_COMMON_1Q|_COMMON_2Q,_PAIR_ROT,frozenset({"u1q","su4q"}),True,True,False,"device_defined","named_1q"),
 "pennylane":BackendCapabilityModel("pennylane","pennylane","gate_model",_COMMON_1Q|frozenset({"cx","cz","swap"}),_PAIR_ROT,frozenset({"u1q","su4q"}),True,True,True,"device_defined","named_1q"),
}
BACKEND_CAPABILITIES:Mapping[str,BackendCapabilityModel]=MappingProxyType(_BUILTINS)

def get_backend_capability_model(name:str)->BackendCapabilityModel:
    try:return BACKEND_CAPABILITIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown backend capability model {name!r}; available: {', '.join(sorted(BACKEND_CAPABILITIES))}") from exc

__all__=["BackendCapabilityModel","BACKEND_CAPABILITIES","get_backend_capability_model"]
