# Changelog

## [0.3.0] — Verified Regional Optimization

- Added `optimize_circuit_regions` for deterministic contiguous regions of at
  most three qubits.
- Added all-or-nothing proof gating: if any changed region is not verified, the
  exact original circuit structure is returned and every tentative change is
  withheld.
- Added JSON-safe `RegionalCompilerReport`, `RegionalOptimizationRecord`, and
  `CompilerReport.to_dict()` interfaces.
- Preserved measurements and barriers as exact region boundaries without
  introducing backend-specific objects.

## [0.2.2](https://github.com/RQM-Technologies-dev/rqm-compiler/compare/v0.2.1...v0.2.2) (2026-07-29)


### Bug Fixes

* dispatch protected publication by repository ([#20](https://github.com/RQM-Technologies-dev/rqm-compiler/issues/20)) ([64eaae9](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/64eaae9178a36115f4f0756b28ec7da60798b652))

## [0.2.1](https://github.com/RQM-Technologies-dev/rqm-compiler/compare/v0.2.0...v0.2.1) (2026-07-29)


### Bug Fixes

* dispatch release pull request CI reliably ([#16](https://github.com/RQM-Technologies-dev/rqm-compiler/issues/16)) ([42a50c9](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/42a50c997512508ec54836353e4ca393b7c9dc66))
* keep generated releases verifiable ([#18](https://github.com/RQM-Technologies-dev/rqm-compiler/issues/18)) ([356af3d](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/356af3d58ca3bd242087ab32a5bc73d33609d179))
* verify iSWAP optimization candidates ([#19](https://github.com/RQM-Technologies-dev/rqm-compiler/issues/19)) ([4ae864b](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/4ae864b21e13a8b5dec1d7ca980d9236dad4f2a6))
