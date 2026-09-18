"""Gate-by-gate tensor-network convention diagnostic for n=2,3."""
import json
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.verification import _apply_gate_to_state
from rqm_compiler.su4_blocks import _operation_matrix,_single_qubit_matrix
from rqm_compiler.ops import Operation

def build(n):
 c=Circuit(n)
 for layer in range(2):
  for q in range(n):c.rz(q,.021*(q+1)*(layer+1));c.rx(q,.017*(q+2)*(layer+1))
  for i in range(n-1):c.cx(i,i+1)
 return c

def dense_prefix(c,k):
 s=[0j]*(1<<c.num_qubits);s[0]=1+0j
 for op in c.operations[:k]:s=_apply_gate_to_state(s,op,c.num_qubits)
 return np.array(s)

def tn_prefix(c,k,swap2=False):
 # Explicit small tensor evolution using the same local matrices but a tested
 # reshape convention. This isolates 2Q index ordering without readout logic.
 psi=np.zeros((2,)*c.num_qubits,complex);psi[(0,)*c.num_qubits]=1
 for op in c.operations[:k]:
  touched=sorted(set(op.targets)|set(op.controls))
  if len(touched)==1:
   q=touched[0];U=_single_qubit_matrix(op)
   psi=np.tensordot(U,psi,axes=([1],[q]));psi=np.moveaxis(psi,0,q)
  else:
   a,b=touched;mp={a:0,b:1};loc=Operation(op.gate,[mp[x] for x in op.targets],[mp[x] for x in op.controls],op.params)
   U=_operation_matrix(loc,(0,1)).reshape(2,2,2,2)
   if swap2:U=U.transpose(1,0,3,2)
   tmp=np.tensordot(U,psi,axes=([2,3],[a,b]))
   rest=[q for q in range(c.num_qubits) if q not in (a,b)]
   # tmp axes: out_a,out_b,rest; permute back to qubit-axis order
   src={a:0,b:1};src.update({q:2+i for i,q in enumerate(rest)})
   psi=np.transpose(tmp,[src[q] for q in range(c.num_qubits)])
 # dense reference indexes little-endian; tensor axes are q0..qn-1
 return psi.transpose(tuple(reversed(range(c.num_qubits)))).reshape(-1)

rows=[];first=None
for n in (2,3):
 c=build(n)
 for k,op in enumerate(c.operations,1):
  ref=dense_prefix(c,k);a=tn_prefix(c,k,False);b=tn_prefix(c,k,True)
  ea=float(np.linalg.norm(a-ref));eb=float(np.linalg.norm(b-ref))
  row={"n":n,"step":k,"gate":op.gate,"targets":op.targets,"controls":op.controls,"error_native":ea,"error_swapped":eb}
  rows.append(row)
  if first is None and ea>1e-12:first=row
summary={"first_native_divergence":first,"native_final_errors":{str(n):next(r["error_native"] for r in reversed(rows) if r["n"]==n) for n in (2,3)},
"swapped_final_errors":{str(n):next(r["error_swapped"] for r in reversed(rows) if r["n"]==n) for n in (2,3)}}
Path("results").mkdir(exist_ok=True);Path("results/tn_convention_diagnostic.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps({"summary":summary,"rows":rows}))
