# Migrating from rqm-compiler 0.3 to 0.4

0.4 is an additive evolution of the 0.3 compiler, not a new public circuit
wire format.

## Existing code

`optimize_circuit(circuit)` remains supported. Existing `Circuit`,
`Operation`, descriptor and proof-gated optimization semantics remain.

## Preferred 0.4 path

```python
from rqm_compiler import compile_representation_aware, plan_and_evaluate

compiled = compile_representation_aware(circuit)
result = plan_and_evaluate(compiled, "ZZZZ")
report = compiled.report
```

The planner adds representation closure accounting, query-aware exact routing,
topology recognition and conservative fallback.

## CompilerReport additions

0.4 adds C_R/C_Q, representation level/histogram, topology, selected query
route, contraction metrics, promotion/fallback information, and backend
capability/materialization telemetry. Consumers should tolerate absent/null
fields when no corresponding planning stage was requested.

## Backend lowering

Use `BackendCapabilityModel` and `compile_for_backend` /
`lower_circuit_for_backend` for explicit target materialization. RQM-internal
`u1q` and `su4q` are not new external wire requirements.

## Compatibility

- Python: 3.11+
- `rqm-circuits` public schema: no 0.4 breaking change required
- `rqm-core`: owns local quaternion/SU(2)/shared operator math
- `rqm-entanglement`: owns AxisHinge/Cartan/nonlocal mathematics
- backend bridges: own framework/device translation and execution

Do not import `stable_prototype` in new integrations; use the public planner
API.
