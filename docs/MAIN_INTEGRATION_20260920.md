# Main integration validation — 2026-09-20

Integrated local qualification snapshot `381abbc` with upstream `286f8b8`.
Preserved upstream generalized transfers and bounded-frontier work, local query
input validation, and the qualified global-Z unsafe-placement fallback.

The first merge test run had 910 passes and 20 failures: unsafe interleaved
global-Z queries selected the new frontier route instead of the qualified
general-Pauli fallback, including two resource-cap cases. A first correction
was too broad (929 passes, one non-Z frontier routing failure). The final guard
is scoped to global-Z queries rejected by the star placement recognizer.
No tests, numerical tolerances, or frozen inputs were changed.

Final local compiler suite: **930 passed**. Command:

```sh
PYTHONPATH=src:../rqm-entanglement/src ../rqm-api/.venv-0.3.7b/bin/python -m pytest -q --disable-warnings
```

The API's unchanged offline corpora produced 270/270 passing measurement cases
and 216/216 passing unitary comparisons at the existing `1e-9` tolerance.
New outputs are retained separately under the API repository's
`artifacts/main-integration-20260920/`. The unitary harness exits nonzero because
its historical installed-candidate source-parity check is false for this newer
checkout; this is not a public-package qualification pass.

Approved release archives were not rebuilt or substituted. These integrated
sources require separate package qualification before publication. No hardware
jobs, deployment, GitHub Actions, or release transition were performed here.
