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
| `rqm-qiskit` | Qiskit lowering/execution bridge | **blocking** | allow `rqm-compiler>=0.3,<0.5`; validate current 0.4 planner candidate and wheel matrix | mandatory |
| `rqm-braket` | Braket lowering/execution bridge | validate | run compiler 0.4 descriptor/lowering compatibility suite | mandatory |
| `rqm-pennylane` | PennyLane descriptor bridge | validate | run compiler 0.4 descriptor/export compatibility suite | mandatory |
| `rqm-circuits` | canonical public circuit schema | compatible-by-design | verify 0.4 changes remain internal and require no wire-schema break | mandatory |
| `rqm-core` | canonical local quaternion/SU(2)/shared operator math | update-required | centralize shared operator/Pauli-basis primitives used by 0.4; retain compiler/topology policy outside core | mandatory |
| `rqm-entanglement` | nonlocal/Cartan math | validate | verify no duplicated two-qubit math moved into compiler/core | mandatory |
| `quantum-compiler-api` | production compiler API / Studio backend | update-required | move off old compiler commit/version assumptions; expose 0.4 planner/report fields | mandatory |
| `openqse-rqm-adapter` | OpenQSE interoperability | update-required | consume public planner/report API; refresh conformance provenance | mandatory |
| `rqm-studio` | product UI | update-required | surface new report fields where useful after API integration | product launch |
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
       quantum-compiler-api
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
