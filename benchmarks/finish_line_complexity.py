"""Repeated exact-observable finish-line benchmark.

Measures RQM against the transparent reference and Qiskit Aer on identical
circuit/query conditions. No RQM state-vector fallback is allowed.
"""
from __future__ import annotations
import argparse,csv,json,platform,statistics,time,tracemalloc
from pathlib import Path
from rqm_compiler import Circuit
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.adaptive_closure import account_closed_representation
from rqm_compiler.compile import optimize_circuit
from rqm_compiler.observables import expectation_pauli,ObservableExpansionExceeded
from rqm_compiler.verification import _apply_gate_to_state

FAMILIES=("chain","star","scrambled")
NS=(4,6,8,10,12,14,16,18,20)
DEPTHS=(1,2,4,8,16)
QUERIES=("global_parity","zz")
WARMUPS=2
REPEATS=9
TOL=1e-9
MAX_TERMS=250000

def build(family,n,depth):
 c=Circuit(n);c.h(0)
 for d in range(depth):
  if family=="chain": es=[(i,i+1) for i in range(n-1)]
  elif family=="star": es=[(0,i) for i in range(1,n)]
  else:
   es=[((3*i+5*d)%n,(7*i+3*d+1)%n) for i in range(max(1,n//2))]
   es=[(a,b if b!=a else (b+1)%n) for a,b in es]
  for k,(a,b) in enumerate(es):
   c.rxx(a,b,.13+.01*d+.003*k);c.rzz(a,b,-.071-.002*k);c.cx(a,b)
  for q in range(n):
   c.rz(q,.007*(q+1)*(d+1))
   if (q+d)%4==0:c.t(q)
 return c

def pauli(q,n):
 if q=="global_parity": return "Z"*n
 p=["I"]*n;p[0]=p[-1]="Z";return "".join(p)

def dense(c,q):
 state=[0j]*(1<<c.num_qubits);state[0]=1+0j
 for op in c.operations: state=_apply_gate_to_state(state,op,c.num_qubits)
 probs=[abs(x)**2 for x in state];n=c.num_qubits
 if q=="global_parity": return float(sum(p*((-1)**i.bit_count()) for i,p in enumerate(probs)))
 return float(sum(p*(1 if (i&1)==((i>>(n-1))&1) else -1) for i,p in enumerate(probs)))

def aer(c,q):
 from qiskit import QuantumCircuit
 from qiskit.quantum_info import Statevector,Pauli
 qc=QuantumCircuit(c.num_qubits)
 for op in c.operations:
  a=op.params.get("angle") if isinstance(op.params,dict) else None
  if op.gate=="h":qc.h(op.targets[0])
  elif op.gate=="t":qc.t(op.targets[0])
  elif op.gate=="rz":qc.rz(a,op.targets[0])
  elif op.gate=="rxx":qc.rxx(a,*op.targets)
  elif op.gate=="rzz":qc.rzz(a,*op.targets)
  elif op.gate=="cx":qc.cx(op.controls[0],op.targets[0])
  else: raise ValueError(op.gate)
 sv=Statevector.from_instruction(qc)
 # Qiskit Pauli labels are highest-qubit first; these queries are symmetric.
 return float(sv.expectation_value(Pauli(pauli(q,c.num_qubits))).real)

def timed(fn):
 tracemalloc.start();t=time.perf_counter_ns();v=fn();dt=time.perf_counter_ns()-t;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop();return v,dt,peak

def med(xs): return int(statistics.median(xs))
def mad(xs):
 m=statistics.median(xs);return int(statistics.median(abs(x-m) for x in xs))

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--out",type=Path,required=True);args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
 rows=[]
 for fam in FAMILIES:
  for n in NS:
   for depth in DEPTHS:
    c=build(fam,n,depth);policy=AdaptiveCartanPolicy.aggressive(n)
    # Compile warmups + measured repeats.
    for _ in range(WARMUPS): optimize_circuit(c,adaptive_policy=policy)
    cts=[];cps=[];out=None
    for _ in range(REPEATS):
     (o,_),dt,pk=timed(lambda: optimize_circuit(c,adaptive_policy=policy));out=o;cts.append(dt);cps.append(pk)
    cr=account_closed_representation(out).minimum_closed_representation_size
    for q in QUERIES:
     available=True;reason="";qts=[];qps=[];terms=[];rvals=[]
     try:
      for _ in range(WARMUPS): expectation_pauli(out,pauli(q,n),max_terms=MAX_TERMS)
      for _ in range(REPEATS):
       res,dt,pk=timed(lambda: expectation_pauli(out,pauli(q,n),max_terms=MAX_TERMS));qts.append(dt);qps.append(pk);terms.append(res.peak_terms);rvals.append(float(res.value.real))
     except ObservableExpansionExceeded:
      available=False;reason="observable_expansion_exceeded"
     # Reference and Aer repeats are independently measured.
     bts=[];bps=[];bvals=[];ats=[];aps=[];avals=[]
     for _ in range(WARMUPS): dense(c,q);aer(c,q)
     for _ in range(REPEATS):
      v,dt,pk=timed(lambda:dense(c,q));bvals.append(v);bts.append(dt);bps.append(pk)
      v,dt,pk=timed(lambda:aer(c,q));avals.append(v);ats.append(dt);aps.append(pk)
     bv=statistics.median(bvals);av=statistics.median(avals);rv=statistics.median(rvals) if rvals else None
     err_ref=abs(rv-bv) if rv is not None else None;err_aer=abs(rv-av) if rv is not None else None
     e2e=med(cts)+med(qts) if qts else None
     rows.append(dict(family=fam,n=n,depth=depth,query=q,statevector_dimension=1<<n,rqm_cr=cr,rqm_available=available,unavailable_reason=reason,
      rqm_compile_ns_median=med(cts),rqm_compile_ns_mad=mad(cts),rqm_query_ns_median=med(qts) if qts else None,rqm_query_ns_mad=mad(qts) if qts else None,
      rqm_end_to_end_ns=e2e,rqm_peak_memory_median=max(med(cps),med(qps)) if qps else med(cps),rqm_peak_terms=max(terms) if terms else None,
      reference_ns_median=med(bts),reference_ns_mad=mad(bts),reference_peak_memory_median=med(bps),
      aer_ns_median=med(ats),aer_ns_mad=mad(ats),aer_peak_memory_median=med(aps),
      rqm_value=rv,reference_value=bv,aer_value=av,abs_error_reference=err_ref,abs_error_aer=err_aer,
      exact_valid=bool(available and err_ref<=TOL and err_aer<=TOL),
      speedup_vs_reference=(med(bts)/e2e if e2e else None),speedup_vs_aer=(med(ats)/e2e if e2e else None)))
 payload=rows
 with (args.out/"finish_line.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(payload[0]));w.writeheader();w.writerows(payload)
 (args.out/"finish_line.json").write_text(json.dumps(payload,indent=2))
 valid=[r for r in rows if r["exact_valid"]]
 summary={"conditions":len(rows),"valid":len(valid),"unavailable":sum(not r["rqm_available"] for r in rows),
  "speedup_vs_reference_gt1":sum((r["speedup_vs_reference"] or 0)>1 for r in valid),
  "speedup_vs_aer_gt1":sum((r["speedup_vs_aer"] or 0)>1 for r in valid),
  "max_n_valid":max((r["n"] for r in valid),default=None),
  "median_speedup_vs_reference":statistics.median([r["speedup_vs_reference"] for r in valid]) if valid else None,
  "median_speedup_vs_aer":statistics.median([r["speedup_vs_aer"] for r in valid]) if valid else None,
  "environment":{"python":platform.python_version(),"platform":platform.platform(),"warmups":WARMUPS,"repeats":REPEATS,"tolerance":TOL,"max_terms":MAX_TERMS}}
 (args.out/"summary.json").write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
