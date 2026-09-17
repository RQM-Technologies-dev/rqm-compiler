# H1-H3 complexity benchmark

This experiment separates three claims that must not be conflated.

- **H1 — representational compression:** the RQM structural representation grows more slowly than the exact state-vector dimension `2^n` for a specified circuit family.
- **H2 — operational/computational compression:** measured compiler/evolution work grows correspondingly slowly with `n` under a fixed protocol.
- **H3 — closure compression:** increasing entanglement and non-Clifford structure does not force uncontrolled promotion into a representation whose size grows exponentially.

## Primary observable

The primary plot is

`minimum closed RQM representation size vs n`

with one curve per circuit family and `2^n` shown only as the conventional exact state-vector dimension reference.

The current compiler does **not** yet expose an exact minimum closed quantum-state dimension. Therefore the harness reports `minimum_closed_representation_size_proxy`, equal to the scalar-leaf size of the optimized canonical compiler IR. This is deliberately labeled a proxy. It is evidence about compiler representation scaling, not by itself evidence of efficient exact classical simulation of an arbitrary quantum state.

A future state-evolution implementation should replace the proxy with a representation-owned metric that counts the actual independent parameters needed to maintain closure under every operation.

## Circuit ladder

For each `n = 2, 4, 8, 16, 32, ...`, the harness evaluates:

1. `local_clifford` — local Clifford structure only.
2. `entangled_clifford` — Hadamards plus a CNOT chain.
3. `entangled_nonclifford` — entanglement plus T gates.
4. `deep_nonclifford` — repeated H/T/Rz layers and alternating entangling brickwork.

This ladder is deterministic so results are reproducible and complexity curves are not hidden by random-instance variance. Random seeded ensembles can be added later as a second experiment.

## Recorded metrics

Each row records:

- qubit count `n`;
- exact state-vector dimension `2^n`;
- input and output operation counts;
- RQM structural representation size;
- minimum-closed-representation proxy;
- median elapsed time across repeats;
- median Python peak allocated memory via `tracemalloc`;
- promotion count when adaptive evidence is exposed by `CompilerReport`;
- maximum structural representation level (1 local/quaternion, 2 two-qubit relation, 3 SU(4) block);
- semantic-verification status when exposed by the report;
- numerical output/reconstruction error when exposed by the report.

## Scientific interpretation

A polynomial-looking proxy curve is **not** sufficient to claim polynomial exact simulation. H1 is supported only for the measured representation and circuit families. H2 additionally requires a scaling analysis of runtime/work. H3 requires the representation metric to remain controlled as entanglement, non-Clifford density, and depth increase.

The strongest future result would require all of the following for the actual closed state representation, not merely compiler IR:

`M(n), T_update(n), C_R(n), T_measure(n) in poly(n)`

while reproducing conventional quantum mechanics within a predeclared error tolerance over circuit families broad enough to test the claimed scope.

## Run

```bash
python benchmarks/complexity_h1_h3.py --max-qubits 32 --repeats 7 --csv results/h1_h3.csv
```

The experiment intentionally permits `n=32` because the RQM compiler operates structurally rather than allocating a `2^n` state vector. Do not instantiate the conventional state vector at large `n`; `2^n` is recorded analytically as the reference dimension.
