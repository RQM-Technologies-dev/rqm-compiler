"""Least-general exact observable evaluation with relational 2Q closure.

A sparse Pauli map is retained, but two-qubit conjugation is performed
analytically for Pauli rotations and Clifford CNOT/CX rather than materializing
and decomposing dense 4x4 operators. This is the observable-side analogue of
AxisHinge/Cartan closure: closed generators stay algebraic and promotion to the
general dense decomposition is reserved for unsupported 2Q operations.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import cmath,math
from .circuit import Circuit
from .observables import expectation_pauli,ObservableExpansionExceeded
from .validate import validate_observable_query

@dataclass(frozen=True)
class StructuredObservableResult:
 value:complex
 final_terms:int
 peak_terms:int
 operations_processed:int
 local_frame_steps:int
 promotion_count:int
 representation:str

# Pauli multiplication: a*b = phase*c.
_M={("I","I"):(1,"I"),("I","X"):(1,"X"),("I","Y"):(1,"Y"),("I","Z"):(1,"Z"),
("X","I"):(1,"X"),("Y","I"):(1,"Y"),("Z","I"):(1,"Z"),
("X","X"):(1,"I"),("Y","Y"):(1,"I"),("Z","Z"):(1,"I"),
("X","Y"):(1j,"Z"),("Y","X"):(-1j,"Z"),("Y","Z"):(1j,"X"),("Z","Y"):(-1j,"X"),
("Z","X"):(1j,"Y"),("X","Z"):(-1j,"Y")}

def _mul(a,b):
 phase=1+0j;out=[]
 for x,y in zip(a,b):
  p,z=_M[(x,y)];phase*=p;out.append(z)
 return phase,tuple(out)

def _anticommutes(a,b):
 return sum(x!="I" and y!="I" and x!=y for x,y in zip(a,b))%2==1

def _rotation(terms,generator,theta,cutoff):
 # U=exp(-i theta G/2): U^dag P U = cos(theta)P + i sin(theta) G P
 out={}
 c=math.cos(theta);s=math.sin(theta)
 for p,a in terms.items():
  if not _anticommutes(generator,p):out[p]=out.get(p,0j)+a;continue
  ph,gp=_mul(generator,p)
  out[p]=out.get(p,0j)+a*c
  out[gp]=out.get(gp,0j)+a*(1j*s*ph)
 return {p:a for p,a in out.items() if abs(a)>cutoff}

def _cx_label(p,c,t):
 # Exact Clifford conjugation via binary symplectic CX map.
 x=[q in ("X","Y") for q in p];z=[q in ("Z","Y") for q in p]
 # phase is recovered robustly by multiplying mapped generators.
 gens=[]
 for i,q in enumerate(p):
  if q=="I":continue
  if q=="X":gens.append(("X",i))
  elif q=="Z":gens.append(("Z",i))
  else:gens.extend([("X",i),("Z",i)])
 acc=tuple("I" for _ in p);phase=1+0j
 # Y = i X Z
 phase*= (1j)**sum(q=="Y" for q in p)
 for kind,i in gens:
  chars=["I"]*len(p)
  if kind=="X":
   chars[i]="X"
   if i==c:chars[t]="X"
  else:
   chars[i]="Z"
   if i==t:chars[c]="Z"
  ph,acc=_mul(acc,tuple(chars));phase*=ph
 # Hermitian Pauli conjugation must have real +/- phase.
 sign=1 if phase.real>=0 else -1
 return acc,sign

def expectation_structured(circuit:Circuit,pauli:str|Iterable[str],*,cutoff:float=1e-13,max_terms:int=250000):
 labels=validate_observable_query(circuit,pauli,max_terms=max_terms)
 terms={labels:1+0j};peak=1;processed=0;promotions=0;closed2q=0
 for op in reversed(circuit.operations):
  if op.gate=="barrier":continue
  if op.gate=="measure":raise ValueError("unitary circuit required")
  touched=sorted(set(op.targets)|set(op.controls))
  if op.gate in ("rxx","ryy","rzz"):
   axis={"rxx":"X","ryy":"Y","rzz":"Z"}[op.gate];g=["I"]*circuit.num_qubits
   for q in touched:g[q]=axis
   terms=_rotation(terms,tuple(g),float(op.params["angle"]),cutoff);closed2q+=1
  elif op.gate=="cx":
   c=op.controls[0];t=op.targets[0];u={}
   for p,a in terms.items():
    np_,sgn=_cx_label(p,c,t);u[np_]=u.get(np_,0j)+a*sgn
   terms={p:a for p,a in u.items() if abs(a)>cutoff};closed2q+=1
  elif len(touched)==1:
   from .local_observable import local_pauli_expansions
   expansions=local_pauli_expansions(op,cutoff);q=touched[0];updated={}
   for p,a in terms.items():
    for label,factor in expansions[p[q]]:
     key=p[:q]+(label,)+p[q+1:]
     updated[key]=updated.get(key,0j)+a*factor
   terms={p:a for p,a in updated.items() if abs(a)>cutoff}
  else:
   # One-qubit and uncommon 2Q gates retain the proven general evaluator for
   # now. If any such gate exists, delegate whole query to preserve exactness.
   promotions+=1
   try:
    r=expectation_pauli(circuit,labels,cutoff=cutoff,max_terms=max_terms)
   except ObservableExpansionExceeded as exc:
    exc.query_promotion_count=promotions
    raise
   return StructuredObservableResult(r.value,r.final_terms,r.peak_terms,r.operations_processed,0,promotions,"general_pauli_promoted")
  processed+=1;peak=max(peak,len(terms))
  if len(terms)>max_terms:raise ObservableExpansionExceeded(f"structured expansion exceeded max_terms={max_terms}", peak_terms=peak, operations_processed=processed)
 value=sum(a for p,a in terms.items() if all(x in ("I","Z") for x in p))
 return StructuredObservableResult(complex(value),len(terms),peak,processed,0,promotions,"axis_hinge_cartan_pauli_sparse")
