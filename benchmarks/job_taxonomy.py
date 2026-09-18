"""Compiler job-taxonomy benchmark: stable RQM vs Qiskit/Aer.\n\nRerun after adding stable topology readout runtime dependency.

Explores representative compiler workloads while preserving an exactness-first
rubric. Each row records whether stable RQM can answer exactly, which readout
path it chose, and side-by-side compiler/runtime metrics.
"""
from __future__ import annotations
import json,statistics,time,random
from pathlib import Path
from rqm_compiler import Circuit,compile_representation_aware,plan_and_evaluate
from rqm_compiler.depth import circuit_depth

NS=(4,8,12)
REPEATS=2
TOL=1e-9

def local(n):
 c=Circuit(n)
 for q in range(n):
  c.h(q);c.rz(q,.07*(q+1));c.x(q if q%3==0 else q);c.rz(q,-.03*(q+1))
 return c

def clifford(n):
 c=Circuit(n)
 for q in range(n): c.h(q)
 for i in range(n-1): c.cx(i,i+1)
 for i in range(0,n-1,2): c.cz(i,i+1)
 return c

def star(n):
 c=Circuit(n);c.h(0)
 for i in range(1,n):
  c.rxx(0,i,.13+.003*i);c.rzz(0,i,-.071-.002*i);c.cx(0,i)
 for q in range(n):c.rz(q,.007*(q+1))
 return c

def chain(n):
 c=Circuit(n);c.h(0)
 for i in range(n-1):
  c.rxx(i,i+1,.11+.002*i);c.rzz(i,i+1,-.067-.001*i);c.cx(i,i+1)
 return c

def clifford_t(n):
 c=Circuit(n)
 for q in range(n):
  c.h(q)
  if q%2==0:c.t(q)
 for i in range(n-1):c.cx(i,i+1)
 for q in range(n):
  if q%3==0:c.t(q)
 return c

def hardware(n):
 c=Circuit(n)
 for layer in range(2):
  for q in range(n):
   c.rz(q,.021*(q+1)*(layer+1));c.rx(q,.017*(q+2)*(layer+1))
  for i in range(n-1):c.cx(i,i+1)
 return c

def random_sparse(n):
 rng=random.Random(1000+n);c=Circuit(n)
 for q in range(n):c.h(q)
 for k in range(max(2,n)):
  a,b=rng.sample(range(n),2)
  c.rxx(a,b,rng.uniform(-.2,.2));c.rzz(a,b,rng.uniform(-.2,.2))
  if k%2==0:c.cx(a,b)
 return c

FAMILIES={
 "local":local,"clifford":clifford,"star":star,"chain":chain,
 "clifford_t":clifford_t,"hardware_efficient":hardware,"random_sparse":random_sparse,
}

def to_qiskit(c):
 from qiskit import QuantumCircuit
 qc=QuantumCircuit(c.num_qubits)
 for op in c.operations:
  a=op.params.get("angle") if isinstance(op.params,dict) else None
  g=op.gate
  if g=="h":qc.h(op.targets[0])
  elif g=="x":qc.x(op.targets[0])
  elif g=="t":qc.t(op.targets[0])
  elif g=="rz":qc.rz(a,op.targets[0])
  elif g=="rx":qc.rx(a,op.targets[0])
  elif g=="rxx":qc.rxx(a,*op.targets)
  elif g=="rzz":qc.rzz(a,*op.targets)
  elif g=="cx":qc.cx(op.controls[0],op.targets[0])
  elif g=="cz":qc.cz(op.controls[0],op.targets[0])
  else: raise ValueError(g)
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
 for family,builder in FAMILIES.items():
  for n in NS:
   c=builder(n)
   rqmc=[];rqmr=[];rr=None;comp=None
   for _ in range(REPEATS):
    t=time.perf_counter_ns();comp=compile_representation_aware(c);rqmc.append(time.perf_counter_ns()-t)
    t=time.perf_counter_ns();rr=plan_and_evaluate(comp,"Z"*n);rqmr.append(time.perf_counter_ns()-t)
   qc=to_qiskit(c);qct=[];tqc=None
   for _ in range(REPEATS):
    t=time.perf_counter_ns();tqc=transpile(qc,basis_gates=["rz","sx","x","cx"],optimization_level=3,seed_transpiler=17);qct.append(time.perf_counter_ns()-t)
   runqc=tqc.copy();runqc.save_statevector()
   at=[];qv=None
   for _ in range(REPEATS):
    t=time.perf_counter_ns();sv=backend.run(runqc).result().get_statevector(runqc);qv=parity(sv);at.append(time.perf_counter_ns()-t)
   rqm_val=float(rr.value.real) if rr.available else None
   err=abs(rqm_val-qv) if rqm_val is not None else None
   valid=bool(rr.available and err<=TOL)
   rqm_e2e=med(rqmc)+med(rqmr) if rr.available else None
   q_e2e=med(qct)+med(at)
   rows.append({
    "family":family,"n":n,"rqm_available":rr.available,"rqm_method":rr.method,
    "exact_valid":valid,"abs_error":err,"C_R":comp.closure.minimum_closed_representation_size,
    "rqm_work_units":rr.work_units,"rqm_ops":len(comp.circuit.operations),"rqm_depth":circuit_depth(comp.circuit),
    "qiskit_ops":sum(tqc.count_ops().values()),"qiskit_depth":tqc.depth(),
    "rqm_compile_ns":int(med(rqmc)),"rqm_readout_ns":int(med(rqmr)) if rr.available else None,
    "qiskit_compile_ns":int(med(qct)),"aer_execute_ns":int(med(at)),
    "end_to_end_speedup":(q_e2e/rqm_e2e if valid else None),
    "compile_speedup":(med(qct)/med(rqmc) if valid else None),
   })
 summary={}
 for fam in FAMILIES:
  fr=[r for r in rows if r["family"]==fam]
  val=[r for r in fr if r["exact_valid"]]
  summary[fam]={
   "conditions":len(fr),"exact_valid":len(val),"coverage":len(val)/len(fr),
   "median_speedup":med([r["end_to_end_speedup"] for r in val]) if val else None,
   "max_speedup":max([r["end_to_end_speedup"] for r in val]) if val else None,
   "methods":sorted(set(r["rqm_method"] for r in fr)),
  }
 Path("results").mkdir(exist_ok=True)
 Path("results/job_taxonomy.json").write_text(json.dumps({"baseline":"0.4","summary":summary,"rows":rows},indent=2))
 import csv
 with Path("results/job_taxonomy.csv").open("w",newline="") as fh:
  w=csv.DictWriter(fh,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 md=["# RQM Compiler 0.4 benchmark baseline","","Exactness gate: abs(error) <= 1e-9.","",
     "| Family | Coverage | Median end-to-end ratio | Max ratio | Route(s) |",
     "| --- | ---: | ---: | ---: | --- |"]
 for fam,s in summary.items():
  md.append(f'| {fam} | {s["exact_valid"]}/{s["conditions"]} | {s["median_speedup"]:.3f}x | {s["max_speedup"]:.3f}x | {", ".join(s["methods"])} |')
 Path("results/BASELINE_RESULTS.md").write_text("\n".join(md)+"\n")
 print(json.dumps({"summary":summary,"rows":rows}))
 assert all(s["exact_valid"]==s["conditions"] for s in summary.values()), "release baseline requires 100% exact coverage"
if __name__=="__main__":main()
