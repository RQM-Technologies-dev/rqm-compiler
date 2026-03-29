# rqm-compiler

Backend-neutral optimization and rewriting engine for the RQM ecosystem.

rqm-compiler owns the internal compiler circuit model and the optimization
pipeline.  The canonical external/public circuit schema is defined by
**rqm-circuits**; rqm-compiler is the next layer after that boundary.

---

## Installation

```bash
pip install rqm-compiler
```

Or in development mode from the repository root:

```bash
pip install -e ".[dev]"
```

---

## Quickstart

> **Note for external integrations:** Callers coming from the RQM API, Studio,
> or any external integration will typically enter the ecosystem through
> **rqm-circuits**, which owns the canonical public circuit schema.
> rqm-compiler is the next layer: it receives a parsed/validated circuit
> object and runs the optimization pipeline before handing off to a backend
> adapter.

```python
from rqm_compiler import Circuit, optimize_circuit

c = Circuit(2)
c.h(0)
c.cx(0, 1)
c.measure_all()

# Recommended: optimize and export
optimized, report = optimize_circuit(c)
print(report)
descriptors = optimized.to_descriptors()
```

---

## Public API Hierarchy

rqm-compiler exposes a tiered API. Most users should use Tier 1.
Lower tiers exist for transformations and advanced workflows.

| Tier | Entrypoint | When to use | Stability |
|------|-----------|-------------|-----------|
| 1 — Build | `Circuit`, `Operation` | Construct programs in the compiler's internal model | Stable |
| 2 — Transform | `compile_circuit(...)`, `optimize_circuit(...)` | Run optimization passes, export internal descriptor IR | Experimental |
| 3 — Internal | low-level IR utilities | Advanced use | Subject to change |

---

## Architecture

```
rqm-core
    ↓
rqm-circuits   ← canonical external/public circuit IR
    ↓
rqm-compiler   ← this repo (internal optimization engine)
    ↓
rqm-qiskit / rqm-braket   ← backend lowering and execution bridges
    ↓ (optional)
rqm-optimize
```

| Layer | Responsibility |
|-------|---------------|
| `rqm-core` | Quaternion algebra, SU(2), Bloch sphere, spinor math |
| `rqm-circuits` | Canonical external/public circuit schema and IR boundary |
| `rqm-compiler` | Internal optimization and rewriting engine |
| `rqm-qiskit` / `rqm-braket` | Backend lowering and execution bridges |
| `rqm-optimize` | Optional backend-adjacent optimization and compression |

`rqm-compiler` does **not** implement quantum math and does **not** import any vendor SDK.

---

## What rqm-compiler owns

- `Circuit` — the internal compiler circuit model used by optimization passes
- `Operation` — the internal instruction model used by compiler transforms
- Gate semantics and supported gate set (compiler-internal)
- Circuit structure and composition rules
- Pass pipelines: normalization, canonicalization, gate fusion, cancellation
- Serialization helpers (`circuit_to_dict`, `circuit_from_dict`)
- Internal backend-neutral descriptor export for translation and debugging
- Compiler reports and optimization metadata (`CompilerReport`)

---

## What rqm-compiler does NOT own

- The canonical public/external circuit schema — belongs in `rqm-circuits`
- API wire format or Studio payload format — belongs in `rqm-circuits`
- Quaternion algebra — belongs in `rqm-core`
- Spinor math — belongs in `rqm-core`
- SU(2) or Bloch sphere math — belongs in `rqm-core`
- Qiskit objects or imports — belongs in `rqm-qiskit`
- Amazon Braket objects or imports — belongs in `rqm-braket`
- Any execution or simulation logic

---

## Internal compiler descriptor format

Every gate operation inside the compiler is represented as a plain dictionary.
This is the **internal compiler descriptor format** — useful for debugging,
backend translation, and pass inspection.  It is not the canonical external
public circuit schema (that lives in rqm-circuits).

```python
{
    "gate": "rx",       # lowercase gate name
    "targets": [0],     # list of target qubit indices (always present)
    "controls": [],     # list of control qubit indices (always present)
    "params": {"angle": 1.5707963267948966}  # parameter dict (always present)
}
```

---

## Circuit builder API (Tier 1)

```python
from rqm_compiler import Circuit

c = Circuit(3)

# Single-qubit gates
c.i(0); c.x(0); c.y(1); c.z(2); c.h(0); c.s(1); c.t(2)

# Parameterised single-qubit gates
c.rx(0, 1.57).ry(1, 0.78).rz(2, 3.14).phaseshift(0, 0.5)

# Two-qubit gates
c.cx(0, 1).cy(1, 2).cz(0, 2)
c.swap(0, 1).iswap(1, 2)

# Measurement
c.measure(0, key="m0")
c.measure_all()   # measures all qubits with default keys

# Barrier
c.barrier()

# Export to internal compiler descriptor list
descriptors = c.to_descriptors()

# Reconstruct from a descriptor list (inverse of to_descriptors)
restored = Circuit.from_descriptors(descriptors, num_qubits=3)
```

---

## Transformation API (Tier 2 — Experimental)

`optimize_circuit` is the **recommended** Tier 2 entry point.  It runs the full
optimization pipeline (validate → normalize → canonicalize → flatten → gate
merging → cancellation) and returns an optimized circuit plus a
:class:`CompilerReport`.  Use this as your default mental model for backend
integration.

`compile_circuit` is the lightweight alternative when you only need validation
and normalization without optimization.

Both functions are optional — basic circuit construction works without them.

```python
from rqm_compiler import optimize_circuit, compile_circuit

# Preferred: optimize first, then export to backend
optimized, report = optimize_circuit(c)
print(report)
for op in optimized.to_descriptors():
    translate_to_backend(op)

# Lightweight alternative: validate + normalize + export (no optimization)
compiled = compile_circuit(c)
compiled.descriptors   # list of internal compiler descriptor dicts
compiled.num_qubits    # int
compiled.metadata      # dict with compilation metadata
```

### Semantic verification in `optimize_circuit`

`optimize_circuit` is **proof-gated and fail-closed**. It always follows:

1. build a candidate optimized circuit
2. run mandatory semantic verification
3. commit only if verification is `VERIFIED`
4. otherwise withhold optimization and return the original circuit unchanged

This means no successful optimization output is ever unverified.

`CompilerReport` records:

- `equivalence_status`: always `VERIFIED` for the returned circuit
- `equivalence_verified`: always `True` for the returned circuit
- `equivalence_guaranteed`: explicit proof-gated guarantee for the returned circuit
- `optimization_applied`: `True` only when a verified candidate was committed
- `fallback_reason`: `"verification_not_established"` when optimization is withheld
- `equivalence_report`: structured payload for the committed output, plus
  `internal_candidate_proof_result` for development diagnostics

Current verifier methods used internally:

- `U1Q_CANONICAL`: exact single-qubit canonical-u1q comparison
- `UNITARY_NUMERICAL`: dense unitary comparison up to global phase for supported small circuits
- `GATEWISE_IDENTITY`: exact descriptor identity check for fully-resolved circuits

Important semantics:

- Only verified candidates are committed as optimized output.
- If proof fails, is unsupported, or errors, optimization is not committed.
- Unsupported proof coverage causes optimization refusal/fallback, not uncertain output.

Backend repos should prefer `optimize_circuit` because it runs gate merging and
cancellation before translation — circuits with redundant or adjacent single-qubit
gates will be cheaper to execute after optimization.  Verify the trade-off for
your specific circuit patterns.

---

## Reconstructing a circuit from descriptors

`Circuit.from_descriptors(descriptors, num_qubits)` is the inverse of
`to_descriptors()`.  It reconstructs a compiler `Circuit` from the internal
descriptor format — useful for debugging, reproducibility, backend roundtrips,
and tests.  This is not the canonical external public IR boundary (which is
owned by rqm-circuits).

```python
from rqm_compiler import Circuit, optimize_circuit

c = Circuit(2)
c.h(0).cx(0, 1).measure_all()

# Optimize and capture the internal compiler descriptor IR
optimized, report = optimize_circuit(c)
descriptors = optimized.to_descriptors()

# Later: reconstruct a Circuit from those descriptors
restored = Circuit.from_descriptors(descriptors, num_qubits=optimized.num_qubits)
assert restored.to_descriptors() == descriptors
```

---

## IO helpers

```python
from rqm_compiler.io import circuit_to_dict, circuit_from_dict

data = circuit_to_dict(c)          # serialize to JSON-compatible dict
restored = circuit_from_dict(data)  # reconstruct Circuit from dict
```

---

## Supported gates (v0)

| Category | Gates |
|---|---|
| Single-qubit | `i x y z h s t` |
| Parameterised single-qubit | `rx ry rz phaseshift` (param: `angle`) |
| Two-qubit | `cx cy cz swap iswap` |
| Other | `measure barrier` |

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

---

## Architecture rules

See [AGENTS.md](AGENTS.md) for the full list of contributor boundary rules.
