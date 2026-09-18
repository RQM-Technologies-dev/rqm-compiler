# Backend Capability Model — 0.3.4

RQM Compiler 0.3.4 introduces `BackendCapabilityModel` as the boundary between
representation/query planning and backend/modality lowering.

Initial models describe:

| Model | Framework | Modality | Structured pair rotations | Internal forms requiring materialization |
| --- | --- | --- | --- | --- |
| `qiskit` | Qiskit | gate model | RXX/RYY/RZZ | u1q, su4q |
| `braket_gate_model` | Amazon Braket | gate model | RXX/RYY/RZZ | u1q, su4q |
| `pennylane` | PennyLane | gate model | RXX/RYY/RZZ | u1q, su4q |

This milestone is deliberately behavior-preserving. The pre-existing
`braket_gate_model` named-single-qubit lowering now consults the model.
Qiskit and PennyLane are described but `lower_circuit_for_backend` does not
silently acquire new lowering semantics for them.

The model records native/structured operations, internal operations requiring
materialization, arbitrary-unitary capability, measurement/dynamic-circuit
capabilities, connectivity ownership, modality and lowering profile.

Future modality work should extend this capability boundary rather than put
hardware assumptions into the representation planner. General photonic/CV
computation is not represented by the initial gate-model capability records.
