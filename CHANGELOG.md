# Changelog

## [0.3.8](https://github.com/RQM-Technologies-dev/rqm-compiler/compare/v0.3.7...v0.3.8) (2026-09-20)


### Documentation

* complete frozen compiler release acceptance ([#34](https://github.com/RQM-Technologies-dev/rqm-compiler/issues/34)) ([8e7f540](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/8e7f54012617cabbcf6b78f30934398e6808589d))
* record verified 0.3.7 publication handoff ([#32](https://github.com/RQM-Technologies-dev/rqm-compiler/issues/32)) ([830d495](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/830d4957194fac7d5ab92a152b6de6de409287f6))

## [0.3.7](https://github.com/RQM-Technologies-dev/rqm-compiler/compare/v0.3.0...v0.3.7) (2026-09-20)


### Features

* add AxisHinge Cartan observable closure ([a0034ef](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/a0034ef495aaeb1b81f72dfffb101eb6117536c4))
* add backend capability model for 0.3.4 ([49e6c57](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/49e6c575303c7dcb31ec3965616172f8e4fa526d))
* add backend capability telemetry to CompilerReport ([2060c77](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/2060c777ab324f1403d27f7381c31dd58afa55db))
* add capability-driven materialization planning ([b95b410](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/b95b4100f6b88ba5709b79553473849809bfd6ed))
* add direct star relational readout invariant ([4d83a0d](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/4d83a0dbbe35d63e6d2cbfdc64be2adc65c24d3a))
* add exact Pauli observable evaluator without statevector ([0322364](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/0322364b1a7a02cc303159fb4b749ced6ea027d5))
* add representation and query telemetry to CompilerReport ([893bed6](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/893bed62d7aff291d86a65bb8585aab5b1be74b3))
* add representation-owned closure accounting ([3c7fbbb](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/3c7fbbbf8c8ae14ecdf2dc39606114ec84a7a427))
* add structured observable evaluator ([df21c26](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/df21c2614cc18de7cf33af62c10840f65ee13aec))
* add validated topology-aware hardware readout ([168a1ac](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/168a1ace584033f1c1f8ba703c55b4c09832195f))
* attach query planner telemetry to CompilerReport ([1c87047](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/1c8704736c2f0bdc2b96713995ef946da865ca82))
* codify stable exact RQM prototype ([ceef7d3](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/ceef7d37515b9ddde6f56b2aeffd47f77e4fd27e))
* emit representation promotion and demotion event stream ([72c7b12](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/72c7b124f41e8985cb3393002450e50fff9278dd))
* export backend capability model ([97e9da3](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/97e9da3b912c80b115b015a3774c9e6dc25c1f99))
* export backend materialization planning API ([93c841f](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/93c841f40c69deac0eb86f43f14a2ce044fa747a))
* export planner through rqm_compiler public namespace ([269034d](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/269034d85e02b9657d49a2cb0da96400e931f786))
* export report-aware query planner ([0d6338b](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/0d6338b3ef7f0363a8136d1901289c3bf44392cd))
* fuse canonical relational two-qubit rotations ([37dc5f5](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/37dc5f5285e8534d55504d84e1c1b1f80a78d14b))
* graduate exact chain boundary readout to stable prototype ([1a580a3](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/1a580a3a3fc23f6c971dab427c6669cd760e76fe))
* graduate validated hardware topology readout ([6d3a5fc](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/6d3a5fc06085a5dddb718857dab6f1b52f389f1f))
* populate C_R and promotion telemetry ([ab01a76](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/ab01a760e10da0549d7a32b23a0a6cc9069d6595))
* promote representation-aware planner to public API ([1fce717](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/1fce717ec00b5030abf7dd0b382988645553d727))
* report capability-driven backend materialization ([f4a8bd4](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/f4a8bd494af778604952beac29b8664941c9000b))


### Bug Fixes

* apply verified two-qubit tensor index permutation ([7a74311](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/7a74311924891b480bbb3f470c33354a91efb55b))
* integrate upstream compiler while preserving safe fallback [skip ci] [skip render] ([ea9ab18](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/ea9ab1854776528fcbbccae3d474c01e799cbb3f))
* keep backend SDKs out of compiler package metadata ([acd6986](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/acd6986517f9a17fd84c75bfffcd1ae61d46a196))
* preserve compatibility before relational package release ([a641cfa](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/a641cfa765e77df10f6eda36fccf2c23f5c484c3))
* preserve pre-0.3.4 lowering behavior by backend family ([7cd603e](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/7cd603e1dc56db8adc3c260aa34a04850ebd637c))
* qualify frozen compiler 0.3.7 release ([#31](https://github.com/RQM-Technologies-dev/rqm-compiler/issues/31)) ([cb29214](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/cb29214e0ee83dfefa03639ba6ca368ec1a297e1))
* route validated chains through boundary transfer ([845a828](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/845a828be6895e59a20cd0eed5b81a27ee04083c))


### Documentation

* add 0.3.5 cross-stack qualification ledger ([c96acbe](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/c96acbe810a962aa712c9c5b4b023157eb70f917))
* add 0.4 ecosystem compatibility matrix ([6604ccf](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/6604ccf437378093272d107d7c0de70a55fec43a))
* add 0.4 public release contract ([dd6bad9](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/dd6bad92266d6452abad6642f4148ace7607e6b7))
* add 0.4 public release contract ([b1b6b1b](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/b1b6b1bb5dda6b3fb4605ddec95535b04f172317))
* add 0.4 public release contract ([a70b710](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/a70b7105663792af02e985e858fada8ad6489312))
* add 0.4 public release contract ([c120d99](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/c120d99d8b734f69c20ba5ca3358c38004fb6e64))
* add runnable representation-aware 0.4 example ([2d00572](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/2d00572cd16156743eba8469358ce8a06ad1e39c))
* advance entanglement Braket and PennyLane compatibility ([55faa4e](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/55faa4e654f2a935255e174fe5722cd9396ac6f2))
* attach frozen benchmark to 0.4 upgrade line ([91a696c](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/91a696c65672f45dba87982ba1ffa1ea948ea784))
* define 0.3.4 backend modality boundary ([e2a728b](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/e2a728bae0483c76916d49b8e6043445384c7b1f))
* define finish-line complexity experiment ([939f6e4](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/939f6e47b4b0e2d4c4e2c180958a08a8587135e9))
* define H1-H3 complexity benchmark protocol ([5a4d157](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/5a4d15769d61f4b1ddfae836b73f7656718ee19f))
* define RQM Compiler v2 upgrade plan ([3894ac7](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/3894ac78a71b81fba905bc417421dbe132fc3708))
* define stable exact prototype boundary ([11865db](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/11865dbe722e6b471259308b3da28cf514ea9f62))
* derive quaternionic spectral Cartan contraction law ([a51c32b](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/a51c32bb55cd617dabe427f403005d689e1b5e8e))
* document relational entanglement compiler model ([d96f6a3](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/d96f6a30e03d271cefb65dea41038465c196b00b))
* expose representation-aware public API ([97e40b7](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/97e40b7818d61e6fc865379ebd9f2b645a2f8674))
* freeze 0.3.6 terminology and exit gate ([b871067](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/b871067b3b2d4bdb853eff96f74c6adc14ddadb2))
* freeze 0.4 benchmark baseline contract ([5df173c](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/5df173ccba59f32decb96937545a0e970570821a))
* freeze ordered 0.3.7 RQM Studio execution program ([936637d](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/936637d4e79540575a7eadee0ee49a7925b0143f))
* make 0.3.7 first RQM Studio QPU orchestration proof ([580df0c](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/580df0c6d75baa721090a238ba02b2dcbddab1ce))
* make representation-aware planner the 0.4 public story ([421a9ef](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/421a9ef8265bbd821665d548904e23044bd4dac2))
* record Braket qualification and current API gate ([c2e3d19](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/c2e3d19ce5dff05bc9440e67cf86beab634663a6))
* reflect relational entanglement methodology ([d27958b](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/d27958b9fc9dc6b395b507d29fd1bb6bbe2e58f8))
* refresh 0.4 ecosystem launch status ([acb962d](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/acb962d0f29da39081847a8b56816d102057991b))
* require two real hardware stacks for 0.3.7 ([8290870](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/829087023134413ec916e3c8e5f60ab9f79c006c))
* track qiskit and core 0.4 compatibility work ([2b3e124](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/2b3e1245c613d23b5def4270f2f17bb44bb30e9a))
* update final 0.3.5 qualification status ([9dbb73e](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/9dbb73e8fad1f486ba716226bd151eff40cf6a83))

## 0.3.7 — release candidate

- Freeze the representation-aware prototype at the integrated September 20 runtime.
- Include quaternion-native observable updates, analytic hinge/CX transfers,
  bounded frontier evaluation, query reuse, and verified regional compilation.
- Preserve input validation and the global-Z unsafe-star-placement fallback.
- Require rqm-entanglement 0.2.2 for the analytic Pauli transfer module and
  rqm-core 0.2.2; retain a default frontier cap of four.
- Qualify exact installed packages before publication; hardware integration
  and wider-frontier research remain separate from this software release.

## [0.3.0](https://github.com/RQM-Technologies-dev/rqm-compiler/compare/v0.2.2...v0.3.0) (2026-08-06)


### Features

* add verified regional optimization reports ([#22](https://github.com/RQM-Technologies-dev/rqm-compiler/issues/22)) ([f0eb1f5](https://github.com/RQM-Technologies-dev/rqm-compiler/commit/f0eb1f570db4744215eb391b2f5fcaed2ea8faf5))

### Verified regional optimization details

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
