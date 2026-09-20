# Compiler 0.3.7 feature freeze

Authorized release target: **0.3.7**, not 0.4.0. Runtime baseline:
`ea9ab1854776528fcbbccae3d474c01e799cbb3f`.

Only packaging, release metadata, documentation, and demonstrated release-gate
fixes are admitted. No new planner routes, increased frontier defaults,
scientific claims, or hardware jobs are part of this pass.

Dependency floor: released rqm-core 0.2.2 and coordinated rqm-entanglement
0.2.2. Publish entanglement before the compiler so a normal install resolves
the analytic transfer module. Existing evidence archives remain historical.

Qualification builds clean committed sources, tests installed wheels without
source overlays, runs the frozen taxonomy and numerical boundaries, validates
source distributions, and records revisions, hashes, environment and failures.
The older 0.4.0 release PR must be retargeted or superseded by 0.3.7.
