# RQM Compiler 0.4.0 Ecosystem Compatibility Matrix

This matrix tracks every repository that must accept or be validated against
`rqm-compiler 0.4.0` before the 0.4.0 compiler launch.

Status values:

- **blocking** — current package metadata or pinned tooling rejects 0.4.0;
- **update-required** — runtime/product integration must adopt or validate the new public API;
- **validate** — interface is expected to remain compatible, but CI must prove it;
- **docs/evidence** — no runtime blocker; documentation/provenance must be refreshed;
- **compatible-by-design** — no compiler-version dependency; stable external contract should remain unchanged.

| Repository | Role | Current 0.4 status | Required action | Launch gate |
| --- | --- | --- | --- | --- |
| `rqm-compiler` | representation-aware compiler/planner | in progress | complete 0.3.x milestones, release 0.4.0 | mandatory |
| `rqm-qiskit` | Qiskit lowering/execution bridge | **in validation** | dependency range now accepts `rqm-compiler>=0.3,<0.5`; CI is qualifying against current 0.4 candidate | mandatory |
| `rqm-braket` | Braket lowering/execution bridge | **compatible** | RXX/RYY/RZZ descriptor validation/lowering added; Python 3.10/3.11/3.12 CI and distribution build pass | mandatory |
| `rqm-pennylane` | PennyLane descriptor bridge | **compatible** | compiler 0.4 qualified on Python 3.11/3.12; bridge retains independent Python 3.10 support | mandatory |
| `rqm-circuits` | canonical public circuit schema | compatible-by-design | verify 0.4 changes remain internal and require no wire-schema break | mandatory |
| `rqm-core` | canonical local quaternion/SU(2)/shared operator math | **in validation** | candidate now centralizes Pauli-basis projection/reconstruction, basis projectors, and two-qubit partial traces; compiler migration waits on a released core version | mandatory |
| `rqm-entanglement` | nonlocal/Cartan math | **compatible** | ownership boundary frozen; compiler delegates canonical pair rotations; CI passed | mandatory |
| `rqm-api` | production compiler API / Studio backend | **in validation** | service adopts public 0.4 planner/report API; CI now overlays the current 0.4 candidate and asserts planner symbols before full tests | mandatory |
| `openqse-rqm-adapter` | OpenQSE interoperability | **compatible** | clean ecosystem evidence exercises public 0.4 compile and query planner APIs | mandatory |
| `rqm-studio` | product UI | **compatible candidate** | report types/UI and explanation canon understand 0.4 planner telemetry; CI and hosted explanation validation pass | product launch |
| `rqm-optimize` | downstream Qiskit-native optimizer | validate | confirm downstream role and no duplicated 0.4 planner responsibility | product launch |
| `RQM-Jobs-MCP` | service/catalog surface | docs/evidence | update compiler capability provenance after 0.4 freeze | product launch |
| `RQM-Storefront` | public product docs | docs/evidence | update compiler positioning and benchmark evidence | product launch |
| `rqm-business-strategy` | business/product roadmap | docs/evidence | update release state and product claims | product launch |
| `rqm-experiments` | evidence corpus | docs/evidence | pin 0.4 release provenance for future experiments | post-release evidence |
| `RQM-patents` | invention evidence | docs/evidence | append 0.4 implementation/provenance without changing claim scope automatically | post-release evidence |

## 0.4 cross-stack acceptance order

```text
rqm-core / rqm-entanglement / rqm-circuits
                |
                v
          rqm-compiler 0.4
                |
      +---------+---------+
      v         v         v
 rqm-qiskit  rqm-braket  rqm-pennylane
      |                     |
      +----------+----------+
                 v
       rqm-api
                 |
          +------+------+
          v             v
      rqm-studio   openqse-rqm-adapter
```

## Compatibility policy

The 0.4 compiler must not force a new `rqm-circuits` wire format merely to
expose internal representation/query planning. Backend bridges consume
materialized standard-compatible circuit descriptors; planner telemetry travels
through `CompilerReport` rather than vendor-specific IR.

The first blocking downstream package is `rqm-qiskit`, whose pre-0.4
dependency range was `rqm-compiler>=0.3,<0.4`.

## Current candidate provenance

- rqm-compiler compatibility matrix: `6604ccf437378093272d107d7c0de70a55fec43a`
- rqm-qiskit 0.4 compatibility range/test work: `03e0459ed0450855e56a5cf889bb0170e9c34545`
- rqm-core shared operator math candidate: `b3dc98f81480c769fa0359f76f67ad32a0a4d36e`

The new core primitives intentionally stop at backend-independent operator mathematics. Query planning, topology recognition, contraction ordering, and boundary-transfer policy remain compiler responsibilities; canonical nonlocal/Cartan mathematics remains in `rqm-entanglement`.
