"""Width-2 topology-aware hardware-efficient readout prototype.

Exact tensor contraction with opt_einsum on the two-layer nearest-neighbor
hardware-efficient circuit. The candidate path contracts the tensor network
directly (no n-qubit statevector, no Pauli expansion). Validate n=4,8,12
against Aer/statevector at 1e-9 and record largest intermediate.
"""
import json,time
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.su4_blocks import _operation_matrix,_single_qubit_matrix
from rqm_compiler.ops import Operation
from rqm_compiler.verification import _apply_gate_to_state

TOL=1e-9
Z=np.array([[1,0],[0,-1]],complex)
ZERO=np.array([1,0],complex)

def build(n):
 c=Circuit(n)
 for layer in range(2):
  for q in range(n):
   c.rz(q,.021*(q+1)*(layer+1));c.rx(q,.017*(q+2)*(layer+1))
  for i in range(n-1):c.cx(i,i+1)
 return c

def dense(c):
 s=[0j]*(1<<c.num_qubits);s[0]=1+0j
 for op in c.operations:s=_apply_gate_to_state(s,op,c.num_qubits)
 return float(sum(abs(x)**2*((-1)**i.bit_count()) for i,x in enumerate(s)))

def tn_expectation(c):
 import opt_einsum as oe
 n=c.num_qubits
 # Build ket amplitude tensor network and conjugate copy, then connect outputs
 # with local Z tensors. Integer labels uniquely identify wire segments.
 tensors=[];inds=[];label=0
 ket=[None]*n;bra=[None]*n
 for q in range(n):
  ket[q]=label;label+=1;tensors.append(ZERO);inds.append([ket[q]])
  bra[q]=label;label+=1;tensors.append(ZERO.conj());inds.append([bra[q]])
 for op in c.operations:
  touched=sorted(set(op.targets)|set(op.controls))
  if len(touched)==1:
   q=touched[0];U=_single_qubit_matrix(op)
   ko=label;label+=1;tensors.append(U);inds.append([ko,ket[q]]);ket[q]=ko
   bo=label;label+=1;tensors.append(U.conj());inds.append([bo,bra[q]]);bra[q]=bo
  else:
   a,b=touched;mp={a:0,b:1}
   loc=Operation(op.gate,[mp[x] for x in op.targets],[mp[x] for x in op.controls],op.params)
   U=_operation_matrix(loc,(0,1)).reshape(2,2,2,2).transpose(1,0,3,2)
   ka,kb=label,label+1;label+=2;tensors.append(U);inds.append([ka,kb,ket[a],ket[b]]);ket[a],ket[b]=ka,kb
   ba,bb=label,label+1;label+=2;tensors.append(U.conj());inds.append([ba,bb,bra[a],bra[b]]);bra[a],bra[b]=ba,bb
 for q in range(n):tensors.append(Z);inds.append([bra[q],ket[q]])
 args=[]
 for T,Ix in zip(tensors,inds):args.extend([T,Ix])
 args.append([])
 path,info=oe.contract_path(*args,optimize="greedy")
 t=time.perf_counter_ns();v=oe.contract(*args,optimize=path);dt=time.perf_counter_ns()-t
 return complex(v),dt,int(info.largest_intermediate),float(info.opt_cost)

rows=[]
for n in (4,8,12):
 c=build(n);v,dt,largest,cost=tn_expectation(c);t=time.perf_counter_ns();ref=dense(c);refdt=time.perf_counter_ns()-t
 rows.append({"n":n,"value":v.real,"reference":ref,"error":abs(v.real-ref),"exact_valid":abs(v.real-ref)<=TOL,
              "tn_ns":dt,"reference_ns":refdt,"largest_intermediate":largest,"opt_cost":cost})
summary={"cases":3,"exact_valid":sum(r["exact_valid"] for r in rows),
         "largest_intermediates":[r["largest_intermediate"] for r in rows],
         "max_error":max(r["error"] for r in rows)}
Path("results").mkdir(exist_ok=True);Path("results/hardware_width2_readout.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps({"summary":summary,"rows":rows}))
assert summary["exact_valid"]==3
