# Compiler 0.3.7 coordinated package certification

Feature-frozen compiler runtime: `ea9ab1854776528fcbbccae3d474c01e799cbb3f`.
This pass changes dependency floors, packaging, release notes, and certification
only. The entanglement dependency required formatting and type annotations to
satisfy its existing lint/type gates; numerical algorithms and tolerances remain
unchanged. The default frontier cap remains four.

## Results

- Eight installed-wheel suites on Python 3.12: **2,941 passed, 11 skipped, zero
  failures/errors**; compiler alone: **930 passed**.
- Python 3.11, compiler plus entanglement installed wheels against released core
  and Qiskit 2.3: **1,090 passed, 2 skipped**. Python 3.12 ecosystem uses Qiskit
  2.5.2. Skips are retained in the XML; not every optional combination is covered.
- All wheel and source distributions pass `twine check`. Compiler and
  entanglement source distributions install into a fresh environment and run
  the documented public example. Rebuilt wheel payloads match certified wheels
  byte-for-byte (excluding RECORD); ZIP archive hashes can differ.
- Frozen taxonomy: **21/21 exact-valid**, maximum absolute error **2.11e-15**.
- Frozen boundary: **79/96 available**, every available answer passes the
  unchanged 1e-9 gate; maximum error **2.66e-15**.
- API offline corpora: **216/216 unitary**, **270/270 measurement**, exit zero,
  no network attempts, and `qualified_source_parity=true`. This is compatibility
  evidence, not a deployment or a full API-suite certification.

## Coverage change retained

The older native-kernel candidate answered 80/96 boundary conditions. The
integrated safety guard rejects one more condition: interleaved star, 12 qubits,
global Z, max_terms=64. Its qualified general-Pauli fallback exceeds the cap.
The same workload at max_terms=4096 remains available and exact. We do not raise
budgets, weaken tolerance, return partial results, or claim unchanged coverage.

Taxonomy and boundary runs overlapped. Their raw timings are retained as
**diagnostic measurements**, not new speedup claims. Earlier controlled native
kernel measurements remain historical, with their original provenance.

## Provenance and reproduction

`manifest.json` records every tested source commit/tree, installed-module path,
wheel SHA-256 and suite count. `summary.json` maps locally built compiler and
entanglement commits to GitHub commits with identical source trees. Later
release metadata/evidence commits must retain these tested runtime payloads.
`candidate-artifacts.zip` contains the exact eight wheels, the compiler and
entanglement source distributions, dependency constraints and manifests.

Install all archived wheels with the archived constraints. Use the compiler and
entanglement wheels on Python 3.11 and 3.12. Run the copied tests with
`--import-mode=importlib -o pythonpath=` from outside source trees. The adapter's
`scripts/certify_candidate.py` builds clean committed sources; its qualification
update adds the optional IBM SDK required by the mocked IBM regression test.
The initial failed run (missing that SDK) is preserved separately and never
represented as a pass.

Use the installed-wheel Python to run the compiler `benchmarks/job_taxonomy.py`
with REPEATS=5, RQM_CANDIDATE_WHEEL and RQM_CANDIDATE_COMMIT set; run the adapter
`scripts/scientific_boundary_benchmark.py` with the passed certification manifest.
Keep OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1.

API source revision: `72c57aef880e262654c1c2c761efd7bf028e4b74`. Apply only the
recorded `api-corpus-provenance.patch`: the unitary harness accepts a qualification
path instead of always loading an older archive. Workloads and comparisons are
unchanged. Run compiler `scripts/qualify_api_corpora.py` using the recorded API
revision, certification directory and a fresh output directory. Expected source
hashes come from the certified wheel ZIPs, then are compared with installed
modules before running either corpus. API-only dependencies are separately
recorded. Private API source and raw API artifacts are not included here.

## Publication order

1. Publish `rqm-entanglement==0.2.2` and verify it resolves from PyPI.
2. Merge compiler packaging/evidence and its generated **0.3.7** release PR.
3. Verify GitHub release assets, PyPI version and a clean public-package install.

Hardware studies, API deployment and further frontier research are separate.
