"""End-to-end quantum-simulation speedup gate.

A speedup is counted ONLY when RQM and a conventional simulator compute the
same quantum quantity to the same accuracy from the same circuit, including
all representation/extraction work. Compiler IR compactness alone cannot pass.

Phase 1 uses exact statevector truth at tractable n and records the RQM-native
query path as unavailable until implemented. This makes the missing capability
an executable research gate rather than silently substituting dense fallback.
"""
from __future__ import annotations
import argparse,csv,json,math,time,tracemalloc
from dataclasses import asdict,dataclass
from pathlib import Path
from rqm_compiler import Circuit
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.adaptive_closure import account_closed_representation
from rqm_compiler.compile import optimize_circuit
from rqm_compiler.verification import _circuit_unitary

@dataclass
class Row:
 family:str;n:int;depth:int;query:str;accuracy_target:float
 rqm_compile_ns:int;rqm_compile_peak:int;rqm_cr:int;rqm_query_available:bool
 rqm_query_ns:int|None;rqm_query_peak:int|None;rqm_value:str|None
 baseline_available:bool;baseline_ns:int|None;baseline_peak:int|None;baseline_value:str|None
 abs_error:float|None;end_to_end_rqm_ns:int|None;speedup:float|None;speedup_claim_valid:bool

def build(family,n,depth):
 c=Circuit(n);c.h(0)
 for d in range(depth):
  if family=='chain': es=[(i,i+1) for i in range(n-1)]
  elif family=='star': es=[(0,i) for i in range(1,n)]
  else: es=[((3*i+5*d)%n,(7*i+3*d+1)%n) for i in range(max(1,n//2))];es=[(a,b if b!=a else (b+1)%n) for a,b in es]
  for k,(a,b) in enumerate(es):c.rxx(a,b,.13+.01*d+.003*k);c.rzz(a,b,-.071-.002*k);c.cx(a,b)
  for q in range(n):c.rz(q,.007*(q+1)*(d+1));c.t(q) if (q+d)%4==0 else None
 return c

def dense_state(c):
 u=_circuit_unitary(c);return [u[i][0] for i in range(len(u))]

def query(state,q):
 probs=[abs(x)**2 for x in state];n=int(math.log2(len(state)))
 if q=='amplitude':return state[-1]
 if q=='global_parity':return sum(p*((-1)**i.bit_count()) for i,p in enumerate(probs))
 if q=='zz':return sum(p*(1 if (i&1)==((i>>(n-1))&1) else -1) for i,p in enumerate(probs))
 if q=='marginal3':
  out=[0.0]*8
  for i,p in enumerate(probs):out[i&7]+=p
  return out
 raise ValueError(q)

def scalar_error(a,b):
 if isinstance(a,list):return max(abs(x-y) for x,y in zip(a,b))
 return abs(a-b)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--json',type=Path,required=True);args=ap.parse_args();rows=[]
 for fam in ('chain','star','scrambled'):
  for n in (4,6,8):
   for depth in (1,4,8):
    c=build(fam,n,depth);p=AdaptiveCartanPolicy.aggressive(n)
    tracemalloc.start();t=time.perf_counter_ns();out,_=optimize_circuit(c,adaptive_policy=p);ct=time.perf_counter_ns()-t;_,cp=tracemalloc.get_traced_memory();tracemalloc.stop();cr=account_closed_representation(out).minimum_closed_representation_size
    tracemalloc.start();t=time.perf_counter_ns();state=dense_state(c);bt=time.perf_counter_ns()-t;_,bp=tracemalloc.get_traced_memory();tracemalloc.stop()
    for q in ('amplitude','global_parity','zz','marginal3'):
     bv=query(state,q)
     # Critical scientific gate: there is not yet an RQM-native state-query API.
     rows.append(Row(fam,n,depth,q,1e-9,ct,cp,cr,False,None,None,None,True,bt,bp,json.dumps(bv,default=lambda z:{'real':z.real,'imag':z.imag}),None,None,None,False))
 payload=[asdict(r) for r in rows];args.csv.parent.mkdir(parents=True,exist_ok=True)
 with args.csv.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(payload[0]));w.writeheader();w.writerows(payload)
 args.json.write_text(json.dumps(payload,indent=2));print(json.dumps(payload))
if __name__=='__main__':main()
