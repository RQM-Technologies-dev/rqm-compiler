"""Validate direct star invariant against exact statevector, <10 min."""
import json,time
from pathlib import Path
from rqm_compiler import Circuit
from rqm_compiler.direct_readout import global_z_star
from rqm_compiler.verification import _apply_gate_to_state
def build(n):
 c=Circuit(n);c.h(0)
 for i in range(1,n):
  c.rxx(0,i,.13+.003*i);c.rzz(0,i,-.071-.002*i);c.cx(0,i)
 for q in range(n):c.rz(q,.007*(q+1))
 return c
def dense(c):
 s=[0j]*(1<<c.num_qubits);s[0]=1+0j
 for op in c.operations:s=_apply_gate_to_state(s,op,c.num_qubits)
 return float(sum(abs(x)**2*((-1)**i.bit_count()) for i,x in enumerate(s)))
rows=[]
for n in (4,8,12,16,18,20):
 c=build(n);t=time.perf_counter_ns();r=global_z_star(c);rt=time.perf_counter_ns()-t
 t=time.perf_counter_ns();v=dense(c);bt=time.perf_counter_ns()-t
 rows.append(dict(n=n,available=r.available,invariants=r.invariant_count,value=r.value.real,reference=v,error=abs(r.value.real-v),direct_ns=rt,reference_ns=bt,speedup=bt/rt))
Path("results").mkdir(exist_ok=True);Path("results/direct_readout.json").write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
assert all(x["available"] and x["error"]<=1e-9 for x in rows)
