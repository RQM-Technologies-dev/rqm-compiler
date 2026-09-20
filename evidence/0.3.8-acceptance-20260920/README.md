# Frozen compiler final acceptance

This record verifies the published **0.3.7** artifacts for the **0.3.8 acceptance
milestone**. It does not publish another version. See
[the acceptance report](../../docs/RELEASE_0_3_8_ACCEPTANCE.md) for scope,
limitations and the separate OpenQSE/ORNL integration workstream.

## Evidence index

| Evidence | Record | Interpretation |
| --- | --- | --- |
| Public artifact identity | `artifact-verification.json`, `github-release-assets.json` | Compiler/core/entanglement runtime and dependency parity; PyPI/GitHub SHA-256 match for compiler. |
| Clean installations | `installed-provenance.json`, `constraints-*.txt`, `pip-check-*.txt` | Python 3.11/3.12 resolve public packages and import matching installed runtime bytes. |
| Compiler regression | `compiler-py311.xml`, `compiler-py312.xml` | 929 pass / 1 skip and 930 pass, respectively; no failures/errors. |
| Source distribution | `sdist-install.log`, `sdist-example.log`, `sdist-pip-check.txt` | Public sdist builds and runs the documented example in a third fresh environment. |
| Fresh taxonomy | `public-taxonomy.json`, `public-taxonomy.csv` | 21/21 exact-valid, max error 2.11e-15; five repetitions, diagnostic timings. |
| Earlier software certification | [0.3.7 evidence](../0.3.7-release-20260920/README.md) | Exact eight-wheel archive, 2,941 tests, 79/96 bounded coverage, 216/270 API corpora. Original candidate environments remain identified. |
| Controlled earlier performance | [adapter post-integration record](https://github.com/RQM-Technologies-dev/openqse-rqm-adapter/tree/c3a075f8397511968246262da45ea669e762af36/evidence/post-integration-2026-09-19) | Paired Cartan controls, application workloads and frontier limits; historical measurements only. |
| Hardware observations | `hardware-evidence.json` | IBM and Rigetti completed experiments, counts, statistical intervals, task identifiers and immutable original links. Raw provider records retain their original access restrictions. |
| Hardware applicability | `hardware-source-hashes.json`, `hardware-source-comparison.json`, `hardware-fixtures.json`, `hardware-replay.json` | Earlier source differs; 36 public-package offline replays reproduce retained operations, IBM probabilities/measurement order and submitted Braket programs. |
| Initial harness failure | `hardware-replay-initial.json` | Initial Qiskit replay supplied dict instead of documented Circuit; Braket API helper also exposes the recorded bridge interface mismatch. This is not a failed hardware experiment. |
| Overall results | `summary.json`, `SHA256SUMS` | Machine-readable acceptance summary and integrity manifest. |

The final replay uses each public bridge's documented interface. Braket's
`api_helper_compatible=false` remains visible in every corresponding row; it
does not mean that the direct descriptor replay failed. Production API behavior
is not certified by this compiler acceptance pass. The older full API corpus
used candidate bridges and must not be relabeled as a public-bridge result.

## Reproduction

Extract the wheels from the retained 0.3.7 `candidate-artifacts.zip`, then run:

```sh
python scripts/verify_published_release.py \
  --certified-wheels /path/to/certified/wheels --output /new/public-artifacts
```

Create a fresh Python 3.12 environment and install from public PyPI:

```sh
python -m pip install 'rqm-compiler[dev]==0.3.7' \
  'rqm-qiskit[simulator,qasm3,ibm]==0.4.0' 'rqm-braket==0.2.2' \
  'rqm-circuits==0.2.1' 'rqm-optimize==0.1.3'
python -m pip check
python -m pytest /path/to/rqm-compiler/tests --import-mode=importlib -o pythonpath=
python /path/to/rqm-compiler/examples/representation_aware.py
```

Run outside the source checkout; installed imports must resolve to site-packages.
The Python 3.11 control installs compiler dev dependencies and Qiskit >=2.3,<2.4.
The retained constraints record actual resolved versions, not required candidate
pins. To reproduce exact environments, use the appropriate constraints file.
Build/install the downloaded public sdist in another fresh environment and run
the example there.

For taxonomy, use the installed Python, `OPENBLAS_NUM_THREADS=1`,
`OMP_NUM_THREADS=1`, `REPEATS=5`, `RQM_CANDIDATE_WHEEL` pointing to the verified
public wheel, and `RQM_CANDIDATE_COMMIT=8cdf4ec9a27d93d46c7daeb921fc10cc2491eb30`.
Run `benchmarks/job_taxonomy.py` from a fresh output directory.

Hardware applicability replay requires authorized access to the recorded API
revision `72c57aef880e262654c1c2c761efd7bf028e4b74` and the API harness dependencies
in `constraints-py312-with-api-harness.txt`:

```sh
python scripts/replay_hardware_acceptance.py \
  --api /path/to/recorded-api-checkout \
  --fixtures evidence/0.3.8-acceptance-20260920/hardware-fixtures.json \
  --output /new/hardware-replay.json
```

The replay prohibits network operations and submits no hardware jobs. The
hardware evidence is consolidated from completed runs, not newly generated
QPU measurements. No API implementation source or credential is included here.
