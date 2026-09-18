"""Fast exact-observable complexity smoke benchmark (<10 minute design target)."""
from __future__ import annotations
import csv,json,statistics,time
from pathlib import Path
from rqm_compiler import Circuit
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.adaptive_closure import account_closed_representation
from rqm_compiler.compile import optimize_circuit
from rqm_compiler.observables import ObservableExpansionExceeded
from rqm_compiler.structured_observables import expectation_structured
from rqm_compiler.verification import _apply_gate_to_state

def build(f,n,d):
 c=Circuit(n);c.h(0)
 for k in range(d):
  es=[(i,i+1) for i in range(n-1)] if f=="chain" else [(0,i) for i in range(1,n)]
  for j,(a,b) in enumerate(es): c.rxx(a,b,.13+.01*k+.002*j);c.rzz(a,b,-.071-.002*j);c.cx(a,b)
  for q in range(n): c.rz(q,.007*(q+1)*(k+1))
 return c
def dense(c):
 s=[0j]*(1<<c.num_qubits);s[0]=1+0j
 for op in c.operations:s=_apply_gate_to_state(s,op,c.num_qubits)
 return float(sum(abs(x)**2*((-1)**i.bit_count()) for i,x in enumerate(s)))
def main():
 rows=[]
 for f in ("chain","star"):
  for n in (4,8,12,16):
   for d in (1,4):
    c=build(f,n,d);p=AdaptiveCartanPolicy.aggressive(n)
    ts=[];qs=[];bs=[];out=None;rv=None;avail=True;peak=None
    for _ in range(3):
     t=time.perf_counter_ns();out,_=optimize_circuit(c,adaptive_policy=p);ts.append(time.perf_counter_ns()-t)
    cr=account_closed_representation(out).minimum_closed_representation_size
    try:
     for _ in range(3):
      t=time.perf_counter_ns();r=expectation_structured(out,"Z"*n,max_terms=250000);qs.append(time.perf_counter_ns()-t);rv=float(r.value.real);peak=r.peak_terms
    except ObservableExpansionExceeded: avail=False
    for _ in range(3):
     t=time.perf_counter_ns();bv=dense(c);bs.append(time.perf_counter_ns()-t)
    e2e=statistics.median(ts)+(statistics.median(qs) if qs else 0)
    err=abs(rv-bv) if avail else None
    rows.append(dict(family=f,n=n,depth=d,C_R=cr,available=avail,error=err,exact_valid=bool(avail and err<=1e-9),
      rqm_ns=int(e2e) if avail else None,reference_ns=int(statistics.median(bs)),speedup=(statistics.median(bs)/e2e if avail else None),peak_terms=peak))
 outp=Path("results");outp.mkdir(exist_ok=True)
 with (outp/"fast_complexity.csv").open("w",newline="") as h:
  w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 summary={"conditions":len(rows),"valid":sum(r["exact_valid"] for r in rows),"unavailable":sum(not r["available"] for r in rows),
 "speedup_gt_1":sum(r["exact_valid"] and r["speedup"]>1 for r in rows),"max_speedup":max((r["speedup"] for r in rows if r["exact_valid"]),default=None),
 "median_speedup":statistics.median([r["speedup"] for r in rows if r["exact_valid"]]) if any(r["exact_valid"] for r in rows) else None}
 (outp/"fast_complexity.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2));print(json.dumps(summary))
if __name__=="__main__":main()
