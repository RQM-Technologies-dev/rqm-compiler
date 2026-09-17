"""End-to-end quantum-simulation speedup gate.

Counts a speedup only when RQM and a conventional statevector simulator compute
the same observable from the same circuit to <=1e-9 absolute error.  RQM uses
Heisenberg-picture Pauli propagation and never materializes 2**n amplitudes.
"""
from __future__ import annotations
import argparse,csv,json,time,tracemalloc
from dataclasses import asdict,dataclass
from pathlib import Path
from rqm_compiler import Circuit
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.adaptive_closure import account_closed_representation
from rqm_compiler.compile import optimize_circuit
from rqm_compiler.observables import expectation_pauli,ObservableExpansionExceeded
from rqm_compiler.verification import _apply_gate_to_state

@dataclass
class Row:
 family:str;n:int;depth:int;query:str;accuracy_target:float
 rqm_compile_ns:int;rqm_compile_peak:int;rqm_cr:int;rqm_query_available:bool
 rqm_query_ns:int|None;rqm_query_peak:int|None;rqm_peak_terms:int|None;rqm_value:float|None
 baseline_ns:int;baseline_peak:int;baseline_value:float
 abs_error:float|None;end_to_end_rqm_ns:int|None;speedup:float|None;speedup_claim_valid:bool

def build(family,n,depth):
 c=Circuit(n);c.h(0)
 for d in range(depth):
  if family=='chain': es=[(i,i+1) for i in range(n-1)]
  elif family=='star': es=[(0,i) for i in range(1,n)]
  else:
   es=[((3*i+5*d)%n,(7*i+3*d+1)%n) for i in range(max(1,n//2))]
   es=[(a,b if b!=a else (b+1)%n) for a,b in es]
  for k,(a,b) in enumerate(es):
   c.rxx(a,b,.13+.01*d+.003*k);c.rzz(a,b,-.071-.002*k);c.cx(a,b)
  for q in range(n):
   c.rz(q,.007*(q+1)*(d+1))
   if (q+d)%4==0:c.t(q)
 return c

def statevector(c):
 state=[0j]*(1<<c.num_qubits);state[0]=1+0j
 for op in c.operations: state=_apply_gate_to_state(state,op,c.num_qubits)
 return state

def dense_observable(state,q,n):
 probs=[abs(x)**2 for x in state]
 if q=='global_parity':return float(sum(p*((-1)**i.bit_count()) for i,p in enumerate(probs)))
 if q=='zz':return float(sum(p*(1 if (i&1)==((i>>(n-1))&1) else -1) for i,p in enumerate(probs)))
 raise ValueError(q)

def pauli_for(q,n):
 if q=='global_parity':return 'Z'*n
 if q=='zz':
  p=['I']*n;p[0]=p[-1]='Z';return ''.join(p)
 raise ValueError(q)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--json',type=Path,required=True);args=ap.parse_args();rows=[]
 for fam in ('chain','star','scrambled'):
  for n in (4,6,8,10,12,14,16):
   for depth in (1,4,8):
    c=build(fam,n,depth);policy=AdaptiveCartanPolicy.aggressive(n)
    tracemalloc.start();t=time.perf_counter_ns();out,_=optimize_circuit(c,adaptive_policy=policy);ct=time.perf_counter_ns()-t;_,cp=tracemalloc.get_traced_memory();tracemalloc.stop();cr=account_closed_representation(out).minimum_closed_representation_size
    tracemalloc.start();t=time.perf_counter_ns();state=statevector(c);bt=time.perf_counter_ns()-t;_,bp=tracemalloc.get_traced_memory();tracemalloc.stop()
    for q in ('global_parity','zz'):
     bv=dense_observable(state,q,n); available=True;qt=qp=terms=None;rv=err=e2e=speed=None;valid=False
     try:
      tracemalloc.start();t=time.perf_counter_ns();res=expectation_pauli(out,pauli_for(q,n),max_terms=250000);qt=time.perf_counter_ns()-t;_,qp=tracemalloc.get_traced_memory();tracemalloc.stop()
      rv=float(res.value.real);terms=res.peak_terms;err=abs(rv-bv);e2e=ct+qt;speed=bt/e2e if e2e else None;valid=err<=1e-9
     except ObservableExpansionExceeded:
      if tracemalloc.is_tracing():tracemalloc.stop()
      available=False
     rows.append(Row(fam,n,depth,q,1e-9,ct,cp,cr,available,qt,qp,terms,rv,bt,bp,bv,err,e2e,speed,valid))
 payload=[asdict(r) for r in rows];args.csv.parent.mkdir(parents=True,exist_ok=True)
 with args.csv.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(payload[0]));w.writeheader();w.writerows(payload)
 args.json.write_text(json.dumps(payload,indent=2));print(json.dumps(payload))
if __name__=='__main__':main()
