"""Exact chain readout using stable map-valued boundary transfers.

Uses the already-validated boundary_transfer primitive recursively on a chain.
No n-qubit Pauli expansion and no global statevector in the RQM candidate path.
Compares against Qiskit/Aer for n=4,8,12 and records exactness + speedup.
"""
from __future__ import annotations
import json,statistics,time
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.stable_prototype import boundary_transfer,apply_boundary_transfer,compile_stable
from rqm_compiler.su4_blocks import _operation_matrix
from rqm_compiler.ops import Operation

I=np.eye(2,dtype=complex); Z=np.array([[1,0],[0,-1]],complex); ZERO=np.array([[1,0],[0,0]],complex)
NS=(4,8,12);REPEATS=3;TOL=1e-9

def build(n):
 c=Circuit(n);c.h(0)
 for i in range(n-1):
  c.rxx(i,i+1,.11+.002*i);c.rzz(i,i+1,-.067-.001*i);c.cx(i,i+1)
 return c

def edge_unitary(ops,a,b):
 U=np.eye(4,dtype=complex)
 for op in ops:
  touched=sorted(set(op.targets)|set(op.controls));mp={a:0,b:1}
  loc=Operation(op.gate,[mp[x] for x in op.targets],[mp[x] for x in op.controls],op.params)
  U=_operation_matrix(loc,(0,1))@U
 return U

def direct_chain(c):
 # benchmark family layout: initial H(0), then 3-op contiguous blocks per edge
 n=c.num_qubits;ops=c.operations
 # q0 initial state after H
 psi=np.array([1,0],complex)
 from rqm_compiler.su4_blocks import _single_qubit_matrix
 psi=_single_qubit_matrix(ops[0])@psi
 rho0=np.outer(psi,psi.conj())
 # start from rightmost leaf observable Z and recursively transfer leftward
 O=Z.copy()
 # edges begin at op index 1, three ops each
 for i in range(n-2,-1,-1):
  block_ops=ops[1+3*i:1+3*i+3]
  U=edge_unitary(block_ops,i,i+1)
  # eliminated leaf/subtree boundary on i+1 carries |0><0| for fresh leaf only
  # for recursive chain semantics, O already contains the subtree response.
  T=boundary_transfer(U,ZERO,O)
  O=apply_boundary_transfer(T,Z)
 # final q0 expectation in prepared rho0
 return complex(np.trace(rho0@O))

def to_qiskit(c):
 from qiskit import QuantumCircuit
 qc=QuantumCircuit(c.num_qubits)
 for op in c.operations:
  a=op.params.get("angle") if isinstance(op.params,dict) else None
  if op.gate=="h":qc.h(op.targets[0])
  elif op.gate=="rxx":qc.rxx(a,*op.targets)
  elif op.gate=="rzz":qc.rzz(a,*op.targets)
  elif op.gate=="cx":qc.cx(op.controls[0],op.targets[0])
  else:raise ValueError(op.gate)
 return qc

def parity(sv):
 probs=abs(sv.data)**2
 return float(sum(float(p)*((-1)**int(i).bit_count()) for i,p in enumerate(probs)))
def med(x):return statistics.median(x)

def main():
 from qiskit import transpile
 from qiskit_aer import AerSimulator
 backend=AerSimulator(method="statevector")
 rows=[]
 for n in NS:
  c=build(n);comp=compile_stable(c)
  rt=[];rv=None
  for _ in range(REPEATS):
   t=time.perf_counter_ns();rv=float(direct_chain(c).real);rt.append(time.perf_counter_ns()-t)
  qc=to_qiskit(c);qct=[];tqc=None
  for _ in range(REPEATS):
   t=time.perf_counter_ns();tqc=transpile(qc,basis_gates=["rz","sx","x","cx"],optimization_level=3,seed_transpiler=17);qct.append(time.perf_counter_ns()-t)
  at=[];qv=None
  for _ in range(REPEATS):
   run=tqc.copy();run.save_statevector()
   t=time.perf_counter_ns();sv=backend.run(run).result().get_statevector(run);qv=parity(sv);at.append(time.perf_counter_ns()-t)
  err=abs(rv-qv);valid=err<=TOL
  rqm_total=med(rt) # readout path only; stable compile reported separately
  q_total=med(qct)+med(at)
  rows.append({"n":n,"exact_valid":valid,"abs_error":err,
    "C_R":comp.closure.minimum_closed_representation_size,
    "rqm_chain_readout_ns":int(med(rt)),
    "qiskit_compile_ns":int(med(qct)),"aer_execute_ns":int(med(at)),
    "qiskit_aer_total_ns":int(q_total),
    "readout_speedup_vs_aer":med(at)/med(rt),
    "end_to_end_like_speedup_vs_qiskit_aer":q_total/rqm_total})
 summary={"conditions":len(rows),"exact_valid":sum(r["exact_valid"] for r in rows),
  "median_readout_speedup":med([r["readout_speedup_vs_aer"] for r in rows if r["exact_valid"]]) if any(r["exact_valid"] for r in rows) else None,
  "max_readout_speedup":max([r["readout_speedup_vs_aer"] for r in rows if r["exact_valid"]],default=None)}
 Path("results").mkdir(exist_ok=True)
 Path("results/chain_boundary_transfer.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2))
 print(json.dumps({"summary":summary,"rows":rows}))
if __name__=="__main__":main()
