# AGENTS.md — rqm-compiler

## Architecture boundary rules

`rqm-compiler` is the **backend-neutral circuit compilation layer** in the RQM ecosystem.

Its sole responsibility is to accept RQM circuit objects, normalize them into a canonical gate IR,
and expose that IR for downstream backend translators.

---

## What belongs here

- Canonical circuit container (`Circuit`)
- Operation and gate descriptor objects (`Operation`, `Gate`)
- Validation logic for circuit structure and qubit indices
- Normalization passes (gate name casing, descriptor shape)
- Compilation passes (canonicalize, flatten, basis checks)
- Serialization helpers (`circuit_to_dict`, `circuit_from_dict`)
- Backend-neutral descriptor IR export

---

## What does NOT belong here

- Quaternion algebra — import from `rqm-core`
- Spinor math — import from `rqm-core`
- SU(2) or Bloch sphere math — import from `rqm-core`
- Qiskit imports or objects — belongs in `rqm-qiskit`
- Amazon Braket imports or objects — belongs in `rqm-braket`
- Any execution or simulation logic

**Violating these boundaries creates tight coupling and defeats the purpose of this layer.**

---

## Canonical descriptor schema

The source of truth for every gate operation is a plain dictionary:

```python
{
    "gate": "rx",       # lowercase gate name
    "targets": [0],     # list of target qubit indices
    "controls": [],     # list of control qubit indices
    "params": {"angle": 1.5707963267948966}  # always a dict, even if empty
}
```

Rules:

- Gate names are always lowercase.
- `targets` is always a list.
- `controls` is always a list (empty if not a controlled gate).
- `params` is always a dict (empty dict if the gate has no parameters).

---

## Compiler pass rules

- New passes must preserve descriptor semantics.
- A pass must not introduce backend-specific behavior.
- A pass must be deterministic given the same input circuit.

---

## Testing rules

- Tests must verify roundtrip stability: `circuit → descriptors → circuit`.
- Tests must verify deterministic descriptor normalization.
- Tests must cover validation rejection of invalid circuits.
