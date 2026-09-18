"""Direct-readout scaling probe: no statevector, no Pauli expansion. <10 min."""
import json,time
from pathlib import Path
from rqm_compiler import Circuit
from rqm_compiler.direct_readout import global_z_star

def build(n):
 c=Circuit(n);c.h(0)
 for i in range(1,n):
  c.rxx(0,i,.13+.003*i);c.rzz(0,i,-.071-.002*i);c.cx(0,i)
 for q in range(n):c.rz(q,.007*(q+1))
 return c

rows=[]
for n in (8,16,32,64,128,256,512):
 c=build(n);times=[];r=None
 for _ in range(5):
  t=time.perf_counter_ns();r=global_z_star(c);times.append(time.perf_counter_ns()-t)
 rows.append({"n":n,"available":r.available,"invariants":r.invariant_count,
              "median_ns":sorted(times)[len(times)//2],"value_real":r.value.real,
              "representation":r.representation})
Path("results").mkdir(exist_ok=True)
Path("results/direct_scaling.json").write_text(json.dumps(rows,indent=2))
print(json.dumps(rows))
assert all(x["available"] and x["invariants"]==x["n"]-1 for x in rows)
