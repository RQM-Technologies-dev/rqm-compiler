"""Adversarial phase-transition experiment for representation closure.

Maps C_R(n,d,p) over qubit count n, circuit depth d, and adversarial density p.
The metric remains compiler-working-representation closure capacity; it is not
an n-qubit state-dimension claim.
"""
from __future__ import annotations

import argparse, csv, json, math, random, statistics, time, tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path

from rqm_compiler import Circuit
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.adaptive_closure import account_closed_representation
from rqm_compiler.compile import optimize_circuit


@dataclass
class Result:
    family: str
    n: int
    depth: int
    density: float
    seed: int
    input_operations: int
    output_operations: int
    minimum_closed_representation_size: int
    maximum_representation_level: int
    representation_histogram: str
    promotion_count: int
    elapsed_ns_median: int
    peak_memory_bytes_median: int
    semantic_verified: bool
    output_error: float | None
    statevector_dimension: int
    statevector_bytes_complex128_theoretical: int
    closure_metric_scope: str
    closure_metric_exact_within_scope: bool
    quantum_state_dimension_claim: bool


def _pair(rng: random.Random, n: int) -> tuple[int, int]:
    a = rng.randrange(n); b = rng.randrange(n - 1)
    if b >= a: b += 1
    return a, b


def _local_layer(c: Circuit, rng: random.Random, p: float) -> None:
    for q in range(c.num_qubits):
        c.h(q)
        if rng.random() < p: c.t(q)
        else: c.s(q)
        if rng.random() < p: c.rz(q, rng.uniform(-math.pi, math.pi))


def random_clifford_t(n: int, depth: int, p: float, seed: int) -> Circuit:
    rng = random.Random(seed); c = Circuit(n)
    for _ in range(depth):
        _local_layer(c, rng, p)
        for _ in range(max(1, round(p * n))):
            a, b = _pair(rng, n); c.cx(a, b)
    return c


def all_to_all_random(n: int, depth: int, p: float, seed: int) -> Circuit:
    rng = random.Random(seed); c = Circuit(n)
    pairs = [(a,b) for a in range(n) for b in range(a+1,n)]
    for _ in range(depth):
        _local_layer(c, rng, p)
        rng.shuffle(pairs)
        k = max(1, min(len(pairs), round(p * len(pairs))))
        for a,b in pairs[:k]:
            gate = rng.randrange(4)
            if gate == 0: c.cx(a,b)
            elif gate == 1: c.rxx(a,b,rng.uniform(-math.pi,math.pi))
            elif gate == 2: c.ryy(a,b,rng.uniform(-math.pi,math.pi))
            else: c.rzz(a,b,rng.uniform(-math.pi,math.pi))
    return c


def random_su4_stress(n: int, depth: int, p: float, seed: int) -> Circuit:
    """SU(4)-stress via generic noncommuting 2Q windows that adaptive KAK may promote."""
    rng = random.Random(seed); c = Circuit(n)
    for _ in range(depth):
        for _ in range(max(1, round(p*n))):
            a,b = _pair(rng,n)
            # Deliberately exceed the adaptive source-cost threshold with a
            # noncommuting local/nonlocal window on one pair.
            c.rxx(a,b,rng.uniform(-math.pi,math.pi))
            c.ryy(a,b,rng.uniform(-math.pi,math.pi))
            c.rzz(a,b,rng.uniform(-math.pi,math.pi))
            c.cx(a,b); c.cz(a,b); c.iswap(a,b)
            c.rx(a,rng.uniform(-math.pi,math.pi)); c.ry(b,rng.uniform(-math.pi,math.pi))
            c.cx(b,a); c.rxx(a,b,rng.uniform(-math.pi,math.pi))
    return c


def hardware_efficient_random(n: int, depth: int, p: float, seed: int) -> Circuit:
    rng = random.Random(seed); c = Circuit(n)
    for layer in range(depth):
        for q in range(n):
            c.ry(q,rng.uniform(-math.pi,math.pi)); c.rz(q,rng.uniform(-math.pi,math.pi))
            if rng.random() < p: c.t(q)
        parity = layer & 1
        for q in range(parity,n-1,2):
            c.cx(q,q+1)
        # Long-range links increase connectivity continuously with p.
        for _ in range(round(p*n/2)):
            a,b=_pair(rng,n); c.cz(a,b)
    return c

FAMILIES = {
    "random_clifford_t": random_clifford_t,
    "all_to_all_random": all_to_all_random,
    "random_su4_stress": random_su4_stress,
    "hardware_efficient_random": hardware_efficient_random,
}


def _compile(c: Circuit):
    policy=AdaptiveCartanPolicy.aggressive(c.num_qubits)
    tracemalloc.start(); t=time.perf_counter_ns()
    out, report=optimize_circuit(c, adaptive_policy=policy)
    elapsed=time.perf_counter_ns()-t; _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
    return out,report,elapsed,peak


def _evidence(report):
    raw=getattr(report,"__dict__",{}); return raw.get("adaptive_routing",{}) or {}


def _verification(report):
    raw=getattr(report,"__dict__",{}); eq=raw.get("equivalence_report") or {}
    return bool(raw.get("equivalence_verified",False)), eq.get("max_abs_err")


def run(ns, depths, densities, seeds, repeats):
    rows=[]
    for n in ns:
      for d in depths:
       for p in densities:
        for seed in seeds:
         for family,builder in FAMILIES.items():
          c=builder(n,d,p,seed); times=[]; peaks=[]; out=report=None
          for _ in range(repeats):
            out,report,t,m=_compile(c); times.append(t); peaks.append(m)
          closure=account_closed_representation(out); ev=_evidence(report); verified,error=_verification(report)
          selected=ev.get("selected_windows",[])
          rows.append(Result(family,n,d,p,seed,len(c.operations),len(out.operations),
            closure.minimum_closed_representation_size,closure.maximum_representation_level,
            json.dumps(closure.representation_histogram,sort_keys=True),
            len(selected) if isinstance(selected,list) else 0,
            int(statistics.median(times)),int(statistics.median(peaks)),verified,
            float(error) if isinstance(error,(int,float)) else None,1<<n,(1<<n)*16,
            closure.scope,closure.exact_within_scope,closure.quantum_state_dimension_claim))
    return rows


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--max-qubits",type=int,default=16)
    ap.add_argument("--repeats",type=int,default=3); ap.add_argument("--csv",type=Path)
    ap.add_argument("--json",type=Path); args=ap.parse_args()
    ns=[x for x in (2,4,8,16,32) if x<=args.max_qubits]
    rows=run(ns,(1,2,4,8),(0.1,0.25,0.5,1.0),(1729,),max(1,args.repeats))
    payload=[asdict(r) for r in rows]
    if args.csv:
      args.csv.parent.mkdir(parents=True,exist_ok=True)
      with args.csv.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(payload[0])); w.writeheader(); w.writerows(payload)
    if args.json:
      args.json.parent.mkdir(parents=True,exist_ok=True); args.json.write_text(json.dumps(payload,indent=2))
    print(json.dumps(payload,indent=2))

if __name__=="__main__": main()
