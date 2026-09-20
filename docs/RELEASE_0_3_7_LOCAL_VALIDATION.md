# 0.3.7 local validation and capability exploration

Run all compiler verification and benchmarks locally. Do not dispatch GitHub
Actions for this program. Save the revision, local patch hash, package versions,
machine information, seeds and raw measurements with every result.

## First priority: semantic preservation across the complete lowering path

Compare each original circuit against representation-aware compilation followed
by provider lowering using an independent Qiskit statevector/operator reference.
Cover single-qubit rotations, controlled gates, Bell and GHZ states, asymmetric
computational basis states, nonlocal wire indices, and multiple measurement
registers. Include angles near zero, pi and 2*pi and phase-sensitive X/Y
observables. Z-basis Bell counts alone cannot establish phase preservation or
detect reversed bit order. Compare operators up to global phase only where the
contract permits it; test controlled composition where relative phase matters.

Use fixed seeds and small exhaustive cases. Require errors <= 1e-9 for exact
reference comparisons. Test descriptor roundtrips, deterministic normalization,
invalid-input rejection, and budget/fallback behavior separately.

## Most informative performance experiment: paired compilation

Compare original -> Qiskit targeting with original -> RQM -> identical Qiskit
targeting. Hold the backend target snapshot, basis, coupling map, optimization
level and transpiler seed fixed. Verify ideal equivalence before including a
row in the performance comparison. Report RQM planning time, downstream
transpilation time and total compile time separately, plus final native two-qubit
gate count, depth and qubit mapping. Do not compare high-level RQM operation
counts directly with decomposed hardware gates.

Exercise star, chain, fixed-depth hardware-efficient, QFT-like, variational,
random sparse and dense/unstructured circuits across sizes and depths. Keep a
held-out seed set, warmups and at least ten repetitions for timing; retain raw
samples and report median and spread. Include regressions and unavailable
routes. Separate exact observable-query timing from hardware compilation timing:
these produce different outputs and support different claims.

## Explore the representation boundary

For the frozen random-sparse family, profile the first query-expansion event.
Vary graph density, depth and observable support independently. Record C_R,
C_Q, peak intermediates, time, memory, selected route and fallback reason.
Evaluate validated contraction-order machinery against the frozen baseline.
Only graduate improvements that preserve the independent exactness gate on
held-out cases; keep slower cases in the report.

## Hardware evidence after offline acceptance

The currently authorized hardware scope is one 100-shot Bell canary on IBM's
Open-plan instance. This establishes a bounded integration observation.
It is insufficient to measure a compiler performance advantage or certify
entanglement from Z-basis counts alone.

A subsequent hardware study should interleave paired original/compiled
circuits on the same backend and layout, record calibration and execution time,
and compare distributions with uncertainty intervals. Include phase-sensitive
measurement bases and asymmetric readouts. Specify shots and total allocation
before expanding hardware execution. A second hardware stack remains a
separate 0.3.7C acceptance requirement.
