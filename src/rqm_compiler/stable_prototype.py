"""Stable exact RQM prototype.

Only mechanisms that have passed exact-reference validation are exposed here.
Experimental QST compression and failed rotor/tree-message variants are
intentionally excluded.

Stable components:
- verified optimize_circuit pipeline
- representation-owned closure accounting C_R
- exact structured Pauli observable propagation
- exact direct star/global-Z relational readout
- exact one-qubit operator boundary transfer maps for recursive research
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
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

@dataclass(frozen=True)
class StableReadoutResult:
 value:complex
 method:str
 exact:bool
 available:bool
 work_units:int|None=None
 reason:str=""

def compile_stable(circuit:Circuit, *, adaptive_policy:AdaptiveCartanPolicy|None=None)->StableCompileResult:
 out,report=optimize_circuit(circuit,adaptive_policy=adaptive_policy)
 return StableCompileResult(out,report,account_closed_representation(out))

def expectation_stable(circuit:Circuit, pauli:str|Iterable[str], *, max_terms:int=250_000)->StableReadoutResult:
 labels="".join(pauli) if not isinstance(pauli,str) else pauli
 if labels=="Z"*circuit.num_qubits:
  direct=global_z_star(circuit)
  if direct.available:
   return StableReadoutResult(direct.value,"direct_star_relational",True,True,direct.invariant_count)
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
 "boundary_transfer","apply_boundary_transfer","ObservableExpansionExceeded"
]
