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
from rqm_compiler import Circuit

c = Circuit(1)
c.ry(0, 1.0)
c.measure_all()

descriptors = c.to_descriptors()
# [
#   {'gate': 'ry',      'targets': [0], 'controls': [], 'params': {'angle': 1.0}},
#   {'gate': 'measure', 'targets': [0], 'controls': [], 'params': {'key': 'm0'}},
# ]
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

# Export
descriptors = c.to_descriptors()
```

---

## Transformation API (Tier 2 — Experimental)

`compile_circuit` and `optimize_circuit` are the Tier 2 entry points.
They are optional — basic circuit construction works without them.

```python
from rqm_compiler import compile_circuit, optimize_circuit

# compile_circuit: validate + normalize + canonicalize + export
compiled = compile_circuit(c)
compiled.descriptors   # list of canonical descriptor dicts
compiled.num_qubits    # int
compiled.metadata      # dict with compilation metadata

# optimize_circuit: full pipeline including gate merging and cancellation
optimized, report = optimize_circuit(c)
print(report)
```

Backend repos use the compiler output like this:

```python
compiled = compile_circuit(circuit)
for op in compiled.descriptors:
    translate_to_backend(op)
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
