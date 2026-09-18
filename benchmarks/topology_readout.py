"""Topology-aware direct readout experiment for chain and balanced tree.

Uses exact tensor-network variable elimination over constant-size gate tensors.
No statevector and no Pauli expansion in the direct path. Exact reference is
used only through n=16. Hard workflow target <10 minutes.
"""
from __future__ import annotations
import json,time
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.verification import _apply_gate_to_state
from rqm_compiler.su4_blocks import _operation_matrix

Z=np.array([[1,0],[0,-1]],complex)

def edges(kind,n):
 if kind=="chain": return [(i,i+1) for i in range(n-1)]
 return [((i-1)//2,i) for i in range(1,n)]

def build(kind,n):
 c=Circuit(n)
 # Product |0> input; tree/chain 2Q episodes only. This isolates topology.
 for k,(a,b) in enumerate(edges(kind,n)):
  c.rxx(a,b,.11+.001*k);c.rzz(a,b,-.067-.001*k);c.cx(a,b)
 return c

def direct(kind,n):
 # Exact message passing on an acyclic interaction graph. Each edge block is a
 # rank-4 tensor. For global Z parity, eliminate leaves inward. Messages are
 # 2x2 operators on the parent, so width remains constant on trees.
 es=edges(kind,n);adj={i:[] for i in range(n)};blocks={}
 c=build(kind,n)
 # operations are three per edge in edge order
 for idx,(a,b) in enumerate(es):
  ops=c.operations[3*idx:3*idx+3];U=np.eye(4,dtype=complex)
  from rqm_compiler.ops import Operation
  for op in ops:
   touched=sorted(set(op.targets)|set(op.controls));mp={touched[0]:0,touched[1]:1}
   loc=Operation(op.gate,[mp[x] for x in op.targets],[mp[x] for x in op.controls],op.params)
   U=_operation_matrix(loc,(0,1))@U
  blocks[(a,b)]=U;adj[a].append(b);adj[b].append(a)
 root=0;parent={root:-1};order=[root]
 for v in order:
  for w in adj[v]:
   if w!=parent[v]:parent[w]=v;order.append(w)
 msg={};zero=np.array([[1,0],[0,0]],complex)
 for v in reversed(order[1:]):
  p=parent[v];key=(p,v) if (p,v) in blocks else (v,p);U=blocks[key]
  # subtree effect on v: Z times child messages
  Ov=Z.copy()
  for ch in adj[v]:
   if parent.get(ch)==v: Ov=Ov@msg[(ch,v)]
  # Contract v input |0><0| and subtree observable through pair unitary,
  # yielding an operator/message on parent input space.
  # M_p = Tr_v[(rho_v ⊗ I_p) U† (Ov ⊗ I_p) U] in local pair convention.
  A=U.conj().T@np.kron(Ov,np.eye(2))@U
  B=np.kron(zero,np.eye(2))@A
  x=B.reshape(2,2,2,2)
  msg[(v,p)]=np.einsum("abad->bd",x)
 O=Z.copy()
 for ch in adj[root]: O=O@msg[(ch,root)]
 return complex(O[0,0]),len(es)

def dense(c):
 s=[0j]*(1<<c.num_qubits);s[0]=1+0j
 for op in c.operations:s=_apply_gate_to_state(s,op,c.num_qubits)
 return float(sum(abs(x)**2*((-1)**i.bit_count()) for i,x in enumerate(s)))

rows=[]
for kind in ("chain","tree"):
 for n in (4,8,16,32,64,128,256):
  t=time.perf_counter_ns();v,count=direct(kind,n);dt=time.perf_counter_ns()-t
  row={"topology":kind,"n":n,"invariants":count,"direct_ns":dt,"value":v.real}
  if n<=16:
   ref=dense(build(kind,n));row["reference"]=ref;row["error"]=abs(v.real-ref)
  rows.append(row)
Path("results").mkdir(exist_ok=True);Path("results/topology_readout.json").write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
assert all(r.get("error",0)<=1e-9 for r in rows)
assert all(r["invariants"]==r["n"]-1 for r in rows)
