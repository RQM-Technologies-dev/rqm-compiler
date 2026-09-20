"""Direct relational readout invariants.

This module deliberately avoids Pauli-sum expansion and state-vector
materialization.  The first exact invariant targets star circuits whose leaves
interact once with a hub through compiler-supported 2Q operations.  Such a
circuit is an exact bond-2 star tensor network: tracing/projecting each leaf
induces a 2x2 transfer map on the hub.  Global product-Z and hub/leaf Z
expectations can therefore be contracted with constant hub dimension.

This is an established tensor-contraction identity applied to RQM's structured
AxisHinge/Cartan gate representation; it is not a claim that a speculative QSG
measurement postulate has been proved.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .circuit import Circuit
from .su4_blocks import _operation_matrix,_single_qubit_matrix

Z=np.array([[1,0],[0,-1]],complex)
I=np.eye(2,dtype=complex)
ZERO=np.array([1,0],complex)

@dataclass(frozen=True)
class DirectReadout:
 value:complex
 available:bool
 invariant_count:int
 representation:str
 reason:str=""
 intermediate_unit:str="complex_array_entries"

def _apply_1q_state(v,u): return u@v

def _leaf_transfer(rho, psi, gates, *, hub, leaf, observable):
 # Contract one fresh leaf exactly.  Hub is pair[0], leaf pair[1] in the
 # compiler matrix convention used by _operation_matrix.
 # Build the 4x4 pair unitary only; never a global state/operator.
 U=np.eye(4,dtype=complex)
 dummy=Circuit(2)
 for op in gates:
  # remap hub/leaf indices to 0/1 for the local structured block
  from .ops import Operation
  touched=sorted(set(op.targets)|set(op.controls))
  mp={hub:0,leaf:1}
  loc=Operation(op.gate,[mp[x] for x in op.targets],[mp[x] for x in op.controls],op.params)
  U=_operation_matrix(loc,(0,1))@U
 # Transfer on hub density: rho'_{a,a'} = sum_{b,b'} ...
 joint=np.kron(np.outer(psi,psi.conj()),rho) # leaf (MSB) kron hub (LSB)
 joint=U@joint@U.conj().T
 O=np.kron(observable,I)
 weighted=O@joint
 # partial trace leaf, preserving hub
 x=weighted.reshape(2,2,2,2) # leaf,hub,leaf',hub'
 return np.einsum("abad->bd",x)

def global_z_star(circuit:Circuit, hub:int=0)->DirectReadout:
 return product_star(circuit, "Z"*circuit.num_qubits, hub=hub)


def product_star(circuit:Circuit, labels:str, hub:int|None=None)->DirectReadout:
 from .validate import validate_circuit
 validate_circuit(circuit)
 if len(labels)!=circuit.num_qubits or any(x not in "IXYZ" for x in labels):
  raise ValueError("Expected one I/X/Y/Z Pauli label per qubit")
 if any(op.gate=="measure" for op in circuit.operations):raise ValueError("unitary circuit required")
 if hub is None:
  pairs=[set(op.targets)|set(op.controls) for op in circuit.operations
         if op.gate!="barrier" and len(set(op.targets)|set(op.controls))==2]
  common=set.intersection(*pairs) if pairs else set()
  if not common:return DirectReadout(0j,False,0,"star_transfer","no common hub")
  hub=min(common)
 if isinstance(hub,bool) or not isinstance(hub,int) or not 0<=hub<circuit.num_qubits:
  raise ValueError("hub must be a valid qubit index")
 # Recognize: initial 1Q gates, uninterrupted leaf episodes, then final 1Q gates;
 # each non-hub qubit participates in exactly one contiguous hub-leaf 2Q block.
 n=circuit.num_qubits
 if n<2:return DirectReadout(0j,False,0,"star_transfer","n<2")
 # For the benchmark family, collect all 1Q gates separately and 2Q episodes
 # per leaf.  Reject leaf-leaf interactions and repeated noncontiguous leaves.
 pre={q:[] for q in range(n)};post={q:[] for q in range(n)};blocks=[];seen=set();current=None
 started=False;post_started=False
 for op in circuit.operations:
  # A barrier is scheduling metadata, not a unitary interaction. Keep it in
  # the circuit IR, but do not send it to the local gate-matrix builder.
  if op.gate=="barrier":continue
  touched=sorted(set(op.targets)|set(op.controls))
  if len(touched)==1:
   if started:post_started=True
   (post if started else pre)[touched[0]].append(op);continue
  # Z-preserving gates may be dropped only at the end, not moved across a
  # later interaction. Reject even potentially commuting placements unless
  # proven by this recognizer; the public planner retains its exact fallback.
  if post_started:return DirectReadout(0j,False,len(blocks),"star_transfer","interleaved single-qubit gate")
  if len(touched)!=2 or hub not in touched:return DirectReadout(0j,False,0,"star_transfer","non-star interaction")
  leaf=touched[0] if touched[1]==hub else touched[1];started=True
  if current is None or current[0]!=leaf:
   if leaf in seen:return DirectReadout(0j,False,0,"star_transfer","revisited leaf")
   seen.add(leaf);current=[leaf,[]];blocks.append(current)
  current[1].append(op)
 if seen!=set(range(n))-{hub}:return DirectReadout(0j,False,0,"star_transfer","not all leaves represented")
 # Closed analytic hinge/CX path: real Pauli coefficients, no gate matrices.
 if all(op.gate in {"rxx","ryy","rzz","cx"} for _,gates in blocks for op in gates):
  from .local_observable import prepared_coefficients, observable_coefficients
  from rqm_entanglement.pauli_transfer import apply_pair_coefficients
  states={q:prepared_coefficients(pre[q]) for q in range(n)}
  obs={q:observable_coefficients(labels[q],post[q]) for q in range(n)}
  rho=np.asarray(states[hub])
  for leaf,gates in blocks:
   joint=np.outer(rho,states[leaf])
   for op in gates:
    axes=(0,1) if op.gate!="cx" or op.controls[0]==hub else (1,0)
    joint=apply_pair_coefficients(joint,axes,op.gate,float(op.params.get("angle",0.)))
   rho=joint@obs[leaf]
  return DirectReadout(complex(np.dot(obs[hub],rho)),True,len(blocks),
                       "analytic_hinge_star_transfer",intermediate_unit="real_pauli_coefficients")
 # Prepare product inputs under pre-1Q gates.
 states={}
 for q in range(n):
  v=ZERO.copy()
  for op in pre[q]:v=_single_qubit_matrix(op)@v
  states[q]=v
 rho=np.outer(states[hub],states[hub].conj())
 # Rotate each requested observable through its final local frame.
 P={"I":I,"X":np.array([[0,1],[1,0]],complex),
    "Y":np.array([[0,-1j],[1j,0]],complex),"Z":Z}
 observables={q:P[labels[q]].copy() for q in range(n)}
 for q in range(n):
  for op in reversed(post[q]):
   u=_single_qubit_matrix(op)
   observables[q]=u.conj().T@observables[q]@u
 for leaf,gates in blocks:
  rho=_leaf_transfer(rho,states[leaf],gates,hub=hub,leaf=leaf,observable=observables[leaf])
 value=np.trace(observables[hub]@rho)
 return DirectReadout(complex(value),True,len(blocks),"axis_hinge_cartan_star_transfer")
