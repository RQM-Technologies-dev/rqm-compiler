# 0.3.8 final acceptance of the frozen compiler

Acceptance date: September 20, 2026. Published baseline: **rqm-compiler 0.3.7**,
tag commit `8cdf4ec9a27d93d46c7daeb921fc10cc2491eb30`.
This is an acceptance milestone, not a claim that 0.3.8 or 0.4.0 is published.

## Scope and outcome

The compiler release requires reliable packages, preserved computational
semantics, reproducible evidence and accurate documentation. Real-hardware
testing is complete on IBM Marrakesh and Rigetti Cepheus-1-108Q via Braket.
Production API orchestration, durable job submission/retrieval, provider
integration and ORNL integration belong to the **OpenQSE-rqm-adapter / ORNL
workstream**. They do not gate compiler publication.

The [acceptance evidence](../evidence/0.3.8-acceptance-20260920/README.md)
contains the machine-readable checks and a consolidated evidence index.

## Released packages and artifact identity

- Public compiler 0.3.7, core 0.2.2 and entanglement 0.2.2 wheels have exactly
  the same runtime payloads and dependency declarations as the certified
  wheels. Their public source distributions contain the same runtime files.
- Downloads were verified against PyPI SHA-256 digests. The compiler wheel and
  sdist also match the GitHub release asset digests. Archive hashes differ from
  locally built candidates; matching runtime bytes establish code identity.
- Clean Python 3.11 installation: **929 passed, 1 skipped** in the 930-test
  compiler suite, with public Qiskit 2.3.1. Clean Python 3.12 installation:
  **930 passed**, with public Qiskit 2.5.2, rqm-qiskit 0.4.0, rqm-braket 0.2.2,
  rqm-circuits 0.2.1 and rqm-optimize 0.1.3. Dependency checks pass.
- A separate fresh installation of the public compiler sdist runs the public
  representation-aware example. No editable installation or local RQM source
  substitution is required.

The candidate's rqm-qiskit 0.4.1, rqm-braket 0.2.3 and OpenQSE adapter wheel
were part of the earlier eight-wheel certification, not public dependencies of
the compiler. Public bridge compatibility is checked separately here.

## Numerical and benchmark evidence

The [0.3.7 certification](../evidence/0.3.7-release-20260920/README.md) retains:

- eight installed-wheel suites: **2,941 passed, 11 skipped**;
- taxonomy **21/21 exact-valid**, maximum error **2.11e-15**;
- boundary **79/96 available**, all available answers within **1e-9**, maximum
  error **2.66e-15**;
- candidate API corpora: **216/216 unitary** and **270/270 measurement**.

The 21-condition taxonomy was repeated with the public packages and newly
resolved dependencies; all 21 remain exact-valid. Numerical thresholds,
workloads and five repetitions were unchanged. The only benchmark source edit
corrects a stale hardware-status metadata field; the offline benchmark does
not evaluate hardware completion. Raw timing values remain diagnostic, with no
new speedup claim. The unchanged runtime permits reuse of the prior bounded
coverage study and controlled performance studies, with their original
environments and limitations retained.

The interleaved-star 12-qubit global-Z case remains unavailable at a 64-term
fallback cap and available at 4096. Frontier default remains four. No tolerance,
budget or partial-result rule was relaxed.

## Completed real-hardware evidence

The original records are in `rqm-api` at revision
`72c57aef880e262654c1c2c761efd7bf028e4b74`; repository access is required for
the raw records. The public evidence index links the immutable paths and
retains summary measurements and hashes without provider account metadata.

| Stack | Completed workload | Result and limitations |
| --- | --- | --- |
| IBM Marrakesh | Job `danj7dg2fm4c73f49n9g`; 18 circuits, 512 shots each | Expected bounded phase signatures observed; all zero-parity references within simultaneous 95% intervals; native probability error at most 2.78e-16 before execution. |
| Rigetti Cepheus-1-108Q / Braket | 18 unique completed tasks, 512 shots each | Six predeclared nonzero-parity gates passed. All 18 raw-result hashes and shot counts rechecked against the retained analysis. |

Both stacks used superconducting devices. These are two distinct providers,
not evidence across two hardware modalities. All nine level-1/level-3 native
pairs matched on each stack; no native circuit reduction or hardware speedup
is demonstrated. Rigetti's ideal-zero diagnostic at index 16 excludes zero;
Z-population leakage was 16.21%–18.16%. These observations remain visible.

The hardware compiler snapshot is not byte-identical to the later public
compiler: 25 Python files match, eight changed and two were added. The evidence
records that difference. Offline replay of all **36 retained inputs** using the
public compiler reproduces the hardware snapshot's compiled operation lists.
IBM probability/measurement-order checks pass; all 18 Braket OpenQASM program
objects match the originally submitted programs. This is an applicability
check, not a new QPU run. Network attempts and new hardware jobs: zero.

## Separate integration finding

The frozen API Braket helper calls `translate_descriptors(...,
circuit_factory=...)`, which the public rqm-braket 0.2.2 interface does not
accept. The direct public descriptor translator passes all 18 replay cases.
The existing API helper requires the later bridge interface when the
OpenQSE/API integration is deployed. This remains an integration item; it is
not hidden by claiming the production API was certified against public bridges.
The new replay harness initially supplied a dictionary to the public Qiskit
translator; it was corrected to use its documented `Circuit` interface.

## Release configuration and next promotion

The one-time `release-as: 0.3.7` override is removed. The manifest and package
version remain at the actual published 0.3.7. Release Please can prepare the
normal patch successor, 0.3.8, from these acceptance/documentation changes;
merging this acceptance change does not publish that successor.

Promotion to 0.4.0 is a separate release decision. Its versioned artifact must
retain the accepted runtime and pass packaging/version checks. The currently
published rqm-qiskit 0.4.0 declares `rqm-compiler<0.4`, so consuming compiler
0.4.0 through that bridge will require a compatible bridge release or revised
constraint in the owning repository. This compatibility work does not add a
production hardware-integration requirement to the compiler.
