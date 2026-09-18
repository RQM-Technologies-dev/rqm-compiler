# Finish-line complexity experiment

This protocol tests the bounded claim that RQM can reduce both representation cost and end-to-end exact-observable computation cost for identifiable circuit/query families.

## Experimental grid

Run deterministic and seeded ensembles across:

- families: chain, star, scrambled, random Clifford+T, hardware-efficient random;
- qubits: 4, 6, 8, 10, 12, 14, 16, 18, 20 where the reference completes within the workflow budget;
- depths: 1, 2, 4, 8, 16;
- seeds: 0..4 for randomized families;
- queries: global Z parity and distant ZZ, with selected amplitudes/marginals added only when a native exact RQM extractor exists;
- timing repeats: 9 measured repeats after 2 warmups.

## Required measurements

For every condition and repeat record:

- representation-owned C_R;
- RQM compile time, query time, and end-to-end time;
- RQM peak memory and peak exact-observable term count;
- promotion/demotion counts and maximum representation level when exposed;
- reference simulator time and peak memory;
- exact output values and absolute error;
- availability/resource-boundary reason.

Report median and MAD across repeats. A speedup is valid only when both paths compute the same requested output with absolute error <= 1e-9. Unavailable RQM conditions remain unavailable; no approximation or state-vector fallback is permitted.

## Baselines

Use two baselines on the same GitHub Actions runner:

1. the repository's transparent exact Python state-vector reference;
2. Qiskit Aer StatevectorSimulator (production baseline).

Time circuit preparation/evolution plus observable extraction consistently. Record package versions and runner metadata.

## Finish-line analysis

For each family/query/depth slice, fit scaling only over measured valid points. Report availability fraction, median C_R, median end-to-end time, memory, and speedup. Do not infer a universal complexity class from finite measurements.

Evidence for representational reduction requires C_R to grow materially slower than 2^n over the tested slice while exactness holds. Evidence for computational reduction requires the RQM end-to-end scaling trend to improve relative to both exact baselines over the same valid slice, not merely a single-point speedup.

The primary result must include failures and resource-boundary crossings so the tractable region is characterized rather than selected after the fact.
