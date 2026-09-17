"""Experiment: does overlap topology, rather than raw depth, force RQM promotion?

Keeps the two-qubit interaction budget comparable while varying interaction graph:
disjoint matching -> chain -> star -> random regular-ish -> dense/all-to-all.
At small n, also forces global observables against an exact statevector reference.
"""
from __future__ import annotations
import argparse,csv,json,math,random,statistics,time,tracemalloc
from dataclasses import asdict,dataclass
from pathlib import Path
import numpy as np
from rqm_compiler import Circuit
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.adaptive_closure import account_closed_representation
from rqm_compiler.compile import optimize_circuit
from rqm_compiler.verification import _simulate_statevector

@dataclass
class Row:
 topology:str; n:int; rounds:int; seed:int; edges_per_round:int; unique_edges:int; max_degree:int
 input_operations:int; output_operations:int; cr:int; max_representation_level:int
 promotions:int; demotions:int; retained:int; root_causes:str; runtime_ns:int; peak_memory_bytes:int
 statevector_dimension:int; global_observable_mode:str; global_observable_runtime_ns:int|None
 parity_z_exact:float|None; parity_z_error:float|None; amplitude_0_exact:float|None; amplitude_0_error:float|None

def edges(topology,n,rng,k):
    if topology=='disjoint':
        base=[(i,i+1) for i in range(0,n-1,2)]
    elif topology=='chain': base=[(i,i+1) for i in range(n-1)]
    elif topology=='star': base=[(0,i) for i in range(1,n)]
    elif topology=='random':
        allp=[(i,j) for i in range(n) for j in range(i+1,n)]; rng.shuffle(allp); base=allp
    else: base=[(i,j) for i in range(n) for j in range(i+1,n)]
    if not base:return []
    return [base[i%len(base)] for i in range(k)]

def build(topology,n,rounds,seed):
    rng=random.Random(seed); c=Circuit(n); k=max(1,n//2); used=set(); deg=[0]*n
    c.h(0)
    for r in range(rounds):
        es=edges(topology,n,rng,k)
        for idx,(a,b) in enumerate(es):
            theta=.17+.013*r+.007*idx
            # same local gate budget across topologies; only overlap graph changes
            c.rxx(a,b,theta); c.rzz(a,b,-.7*theta); c.cx(a,b)
            used.add(tuple(sorted((a,b))));deg[a]+=1;deg[b]+=1
        for q in range(n):
            c.rz(q,.011*(r+1)*(q+1));
            if (q+r)%3==0:c.t(q)
    return c,k,len(used),max(deg,default=0)

def exact_observables(c):
    t=time.perf_counter_ns(); state=_simulate_statevector(c); elapsed=time.perf_counter_ns()-t
    probs=np.abs(state)**2; n=c.num_qubits
    signs=np.array([(-1)**(int(i).bit_count()) for i in range(len(state))],dtype=float)
    parity=float(np.dot(probs,signs)); amp0=float(probs[0]); return elapsed,parity,amp0

def run(topology,n,rounds,seed):
    c,k,unique,maxdeg=build(topology,n,rounds,seed); policy=AdaptiveCartanPolicy.aggressive(n)
    tracemalloc.start();t=time.perf_counter_ns();out,report=optimize_circuit(c,adaptive_policy=policy);runtime=time.perf_counter_ns()-t;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    closure=account_closed_representation(out); ar=report.adaptive_routing
    mode='not_materialized'; ort=None; parity=perr=amp0=aerr=None
    if n<=16:
        mode='exact_statevector_reference'; ort,parity,amp0=exact_observables(out)
        rt,rp,ra=exact_observables(c)[1:]
        perr=abs(parity-rp);aerr=abs(amp0-ra)
    return Row(topology,n,rounds,seed,k,unique,maxdeg,len(c.operations),len(out.operations),closure.minimum_closed_representation_size,closure.maximum_representation_level,int(ar.get('promotion_count',0)),int(ar.get('demotion_count',0)),int(ar.get('retained_count',0)),json.dumps(ar.get('root_cause_histogram',{}),sort_keys=True),runtime,peak,1<<n,mode,ort,parity,perr,amp0,aerr)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--json',type=Path,required=True);args=ap.parse_args()
    rows=[]
    for n in (4,8,16,32):
      for rounds in (1,2,4,8,16):
       for seed in (1729,2718,31415):
        for topology in ('disjoint','chain','star','random','dense'):
         rows.append(run(topology,n,rounds,seed))
    payload=[asdict(x) for x in rows];args.csv.parent.mkdir(parents=True,exist_ok=True)
    with args.csv.open('w',newline='') as f:
      w=csv.DictWriter(f,fieldnames=list(payload[0]));w.writeheader();w.writerows(payload)
    args.json.write_text(json.dumps(payload,indent=2));print(json.dumps(payload))
if __name__=='__main__':main()
