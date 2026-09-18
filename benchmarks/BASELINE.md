# RQM Compiler 0.4 Benchmark Baseline

This directory defines the **frozen performance/coverage baseline** for the
0.4.0 development line.

## Baseline contract

The canonical comparison is RQM's public representation-aware planner versus:

- Qiskit 2.x transpiler, `optimization_level=3`, fixed `seed_transpiler=17`;
- basis `rz,sx,x,cx`;
- Qiskit Aer 0.17.x statevector execution;
- identical global-Z parity observable;
- exactness gate `abs(RQM - Aer) <= 1e-9`;
- median timings over fixed repeats;
- GitHub Actions Ubuntu runner, Python 3.12;
- each workflow hard-limited to 10 minutes.

Performance ratios are valid only for rows that pass the exactness gate.

## Frozen taxonomy

Seven families, each at n=4,8,12:

1. local rotations;
2. Clifford;
3. structured star;
4. structured chain;
5. Clifford+T;
6. fixed-depth 1D hardware-efficient;
7. seeded random sparse.

That is 21 headline coverage conditions.

The workload constructors, random seed, angles, Qiskit basis and transpiler
seed are frozen in `benchmarks/release_baseline.py`. Changes to any of those
constitute a new benchmark-baseline revision and must be documented.

## Metrics

Each row records:

- exactness / absolute error;
- RQM selected route;
- C_R;
- C_Q / work units;
- RQM and Qiskit gate count/depth;
- compile time;
- RQM readout time;
- Aer execution/readout time;
- end-to-end ratio;
- compile ratio.

The artifact contains JSON and CSV plus a Markdown summary suitable for release
notes.

## Interpretation

This suite measures the tested workload distribution only. It does not establish
a universal RQM speedup or polynomial simulation of arbitrary circuits.
Environment-sensitive timing results must always be accompanied by coverage and
exactness.
