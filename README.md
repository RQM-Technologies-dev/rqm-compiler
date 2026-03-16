# rqm-compiler

`rqm-compiler` is the backend-neutral compilation layer for the RQM ecosystem.
It converts RQM circuit objects into canonical gate descriptors that can be translated
by execution backends such as Qiskit and Amazon Braket.

---

## Ecosystem position

```
RQM physics / math
        ↓
    rqm-core
        ↓
   rqm-compiler          ← this repo
        ↓
rqm-qiskit   rqm-braket
```

`rqm-compiler` sits between the physics math layer (`rqm-core`) and the vendor execution
layers.  It does **not** implement quantum math and does **not** import vendor SDKs.

---

## Quick start

```python
from rqm_compiler import Circuit, compile_circuit

c = Circuit(2)
c.h(0)
c.cx(0, 1)
c.measure(0, key="m0")
c.measure(1, key="m1")

compiled = compile_circuit(c)
print(compiled.descriptors)
# [
#   {'gate': 'h',       'targets': [0], 'controls': [],  'params': {}},
#   {'gate': 'cx',      'targets': [1], 'controls': [0], 'params': {}},
#   {'gate': 'measure', 'targets': [0], 'controls': [],  'params': {'key': 'm0'}},
#   {'gate': 'measure', 'targets': [1], 'controls': [],  'params': {'key': 'm1'}},
# ]
```

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

## Core concepts

### Canonical descriptor

Every gate operation is represented as a plain dictionary:

```python
{
    "gate": "rx",       # lowercase gate name
    "targets": [0],     # list of target qubit indices (always present)
    "controls": [],     # list of control qubit indices (always present)
    "params": {"angle": 1.5707963267948966}  # parameter dict (always present)
}
```

This is the **source of truth** for the entire ecosystem.  Backend repos translate these
descriptors into their respective SDK objects.

### Circuit

`Circuit(num_qubits)` is the canonical circuit container.  It provides a fluent builder API:

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

# Barrier
c.barrier()

# Export
descriptors = c.to_descriptors()
```

### compile_circuit

`compile_circuit(circuit)` is the main entry point:

```python
from rqm_compiler import compile_circuit

compiled = compile_circuit(c)

compiled.descriptors   # list of canonical descriptor dicts
compiled.num_qubits    # int
compiled.metadata      # dict with compilation metadata
```

The pipeline: **validate → normalize → canonicalize → flatten → export**.

### IO helpers

```python
from rqm_compiler.io import circuit_to_dict, circuit_from_dict

data = circuit_to_dict(c)         # serialize to JSON-compatible dict
restored = circuit_from_dict(data) # reconstruct Circuit from dict
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

## Backend integration

Backend repos use `rqm-compiler` like this:

```python
from rqm_compiler import compile_circuit

compiled = compile_circuit(circuit)

for op in compiled.descriptors:
    translate_to_backend(op)
```

The backend never needs to re-implement normalization, validation, or gate naming conventions.

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
