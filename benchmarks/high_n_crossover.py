"""High-n exact-observable crossover probe. Hard target: <10 minutes."""
from __future__ import annotations
import json,statistics,time
from pathlib import Path
from rqm_compiler import Circuit
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.compile import optimize_circuit
from rqm_compiler.structured_observables import expectation_structured,ObservableExpansionExceeded
from rqm_compiler.verification import _apply_gate_to_state

def build(n):
 c=Circuit(n);c.h(0)
 # Star/depth-1 is the previously exact-valid crossover family.
 for i in range(1,n):
  c.rxx(0,i,.13+.003*i);c.rzz(0,i,-.071-.002*i);c.cx(0,i)
 for q in range(n):c.rz(q,.007*(q+1))
 return c
def dense(c):
 s=[0j]*(1<<c.num_qubits);s[0]=1+0j
 for op in c.operations:s=_apply_gate_to_state(s,op,c.num_qubits)
 return float(sum(abs(x)**2*((-1)**i.bit_count()) for i,x in enumerate(s)))
def main():
 rows=[]
 # 18/20 remain feasible for exact reference on hosted runner; 22 is attempted
 # only if prior point stays within a conservative elapsed budget.
 start=time.monotonic()
 for n in (18,20,22):
  if time.monotonic()-start>420:break
  c=build(n);p=AdaptiveCartanPolicy.aggressive(n)
  t=time.perf_counter_ns();out,_=optimize_circuit(c,adaptive_policy=p);ct=time.perf_counter_ns()-t
  try:
   t=time.perf_counter_ns();r=expectation_structured(out,"Z"*n,max_terms=250000);qt=time.perf_counter_ns()-t;rv=float(r.value.real)
  except ObservableExpansionExceeded:
   rows.append({"n":n,"available":False});continue
  t=time.perf_counter_ns();bv=dense(c);bt=time.perf_counter_ns()-t
  e2e=ct+qt;rows.append({"n":n,"available":True,"error":abs(rv-bv),"rqm_ns":e2e,"reference_ns":bt,"speedup":bt/e2e,"peak_terms":r.peak_terms})
 Path("results").mkdir(exist_ok=True);Path("results/high_n.json").write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
if __name__=="__main__":main()
