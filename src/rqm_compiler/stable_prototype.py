"""Stable exact RQM prototype.

Only mechanisms that have passed exact-reference validation are exposed here.
Experimental QST compression and failed rotor/tree-message variants are
intentionally excluded.

Stable components:
- verified optimize_circuit pipeline
- representation-owned closure accounting C_R
- exact structured Pauli observable propagation
- exact direct star/global-Z relational readout
- exact one-qubit operator boundary transfer maps\n- recognized chain/global-Z recursive boundary-transfer readout\n- validated fixed-depth 1D hardware-efficient topology-aware readout
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import hashlib
import json
import time
import numpy as np

from .adaptive import AdaptiveCartanPolicy
from .adaptive_closure import account_closed_representation, ClosureAccounting
from .circuit import Circuit
from .compile import optimize_circuit
from .direct_readout import global_z_star
from .structured_observables import expectation_structured, ObservableExpansionExceeded
from .su4_blocks import _operation_matrix

_I=np.eye(2,dtype=complex)
_X=np.array([[0,1],[1,0]],complex)
_Y=np.array([[0,-1j],[1j,0]],complex)
_Z=np.array([[1,0],[0,-1]],complex)
_BASIS=(_I,_X,_Y,_Z)

@dataclass(frozen=True)
class StableCompileResult:
 circuit:Circuit
 report:object
 closure:ClosureAccounting
 query_source:Circuit|None=None
 source_digest:str|None=None
 output_digest:str|None=None

@dataclass(frozen=True)
class StableReadoutResult:
 value:complex
 method:str
 exact:bool
 available:bool
 work_units:int|None=None
 reason:str=""

def circuit_digest(circuit:Circuit)->str:
 payload={"num_qubits":circuit.num_qubits,"operations":circuit.to_descriptors()}
 return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def compile_stable(circuit:Circuit, *, adaptive_policy:AdaptiveCartanPolicy|None=None)->StableCompileResult:
 from .depth import circuit_depth
 from .report import CompilerReport
 from .regional import optimize_circuit_regions
 if circuit.num_qubits<=3:
  out,report=optimize_circuit(circuit,adaptive_policy=adaptive_policy)
 else:
  start=time.perf_counter_ns()
  out,regional=optimize_circuit_regions(circuit,adaptive_policy=adaptive_policy)
  changed=out.to_descriptors()!=circuit.to_descriptors()
  passes=list(dict.fromkeys(p for r in regional.regions for p in r.passes_applied)) if changed else []
  events=[]
  for region in regional.adaptive_regions:
   if not (regional.committed and region["optimization_applied"]):continue
   for event in region["routing"].get("representation_events",[]):
    if event.get("reason")!="verified_su4_replacement":continue
    if event.get("window_id") not in {w["window_id"] for w in region["routing"].get("selected_windows",[])}:continue
    # Preserve the local event and its localization map; do not mislabel local
    # window coordinates as global ones.
    events.append({**event,"region_index":region["region_index"],
                   "region_qubits":region["qubits"],"region_source_start":region["source_start"]})
  report=CompilerReport(
   original_gate_count=len(circuit),optimized_gate_count=len(out),
   original_depth=circuit_depth(circuit),optimized_depth=circuit_depth(out),
   passes_applied=passes,optimization_applied=changed,fallback_reason=regional.fallback_reason,
   equivalence_report={"status":"VERIFIED","verified":True,
     "method":"REGIONAL_COMPOSITION" if changed else "GATEWISE_IDENTITY",
     "phase_invariant":True,"regional":regional.to_dict()},
   adaptive_routing={"mode":(adaptive_policy or AdaptiveCartanPolicy.safe()).mode,
     "representation_events":events,"regions":regional.adaptive_regions,
     "kak_invocations":sum(r["routing"].get("kak_invocations",0) for r in regional.adaptive_regions)},
   stage_timings_ns={"regional_compilation":time.perf_counter_ns()-start})
 closure=account_closed_representation(out)
 report.representation_complexity=closure.minimum_closed_representation_size
 report.maximum_representation_level=closure.maximum_representation_level
 report.representation_histogram=dict(closure.representation_histogram)
 selected={w["window_id"] for w in report.adaptive_routing.get("selected_windows",[])}
 report.promotion_count=sum(e.get("kind")=="promotion" and e.get("reason")=="verified_su4_replacement"
  and ("region_index" in e or e.get("window_id") in selected)
  for e in report.adaptive_routing.get("representation_events",[])) if report.optimization_applied else 0
 # A verified equivalent input preserves specialized query structure that
 # optimization may materialize differently. Digests guard against mutation.
 source=Circuit.from_descriptors(circuit.to_descriptors(),num_qubits=circuit.num_qubits)
 return StableCompileResult(out,report,closure,source,circuit_digest(source),circuit_digest(out))


def global_z_chain(circuit:Circuit)->StableReadoutResult:
 from .su4_blocks import _single_qubit_matrix
 from .ops import Operation
 n=circuit.num_qubits;ops=circuit.operations
 if n<2:return StableReadoutResult(0j,"chain_boundary_transfer",True,False,None,"n<2")
 idx=0;psi=np.array([1,0],complex)
 while idx<len(ops) and len(set(ops[idx].targets)|set(ops[idx].controls))==1:
  if ops[idx].targets[0]!=0:return StableReadoutResult(0j,"chain_boundary_transfer",True,False,None,"unsupported preparation")
  psi=_single_qubit_matrix(ops[idx])@psi;idx+=1
 blocks=[]
 for edge in range(n-1):
  if idx+3>len(ops):return StableReadoutResult(0j,"chain_boundary_transfer",True,False,None,"incomplete chain")
  b=ops[idx:idx+3];idx+=3;touched=[set(x.targets)|set(x.controls) for x in b]
  if [x.gate for x in b]!=["rxx","rzz","cx"] or any(t!={edge,edge+1} for t in touched):
   return StableReadoutResult(0j,"chain_boundary_transfer",True,False,None,"not validated chain form")
  blocks.append(b)
 if idx!=len(ops):return StableReadoutResult(0j,"chain_boundary_transfer",True,False,None,"extra operations")
 O=_Z.copy()
 for edge in range(n-2,-1,-1):
  U=np.eye(4,dtype=complex);mp={edge:0,edge+1:1}
  for op in blocks[edge]:
   loc=Operation(op.gate,[mp[x] for x in op.targets],[mp[x] for x in op.controls],op.params)
   U=_operation_matrix(loc,(0,1))@U
  O=apply_boundary_transfer(boundary_transfer(U,np.array([[1,0],[0,0]],complex),O),_Z)
 rho=np.outer(psi,psi.conj())
 return StableReadoutResult(complex(np.trace(rho@O)),"chain_boundary_transfer",True,True,n-1)

def expectation_stable(circuit:Circuit, pauli:str|Iterable[str], *, max_terms:int=250_000)->StableReadoutResult:
 from .validate import validate_circuit
 validate_circuit(circuit)
 labels="".join(pauli) if not isinstance(pauli,str) else pauli
 if len(labels)!=circuit.num_qubits or any(x not in "IXYZ" for x in labels):
  raise ValueError("Expected one I/X/Y/Z Pauli label per qubit")
 if isinstance(max_terms,bool) or not isinstance(max_terms,int) or max_terms<1:raise ValueError("max_terms must be a positive integer")
 if any(op.gate=="measure" for op in circuit.operations):raise ValueError("unitary circuit required")
 if labels=="Z"*circuit.num_qubits:
  direct=global_z_star(circuit)
  if direct.available:
   return StableReadoutResult(direct.value,"direct_star_relational",True,True,direct.invariant_count)
  chain=global_z_chain(circuit)
  if chain.available:
   return chain
  from .topology_readout import global_z_hardware
  hw=global_z_hardware(circuit)
  if hw is not None:
   value,largest,layers=hw
   return StableReadoutResult(value,"topology_hardware_1d",True,True,largest,f"validated_layers={layers}")
 try:
  r=expectation_structured(circuit,labels,max_terms=max_terms)
  return StableReadoutResult(r.value,r.representation,True,True,r.peak_terms)
 except ObservableExpansionExceeded as exc:
  return StableReadoutResult(0j,"structured_exact",True,False,None,str(exc))

def boundary_transfer(pair_unitary:np.ndarray, rho_leaf:np.ndarray, observable_leaf:np.ndarray)->np.ndarray:
 """Exact map O_parent -> O'_parent in the {I,X,Y,Z} basis.

 This is a constant-dimensional exact primitive.  It does not construct a
 global statevector or an n-qubit Pauli expansion.
 """
 U=np.asarray(pair_unitary,dtype=complex)
 rho=np.asarray(rho_leaf,dtype=complex)
 Ol=np.asarray(observable_leaf,dtype=complex)
 if U.shape!=(4,4) or rho.shape!=(2,2) or Ol.shape!=(2,2):
  raise ValueError("expected U:(4,4), rho_leaf:(2,2), observable_leaf:(2,2)")
 T=np.zeros((4,4),complex)
 for nu,Op in enumerate(_BASIS):
  A=U.conj().T@np.kron(Ol,Op)@U
  C=np.kron(rho,_I)@A
  x=C.reshape(2,2,2,2)
  M=np.einsum("abad->bd",x)
  for mu,S in enumerate(_BASIS):
   T[mu,nu]=np.trace(S@M)/2
 return T

def apply_boundary_transfer(T:np.ndarray, observable:np.ndarray)->np.ndarray:
 T=np.asarray(T,dtype=complex);O=np.asarray(observable,dtype=complex)
 if T.shape!=(4,4) or O.shape!=(2,2):
  raise ValueError("expected T:(4,4), observable:(2,2)")
 v=np.array([np.trace(S@O)/2 for S in _BASIS],complex)
 w=T@v
 return sum(w[i]*_BASIS[i] for i in range(4))

__all__=[
 "StableCompileResult","StableReadoutResult","compile_stable","expectation_stable",
 "boundary_transfer","apply_boundary_transfer","global_z_chain","ObservableExpansionExceeded"
]
