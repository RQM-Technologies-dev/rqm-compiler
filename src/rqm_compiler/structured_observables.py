"""Least-general exact observable evaluator.

The current first stage recognizes exact local-frame closure: trailing 1Q
conjugations are accumulated as one Bloch/quaternion-frame vector per qubit.
If an entangling boundary is reached, evaluation promotes to the proven exact
Pauli-sum engine. This is deliberately conservative and provides the promotion
boundary needed for subsequent AxisHinge/Cartan observable representations.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import numpy as np
from .circuit import Circuit
from .observables import expectation_pauli, ObservableExpansionExceeded
from .su4_blocks import _single_qubit_matrix

P={
 "X":np.array([[0,1],[1,0]],complex),
 "Y":np.array([[0,-1j],[1j,0]],complex),
 "Z":np.array([[1,0],[0,-1]],complex),
}

@dataclass(frozen=True)
class StructuredObservableResult:
 value:complex
 final_terms:int
 peak_terms:int
 operations_processed:int
 local_frame_steps:int
 promotion_count:int
 representation:str

def _rotate(v,u):
 labels=("X","Y","Z");out=np.zeros(3,float)
 for j,a in enumerate(labels):
  for k,b in enumerate(labels):
   out[j]+=float((np.trace(P[a]@u.conj().T@P[b]@u)/2).real)*v[k]
 return out

def expectation_structured(circuit:Circuit,pauli:str|Iterable[str],*,cutoff:float=1e-13,max_terms:int=250000):
 labels=tuple(pauli)
 if len(labels)!=circuit.num_qubits: raise ValueError("Pauli string length must equal circuit.num_qubits")
 vectors=[None if x=="I" else np.eye(3)[("X","Y","Z").index(x)] for x in labels]
 local_steps=0;hit_entangling=False
 for op in reversed(circuit.operations):
  if op.gate=="barrier": continue
  touched=sorted(set(op.targets)|set(op.controls))
  if len(touched)!=1:
   hit_entangling=True;break
  q=touched[0]
  if vectors[q] is not None:vectors[q]=_rotate(vectors[q],_single_qubit_matrix(op))
  local_steps+=1
 if not hit_entangling:
  value=1+0j
  for v in vectors:
   if v is not None:value*=complex(v[2])
  return StructuredObservableResult(value,1,1,local_steps,local_steps,0,"local_quaternion_frame")
 r=expectation_pauli(circuit,labels,cutoff=cutoff,max_terms=max_terms)
 return StructuredObservableResult(r.value,r.final_terms,r.peak_terms,r.operations_processed,local_steps,1,"pauli_sum_promoted")
