# Representation-Aware API

## Compile

`compile_representation_aware(circuit)` returns a
`RepresentationCompileResult` containing the committed circuit,
`CompilerReport`, and representation-closure accounting.

The compiler seeks the least-general exact representation that remains
information-closed for the computation. This is a policy for validated
structure, not a promise that arbitrary circuits are compact.

## Query

`plan_and_evaluate(compiled, pauli)` selects an exact query/readout route and
writes its telemetry into the same `CompilerReport`.

Current strict specialized routes include:

- validated star/global-Z -> direct relational readout;
- validated chain/global-Z -> boundary transfer;
- validated fixed-depth 1D hardware-efficient/global-Z -> topology-aware
  contraction;
- otherwise -> structured/general exact fallback.

## Complexity telemetry

`representation_complexity` is C_R: representation-owned complexity.

`query_complexity` is C_Q/work units for the selected exact query route.

These are distinct: a compact circuit representation can still have an
expensive query strategy.

## Target capabilities

`get_backend_capability_model(name)` describes a target boundary.
`plan_backend_materialization(circuit, name)` reports internal operations
that must be materialized and unsupported operations before execution.

Initial models: `qiskit`, `braket_gate_model`, and `pennylane`.

## Correctness

Specialized routes are guarded by strict recognizers. Unsupported or
unvalidated structure is not silently treated as a known fast path.
Optimization remains proof-gated and fail-closed.
