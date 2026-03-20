# rqm-compiler

Canonical circuit IR and compilation layer for the RQM ecosystem.

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
| 1 — Build | `Circuit`, `Operation` | Construct programs | Stable |
| 2 — Transform | `compile_circuit(...)`, `optimize_circuit(...)` | Normalize and export canonical descriptor IR | Experimental |
| 3 — Internal | low-level IR utilities | Advanced use | Subject to change |

---

## Architecture

```
rqm-core
    ↓
rqm-compiler   ← this repo
    ↓
rqm-qiskit
```

`rqm-core` owns all quantum math (quaternions, SU(2), Bloch sphere, spinors).
`rqm-compiler` owns the canonical circuit IR and compilation logic.
`rqm-qiskit` (and other backend repos) translate the compiler IR into vendor objects.

`rqm-compiler` does **not** implement quantum math and does **not** import any vendor SDK.

---

## What rqm-compiler owns

- `Circuit` — the only canonical quantum program container
- `Operation` — the only canonical instruction type
- Gate semantics and supported gate set
- Circuit structure and composition rules
- Validation, normalization, and compilation passes
- Serialization helpers (`circuit_to_dict`, `circuit_from_dict`)
- Backend-neutral descriptor IR export

---

## What rqm-compiler does NOT own

- Quaternion algebra — belongs in `rqm-core`
- Spinor math — belongs in `rqm-core`
- SU(2) or Bloch sphere math — belongs in `rqm-core`
- Qiskit objects or imports — belongs in `rqm-qiskit`
- Amazon Braket objects or imports — belongs in `rqm-braket`
- Any execution or simulation logic

---

## Canonical descriptor schema

Every gate operation is a plain dictionary — the source of truth for the whole ecosystem:

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

# Export to canonical descriptor list
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
compiled.descriptors   # list of canonical descriptor dicts
compiled.num_qubits    # int
compiled.metadata      # dict with compilation metadata
```

Backend repos should prefer `optimize_circuit` because it runs gate merging and
cancellation before translation — circuits with redundant or adjacent single-qubit
gates will be cheaper to execute after optimization.  Verify the trade-off for
your specific circuit patterns.

---

## Reconstructing a circuit from descriptors

`Circuit.from_descriptors(descriptors, num_qubits)` is the inverse of
`to_descriptors()`.  It is useful for API ingestion, backend-to-compiler
roundtrips, debugging, and reproducibility.

```python
from rqm_compiler import Circuit, optimize_circuit

c = Circuit(2)
c.h(0).cx(0, 1).measure_all()

# Optimize and capture the canonical IR
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
