# 0.3.5 Cross-Stack Release Qualification

This is the acceptance ledger for the RQM Compiler 0.3.5 milestone on the path
to 0.4.0.

## Required stack

| Component | Required evidence | Current state |
| --- | --- | --- |
| rqm-core | shared operator math CI | qualified |
| rqm-entanglement | nonlocal ownership/relational CI | qualified |
| rqm-compiler | Python 3.11/3.12 CI + distribution build | qualified |
| rqm-qiskit | compiler-0.4 candidate qualification | qualified |
| rqm-braket | compiler-0.4 candidate + RXX/RYY/RZZ lowering | validating |
| rqm-pennylane | compiler-0.4 candidate qualification | qualified |
| openqse-rqm-adapter | clean source ecosystem demonstration using public planner | qualified |
| quantum-compiler-api | locked production install + candidate overlay | validating |
| rqm-studio | UI CI + hosted explanation validation | qualified |

## Package acceptance

The canonical `0.3.5 Release qualification` workflow must prove:

- source regression suite;
- wheel build and clean installation on Python 3.11 and 3.12;
- sdist build and clean installation;
- public `compile_representation_aware` import and execution from the installed
  wheel rather than the source checkout;
- public `BackendCapabilityModel` availability from installed artifacts;
- dependency resolution from package metadata.

## Cross-stack policy

A repository is qualified only when its integration test exercises the actual
0.4-development public API or the stable external descriptor contract it is
supposed to consume. Import-only checks are insufficient.

Candidate Git SHAs are acceptable for qualification but must be replaced by
released package constraints before the final 0.3.8/0.4.0 acceptance gate.

Python 3.10 bridge support may remain where independently useful, but
`rqm-compiler 0.4` itself requires Python 3.11+.

## Exit gate

0.3.5 is complete when every mandatory row above is qualified and the clean
wheel/sdist workflow is green. Any bridge incompatibility found during
qualification is fixed in its owning bridge rather than hidden by weakening
compiler semantics.
