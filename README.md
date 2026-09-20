# rqm-compiler

**RQM Compiler 0.3.7 is a representation-aware quantum computation planner.** It analyzes the circuit, requested observable, interaction structure, and target capabilities, then uses the least-general validated exact representation and readout/lowering strategy available. When specialized structure is not proven, it falls back conservatively to general exact machinery.

It remains backend-neutral: RQM plans the computation; backend bridges materialize and execute it.

rqm-compiler owns the internal compiler circuit model and optimization policy. The canonical external/public circuit schema is defined by **rqm-circuits**; two-qubit relational mathematics is owned by **rqm-entanglement**.

## Representation model

`u1q` is a compact, backend-neutral, standard-compatible single-qubit compiler IR. It preserves tested quaternion/`SU(2)` semantics; it is not a quantum-mechanically richer state representation.

For two-qubit work, the compiler now uses an exact relational promotion hierarchy:

```text
Bell
  ⊂ AxisHinge
  ⊂ CartanRelation
  ⊂ QuaternionCartanBlock
  ⊂ U(4)
```

The subset notation means increasing representational generality, not different physical kinds of entanglement. See [Relational Entanglement](docs/RELATIONAL_ENTANGLEMENT.md) for the compiler methodology.

## Installation

```bash
pip install rqm-compiler
```

Development:

```bash
pip install -e ".[dev]"
pytest
```

## Representation-aware public API

The 0.3.7 prototype planner is available through the normal `rqm_compiler`
namespace; callers no longer need to import `stable_prototype` directly.

```python
from rqm_compiler import Circuit, compile_representation_aware, plan_and_evaluate

c = Circuit(4)
c.h(0)
for i in range(3):
    c.rxx(i, i + 1, 0.11)
    c.rzz(i, i + 1, -0.067)
    c.cx(i, i + 1)

compiled = compile_representation_aware(c)
result = plan_and_evaluate(compiled, "ZZZZ")

print(compiled.report.representation_complexity)  # C_R
print(compiled.report.query_complexity)           # C_Q
print(compiled.report.recognized_topology)
print(compiled.report.selected_query_route)
print(result.value)
```

`plan_and_evaluate` uses strict validated recognizers for specialized exact
routes (currently star relational, chain boundary transfer, and the validated
fixed-depth 1D hardware-efficient topology path) and otherwise falls back to
the general exact evaluator.

The legacy `optimize_circuit` API remains supported during the 0.3.x migration.

## Compiler model

The preferred flow is:

```text
recognize → compress → propagate relationally → promote if closure breaks → backend materialize
```

The compiler attempts to retain the smallest exact representation of a two-qubit interaction. A Bell-sector special case need not become a general block; a one-axis interaction can remain an `AxisHinge`; multiple commuting nonlocal axes can remain a `CartanRelation`; and only a general two-qubit window needs the local-quaternion plus nonlocal-Cartan structure of a `QuaternionCartanBlock`. Dense `U(4)` remains the mathematical envelope and verification/interoperability fallback.

This representation policy does not relax semantic verification. Optimization remains proof-gated and fail-closed.

## Quickstart

External integrations normally enter through `rqm-circuits`, then pass a parsed circuit to this compiler.

```python
from rqm_compiler import Circuit, optimize_circuit, lower_circuit_for_backend

c = Circuit(2)
c.rxx(0, 1, 0.25)
c.ryy(0, 1, 0.50)

optimized, report = optimize_circuit(c)
print(report.to_dict())

lowered = lower_circuit_for_backend(
    optimized,
    backend_family="braket_gate_model",
)
```

`RXX`, `RYY`, and `RZZ` are the portable materialization primitives for X-, Y-, and Z-axis hinges. Relational metadata may be carried internally without changing the public `rqm-circuits` wire contract.

## Architecture

```text
rqm-core                 local quaternion / SU(2) mathematics
    ↓
rqm-entanglement         two-qubit relational geometry and Cartan mathematics
    ↓
rqm-circuits             canonical public circuit schema; RXX/RYY/RZZ materialization
    ↓
rqm-compiler             recognition, relational propagation, promotion, proof gating
    ↓
rqm-qiskit / rqm-braket / rqm-pennylane
                         backend lowering and execution
```

| Layer | Responsibility |
|---|---|
| `rqm-core` | Quaternion algebra, SU(2), Bloch sphere, spinor math |
| `rqm-entanglement` | Bell/axis/Cartan relational coordinates, arbitrary two-qubit quaternion–Cartan decomposition, reconstruction, classification and fingerprints |
| `rqm-circuits` | Canonical external/public circuit schema, including RXX/RYY/RZZ |
| `rqm-compiler` | Backend-neutral optimization, relational representation policy, proof-gated promotion/demotion, internal `su4q` materialization |
| backend bridges | Native gate materialization, synthesis, execution |

`rqm-compiler` does **not** own decomposition math and does not import vendor SDKs. Local quaternion/SU(2) mathematics is delegated to `rqm-core`; relational two-qubit decomposition and reconstruction are delegated to `rqm-entanglement`.

## Relational hierarchy

### Bell

The smallest special case. Bell-sector coordinates can preserve parity and relative-phase structure without promoting the interaction to a more general representation.

### AxisHinge

An exact single-axis nonlocal relation, represented by an axis plus angle. X/Y/Z hinges naturally materialize as `rxx`, `ryy`, and `rzz`.

### CartanRelation

The nonlocal Cartan coordinates required when a relation spans multiple commuting two-qubit axes. This preserves nonlocal structure without carrying unnecessary local factors or a dense matrix.

### QuaternionCartanBlock

A structured general two-qubit unitary representation: local quaternion/SU(2) factors around a nonlocal Cartan relation. The internal `su4q` compiler descriptor is a materialization of this structure.

### U(4)

The fully general two-qubit unitary space. Dense matrices remain useful for verification, reconstruction and interoperability, but are not the preferred working IR when a smaller exact relational representation is sufficient.

## What rqm-compiler owns

- `Circuit` and `Operation`, the internal compiler model.
- Validation, normalization, canonicalization and optimization pipelines.
- Single-qubit `u1q` fusion/canonicalization.
- Recognition and propagation policy for relational two-qubit structure.
- Exact promotion/demotion decisions between supported relational levels.
- Two-qubit cancellation and compatible relational compression.
- Proof-gated commit/fallback behavior and `CompilerReport` metadata.
- Backend-neutral descriptor export.
- Opt-in/internal `su4q` (`QuaternionCartanBlock`) materialization.

## What rqm-compiler does not own

- Public/external circuit schema (`rqm-circuits`).
- Quaternion/SU(2) mathematics (`rqm-core`).
- Bell/Cartan decomposition, reconstruction or two-qubit relational mathematics (`rqm-entanglement`).
- Qiskit, Braket, PennyLane or other vendor/backend objects.
- Execution or simulation.

## Internal descriptors

The compiler uses dictionaries such as:

```python
{
    "gate": "rxx",
    "targets": [0, 1],
    "controls": [],
    "params": {"angle": 0.25},
}
```

These are compiler descriptors, not the canonical external wire schema.

## Two-qubit structured analysis

`su4q` means an internal universal two-qubit quaternion–Cartan compiler block. It is not part of the public `rqm-circuits` wire format and is not a claim of quaternionic composite mechanics.

```python
from rqm_compiler import analyze_two_qubit_blocks, extract_su4q_blocks

report = analyze_two_qubit_blocks(circuit)

candidate_view, report = extract_su4q_blocks(
    circuit,
    mode="emit_candidate",
)

lowering_input, report = extract_su4q_blocks(
    circuit,
    mode="replace_if_backend_requests",
    backend_requests_su4q=True,
)
```

The new relational methodology generalizes the compiler's mental model around this machinery: do not promote a Bell, axis-hinge, or Cartan-relation window into a full quaternion-Cartan block unless exact composition requires it.

## Semantic verification

`optimize_circuit` remains proof-gated and fail-closed:

1. build a candidate optimized circuit;
2. run mandatory semantic verification;
3. commit only if verification is `VERIFIED`;
4. otherwise return the original circuit unchanged.

`CompilerReport` records equivalence status, whether optimization was applied, fallback reason, comparison evidence, and relational/adaptive routing metadata where available.

Current verification includes canonical single-qubit checks, dense numerical unitary comparison for supported small circuits, and exact descriptor identity where applicable.

## Supported gates

| Category | Gates |
|---|---|
| Single-qubit | `i x y z h s t` |
| Parameterized single-qubit | `rx ry rz phaseshift` |
| Two-qubit | `cx cy cz swap iswap rxx ryy rzz` |
| Internal structured two-qubit | `su4q` / `QuaternionCartanBlock` |
| Other | `measure barrier` |

## Documentation

- [Relational entanglement methodology](docs/RELATIONAL_ENTANGLEMENT.md)
- [EXP-012 SU4Q boundary](docs/EXP012_SU4Q_BOUNDARY.md)
- [RQM Technical Canon v2](RQM_TECHNICAL_CANON_V2.md)
- [Contributor architecture rules](AGENTS.md)
- [Migrating from 0.3 to 0.4](docs/MIGRATING_0_3_TO_0_4.md)
- [Representation-aware API](docs/REPRESENTATION_AWARE_API.md)
- [CompilerReport 0.4 fields](docs/COMPILER_REPORT_0_4.md)
- [Claims and limitations](docs/CLAIMS_AND_LIMITATIONS.md)
- [Frozen benchmark contract](benchmarks/BASELINE.md)
- [Backend capability model](docs/BACKEND_CAPABILITY_MODEL.md)

Performance advantages are workload- and backend-dependent and require measurement. The relational hierarchy defines exact representation and compiler architecture; it does not itself establish a universal speed, fidelity, or compression advantage.
