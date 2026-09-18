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

def _apply_1q_state(v,u): return u@v

def _leaf_transfer(rho, psi, gates, *, insert_z):
 # Contract one fresh leaf exactly.  Hub is pair[0], leaf pair[1] in the
 # compiler matrix convention used by _operation_matrix.
 # Build the 4x4 pair unitary only; never a global state/operator.
 U=np.eye(4,dtype=complex)
 dummy=Circuit(2)
 for op in gates:
  # remap hub/leaf indices to 0/1 for the local structured block
  from .ops import Operation
  touched=sorted(set(op.targets)|set(op.controls))
  mp={touched[0]:0,touched[1]:1}
  loc=Operation(op.gate,[mp[x] for x in op.targets],[mp[x] for x in op.controls],op.params)
  U=_operation_matrix(loc,(0,1))@U
 # Transfer on hub density: rho'_{a,a'} = sum_{b,b'} ...
 joint=np.kron(np.outer(psi,psi.conj()),rho) # leaf (MSB) kron hub (LSB)
 joint=U@joint@U.conj().T
 O=np.kron(Z if insert_z else I,I)
 weighted=O@joint
 # partial trace leaf, preserving hub
 x=weighted.reshape(2,2,2,2) # leaf,hub,leaf',hub'
 return np.einsum("abad->bd",x)

def global_z_star(circuit:Circuit, hub:int=0)->DirectReadout:
 # Recognize: arbitrary initial/final 1Q gates plus disjoint leaf episodes;
 # each non-hub qubit participates in exactly one contiguous hub-leaf 2Q block.
 n=circuit.num_qubits
 if n<2:return DirectReadout(0j,False,0,"star_transfer","n<2")
 # For the benchmark family, collect all 1Q gates separately and 2Q episodes
 # per leaf.  Reject leaf-leaf interactions and repeated noncontiguous leaves.
 pre={q:[] for q in range(n)};post={q:[] for q in range(n)};blocks=[];seen=set();current=None
 started=False
 for op in circuit.operations:
  touched=sorted(set(op.targets)|set(op.controls))
  if len(touched)==1:
   (post if started else pre)[touched[0]].append(op);continue
  if len(touched)!=2 or hub not in touched:return DirectReadout(0j,False,0,"star_transfer","non-star interaction")
  leaf=touched[0] if touched[1]==hub else touched[1];started=True
  if current is None or current[0]!=leaf:
   if leaf in seen:return DirectReadout(0j,False,0,"star_transfer","revisited leaf")
   seen.add(leaf);current=[leaf,[]];blocks.append(current)
  current[1].append(op)
 if seen!=set(range(n))-{hub}:return DirectReadout(0j,False,0,"star_transfer","not all leaves represented")
 # Prepare product inputs under pre-1Q gates.
 states={}
 for q in range(n):
  v=ZERO.copy()
  for op in pre[q]:v=_single_qubit_matrix(op)@v
  states[q]=v
 rho=np.outer(states[hub],states[hub].conj())
 # Final local gates rotate measurement axes. Current exact invariant supports
 # only gates commuting with Z (the benchmark uses RZ); reject otherwise.
 for q in range(n):
  for op in post[q]:
   u=_single_qubit_matrix(op)
   if not np.allclose(u.conj().T@Z@u,Z,atol=1e-12):
    return DirectReadout(0j,False,len(blocks),"star_transfer","non-Z-preserving post gate")
 for leaf,gates in blocks:
  rho=_leaf_transfer(rho,states[leaf],gates,insert_z=True)
 value=np.trace(Z@rho)
 return DirectReadout(complex(value),True,len(blocks),"axis_hinge_cartan_star_transfer")
