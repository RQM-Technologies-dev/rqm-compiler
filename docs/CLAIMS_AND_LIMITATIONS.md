# RQM Compiler 0.4 — Claims and Limitations

This document is the public claim boundary for the 0.4 release line.

## Demonstrated

- The frozen release taxonomy has 21/21 exact-valid tested conditions across
  seven workload families at n=4,8,12 using an absolute-error gate of 1e-9.
- The validated chain route changes the tested n=4,8,12 query work sequence
  from 18/1,457/96,899 in the prior general route to 3/7/11.
- The validated fixed-depth 1D hardware-efficient route passes the documented
  stress suite at machine precision and keeps bounded intermediates in the
  tested fixed-depth cases.
- The public planner exposes representation/query and backend-capability
  telemetry.
- Clean wheel installs are qualified on Python 3.11 and 3.12; clean sdist
  installation is part of the release qualification gate.

Performance measurements are workload-, implementation-, machine- and
reference-dependent. Use the frozen benchmark artifacts for exact conditions.

## Architecture/design statements

RQM attempts to use the least-general validated exact representation that
preserves required information. It separates representation/query planning
from backend materialization and execution.

C_R and C_Q are compiler metrics; they are not universal computational
complexity classes.

## Not established

0.4 does **not** establish:

- universal RQM speedup over conventional compilers;
- polynomial classical simulation of arbitrary universal quantum computation;
- compact representation of arbitrary quantum states/circuits;
- a general complexity-theory separation or collapse;
- hardware quantum advantage;
- general photonic/CV modality support;
- correctness of experimental Quaternionic Spectral Transfer (QST) as a
  production representation.

Experimental results graduate only through the documented exact-reference,
recognizer and regression gates.
