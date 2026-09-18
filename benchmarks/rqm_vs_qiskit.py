"""Stable RQM vs Qiskit/Aer side-by-side benchmark.

Scope: validated star circuits + global Z parity, where stable RQM uses the
proven direct relational readout. Qiskit transpiler (optimization_level=3) is
the standard compiler baseline and Aer statevector is the execution/readout
baseline. Results count only when outputs agree within 1e-9.
"""
from __future__ import annotations
import csv,json,statistics,time
from pathlib import Path
from rqm_compiler import Circuit
from rqm_compiler.stable_prototype import compile_stable,expectation_stable
from rqm_compiler.depth import circuit_depth

NS=(4,8,12,16,20)
REPEATS=3
TOL=1e-9

def build(n):
 c=Circuit(n);c.h(0)
 for i in range(1,n):
  c.rxx(0,i,.13+.003*i);c.rzz(0,i,-.071-.002*i);c.cx(0,i)
 for q in range(n):c.rz(q,.007*(q+1))
 return c

def to_qiskit(c):
 from qiskit import QuantumCircuit
 qc=QuantumCircuit(c.num_qubits)
 for op in c.operations:
  a=op.params.get("angle") if isinstance(op.params,dict) else None
  if op.gate=="h":qc.h(op.targets[0])
  elif op.gate=="rz":qc.rz(a,op.targets[0])
  elif op.gate=="rxx":qc.rxx(a,*op.targets)
  elif op.gate=="rzz":qc.rzz(a,*op.targets)
  elif op.gate=="cx":qc.cx(op.controls[0],op.targets[0])
  else:raise ValueError(f"unsupported benchmark gate {op.gate}")
 return qc

def parity_from_statevector(sv):
 probs=abs(sv.data)**2
 return float(sum(float(p)*((-1)**int(i).bit_count()) for i,p in enumerate(probs)))

def median(xs):return statistics.median(xs)

def main():
 from qiskit import transpile
 from qiskit_aer import AerSimulator
 backend=AerSimulator(method="statevector")
 rows=[]
 for n in NS:
  c=build(n)

  # RQM stable compiler + direct exact readout.
  rqmc=[];rqmr=[];rv=None;comp=None
  for _ in range(REPEATS):
   t=time.perf_counter_ns();comp=compile_stable(c);rqmc.append(time.perf_counter_ns()-t)
   t=time.perf_counter_ns();rr=expectation_stable(c,"Z"*n);rqmr.append(time.perf_counter_ns()-t);rv=float(rr.value.real)
  rqm_e2e=median(rqmc)+median(rqmr)
  rqm_ops=len(comp.circuit.operations);rqm_depth=circuit_depth(comp.circuit)

  # Qiskit compilation. Transpile to a common hardware-like IBM basis.
  qc=to_qiskit(c);qct=[];tqc=None
  for _ in range(REPEATS):
   t=time.perf_counter_ns()
   tqc=transpile(qc,basis_gates=["rz","sx","x","cx"],optimization_level=3,seed_transpiler=17)
   qct.append(time.perf_counter_ns()-t)
  qiskit_ops=sum(tqc.count_ops().values());qiskit_depth=tqc.depth()

  # Aer exact statevector execution + parity extraction.
  aer_times=[];qv=None
  for _ in range(REPEATS):
   runqc=tqc.copy();runqc.save_statevector()
   t=time.perf_counter_ns()
   sv=backend.run(runqc).result().get_statevector(runqc)
   qv=parity_from_statevector(sv)
   aer_times.append(time.perf_counter_ns()-t)
  qiskit_e2e=median(qct)+median(aer_times)
  err=abs(rv-qv);valid=err<=TOL
  rows.append({
   "n":n,"statevector_dimension":1<<n,"exact_valid":valid,"abs_error":err,
   "rqm_method":rr.method,"rqm_C_R":comp.closure.minimum_closed_representation_size,
   "rqm_work_units":rr.work_units,"rqm_ops":rqm_ops,"rqm_depth":rqm_depth,
   "rqm_compile_ns":int(median(rqmc)),"rqm_readout_ns":int(median(rqmr)),"rqm_end_to_end_ns":int(rqm_e2e),
   "qiskit_ops":int(qiskit_ops),"qiskit_depth":int(qiskit_depth),
   "qiskit_compile_ns":int(median(qct)),"aer_execute_readout_ns":int(median(aer_times)),"qiskit_end_to_end_ns":int(qiskit_e2e),
   "compile_speedup_qiskit_over_rqm":(median(qct)/median(rqmc) if valid else None),
   "execute_readout_speedup_aer_over_rqm":(median(aer_times)/median(rqmr) if valid else None),
   "end_to_end_speedup_qiskit_aer_over_rqm":(qiskit_e2e/rqm_e2e if valid else None),
   "gate_count_reduction_pct":((qiskit_ops-rqm_ops)/qiskit_ops*100 if valid and qiskit_ops else None),
   "depth_reduction_pct":((qiskit_depth-rqm_depth)/qiskit_depth*100 if valid and qiskit_depth else None),
  })
 valid=[r for r in rows if r["exact_valid"]]
 summary={
  "conditions":len(rows),"exact_valid":len(valid),
  "median_end_to_end_speedup":median([r["end_to_end_speedup_qiskit_aer_over_rqm"] for r in valid]),
  "max_end_to_end_speedup":max(r["end_to_end_speedup_qiskit_aer_over_rqm"] for r in valid),
  "median_execute_readout_speedup":median([r["execute_readout_speedup_aer_over_rqm"] for r in valid]),
  "largest_n":max(r["n"] for r in valid),
  "median_gate_count_reduction_pct":median([r["gate_count_reduction_pct"] for r in valid]),
  "median_depth_reduction_pct":median([r["depth_reduction_pct"] for r in valid]),
 }
 out=Path("results");out.mkdir(exist_ok=True)
 (out/"rqm_vs_qiskit.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2))
 with (out/"rqm_vs_qiskit.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(json.dumps({"summary":summary,"rows":rows}))
 assert len(valid)==len(rows), "all headline benchmark rows must pass exactness gate"
if __name__=="__main__":main()
