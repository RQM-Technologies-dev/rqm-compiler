# Desktop handoff

All implementation changes are on main in rqm-compiler, rqm-entanglement,
and openqse-rqm-adapter. Pull main in each repository before continuing.

## Integrated runtime

- Compiler integration: `7b79a2281971afc946ccfd75a7863793d0bd5001`.
- Entanglement integration: `8b0c4e2e0cfdc3a7bec9ab34a258264cd69bd3c1`.
- Adapter integration plus follow-up probes: `439b86e775516d88a529843dd0bfca6e267ae765`.

Quaternion observable updates, analytic hinge/CX star and chain transfers,
canonical Cartan promotion bypass, real frontier coefficients, bounded
planning, verified regional compilation, and batch query reuse are integrated.
The default frontier cap remains four. Package versions were not bumped;
there is no new release tag. Use source commits or exact wheel hashes to
identify a candidate.

## Evidence

The adapter repository contains:

- `evidence/native-kernels-2026-09-19/`: 2,330 passed / 11 skipped ecosystem
  certification, exact eight-wheel archive, constraints, raw benchmark data.
- `evidence/post-integration-2026-09-19/`: paired Cartan controls, application
  energies, wider frontiers, merge-tree provenance, and 64 passing adapter tests.
- `scripts/certify_candidate.py`: build and test clean pinned sibling sources.
- `scripts/probe_application_frontiers.py`: reproduce the follow-up experiments.

Run certification from the parent of sibling repository checkouts. Extend
adapter `candidate-revisions.json` with the exact adapter HEAD under the key
`openqse-rqm-adapter`, and pass that JSON to `--revisions`. Use a fresh output
folder and `--constraints openqse-rqm-adapter/candidate-constraints.txt`.
The certification script takes `--sources`, `--output`, and `--revisions`.
Use its installed-wheel venv for benchmarks, with OPENBLAS_NUM_THREADS=1 and
OMP_NUM_THREADS=1; benchmark scripts document their CLI options.

## What the follow-up established

The earlier 6% noncanonical Cartan slowdown did not reproduce in three
fresh-process paired experiments. No speculative runtime patch was applied.
Application probes cover weighted MaxCut QAOA, Heisenberg quenches, and Ising
variational energies at 6/10/14 qubits. Some deeper energy workloads remain
unavailable under caps 4/8 and the 128-term fallback budget; incomplete energies
are never reported as complete. Width ten was evaluated accurately with about
38 MB traced peak memory. Width 12/16/24 schedules were rejected before numeric
evaluation. Tensor size remains exponential in frontier width.

Further work can target ordering and query reuse on the incomplete application
cases. Increasing the default cap is not justified by these measurements alone.
Compiler computation remains separate from API orchestration and hardware routes.
