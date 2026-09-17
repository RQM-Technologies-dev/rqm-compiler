"""Global-information extraction benchmark.

Attack the point where dense simulation pays 2^n: extracting information from
entangled computations. This benchmark deliberately distinguishes:
  (A) compiler-owned compact representation / compilation cost,
  (B) exact dense-reference extraction cost,
  (C) whether a direct compact-representation extractor exists.

It must never label circuit inspection as state simulation.
"""
from __future__ import annotations
import argparse,csv,json,math,random,statistics,time,tracemalloc
from dataclasses import asdict,dataclass
from pathlib import Path
from rqm_compiler import Circuit
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.adaptive_closure import account_closed_representation
from rqm_compiler.compile import optimize_circuit
from rqm_compiler.verification import _circuit_unitary

@dataclass
class Row:
 family:str; n:int; rounds:int; seed:int; input_operations:int; output_operations:int
 cr:int; promotions:int; demotions:int; compile_ns:int; compile_peak_bytes:int
 query:str; query_size:int; extraction_path:str; extraction_ns:int|None; extraction_peak_bytes:int|None
 exact_value:str|None; reference_available:bool; reference_state_dimension:int
 reference_bytes_complex128:int; compact_direct_extractor_available:bool

def build(family,n,rounds,seed):
    rng=random.Random(seed); c=Circuit(n); c.h(0)
    for r in range(rounds):
        if family=='ghz_chain': pairs=[(i,i+1) for i in range(n-1)]
        elif family=='star': pairs=[(0,i) for i in range(1,n)]
        else:
            pairs=[(i,j) for i in range(n) for j in range(i+1,n)]; rng.shuffle(pairs); pairs=pairs[:max(1,n//2)]
        for k,(a,b) in enumerate(pairs):
            th=.19+.017*r+.009*k
            c.rxx(a,b,th); c.rzz(a,b,-.61*th); c.cx(a,b)
        for q in range(n):
            c.rz(q,.013*(q+1)*(r+1))
            if (q+r)%3==0:c.t(q)
    return c

def dense_column(c):
    # Supported verifier unitary path; only used for deliberately small reference n.
    u=_circuit_unitary(c); return [u[i][0] for i in range(len(u))]

def extract_reference(state,query,k):
    n=int(math.log2(len(state))); probs=[abs(x)**2 for x in state]
    if query=='amplitude_0': return state[0]
    if query=='amplitude_random': return state[(1<<n)-1]
    if query=='marginal_prefix':
        mask=(1<<k)-1; out=[0.0]*(1<<k)
        for i,p in enumerate(probs): out[i&mask]+=p
        return out
    if query=='zz_correlation':
        a,b=0,n-1; return sum(p*(1 if ((i>>a)&1)==((i>>b)&1) else -1) for i,p in enumerate(probs))
    if query=='global_parity': return sum(p*((-1)**i.bit_count()) for i,p in enumerate(probs))
    if query=='distribution': return probs
    raise ValueError(query)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--json',type=Path,required=True);args=ap.parse_args()
    rows=[]; queries=(('amplitude_0',1),('amplitude_random',1),('marginal_prefix',3),('zz_correlation',2),('global_parity',0),('distribution',0))
    for family in ('ghz_chain','star','random_overlap'):
      for n in (4,8,12,16,24,32,48,64):
       for rounds in (1,4,16):
        for seed in (1729,2718):
         c=build(family,n,rounds,seed);p=AdaptiveCartanPolicy.aggressive(n)
         tracemalloc.start();t=time.perf_counter_ns();out,report=optimize_circuit(c,adaptive_policy=p);compile_ns=time.perf_counter_ns()-t;_,compile_peak=tracemalloc.get_traced_memory();tracemalloc.stop()
         cl=account_closed_representation(out); ar=report.adaptive_routing
         # Exact reference intentionally capped: dense unitary construction scales as 4^n.
         state=None; ref_n=(n<=8)
         if ref_n: state=dense_column(out)
         for query,k in queries:
            path='no_compact_direct_extractor'; ns=peak=None; value=None
            if state is not None:
                tracemalloc.start();t=time.perf_counter_ns();v=extract_reference(state,query,min(k,n));ns=time.perf_counter_ns()-t;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop();value=json.dumps(v,default=lambda z:{'real':z.real,'imag':z.imag});path='dense_exact_reference'
            rows.append(Row(family,n,rounds,seed,len(c.operations),len(out.operations),cl.minimum_closed_representation_size,int(ar.get('promotion_count',0)),int(ar.get('demotion_count',0)),compile_ns,compile_peak,query,k,path,ns,peak,value,ref_n,1<<n,(1<<n)*16,False))
    payload=[asdict(x) for x in rows];args.csv.parent.mkdir(parents=True,exist_ok=True)
    with args.csv.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(payload[0]));w.writeheader();w.writerows(payload)
    args.json.write_text(json.dumps(payload,indent=2));print(json.dumps(payload))
if __name__=='__main__':main()
