"""Acceptance benchmark for stable_prototype.

Only validates mechanisms intentionally admitted to the stable base.
"""
import json,time
from pathlib import Path
from rqm_compiler import Circuit
from rqm_compiler.stable_prototype import compile_stable,expectation_stable
from rqm_compiler.verification import _apply_gate_to_state

def dense(c):
 s=[0j]*(1<<c.num_qubits);s[0]=1+0j
 for op in c.operations:s=_apply_gate_to_state(s,op,c.num_qubits)
 return float(sum(abs(x)**2*((-1)**i.bit_count()) for i,x in enumerate(s)))

def star(n):
 c=Circuit(n);c.h(0)
 for i in range(1,n):
  c.rxx(0,i,.13+.003*i);c.rzz(0,i,-.071-.002*i);c.cx(0,i)
 for q in range(n):c.rz(q,.007*(q+1))
 return c

rows=[]
for n in (4,8,12,16):
 c=star(n)
 comp=compile_stable(c)
 t=time.perf_counter_ns();r=expectation_stable(c,"Z"*n);dt=time.perf_counter_ns()-t
 ref=dense(c)
 rows.append({"n":n,"method":r.method,"available":r.available,"error":abs(r.value.real-ref),
              "readout_ns":dt,"work_units":r.work_units,
              "C_R":comp.closure.minimum_closed_representation_size,
              "max_representation_level":comp.closure.maximum_representation_level})
summary={"cases":len(rows),"exact":sum(r["available"] and r["error"]<=1e-9 for r in rows),
         "all_direct":all(r["method"]=="direct_star_relational" for r in rows)}
Path("results").mkdir(exist_ok=True)
Path("results/stable_prototype.json").write_text(json.dumps({"summary":summary,"rows":rows},indent=2))
print(json.dumps({"summary":summary,"rows":rows}))
assert summary["exact"]==len(rows)
