# Observable input safety contract

The original-circuit and compiled public query APIs validate inputs before
selecting any specialized route. The stable, structured and general evaluator
entry points use the same validation. Cheap invariants and empty circuits do
not bypass the contract.

- Circuit qubit counts are positive integers. Wire indices are non-negative
  integers, excluding bool, and must be in range when circuit size is known.
  Duplicate targets/controls and overlapping controls/targets are rejected.
- Gate names, arity, controls and required parameters follow the compiler gate
  registry. Rotation angles and quaternion components must be finite real
  numbers, excluding bool. Quaternion components must satisfy the existing
  unit-norm tolerance; NaN/Inf cannot satisfy validation.
- An observable is a string or iterable of individual I/X/Y/Z symbols, one per
  qubit, in q0-first order. A one-shot iterable is materialized once. Lowercase,
  whitespace, multi-character elements and unsupported symbols are rejected.
- `max_terms` is a positive integer, excluding bool. Zero, negative, fractional,
  non-finite, string and None values are invalid, including on trivial queries.
- Keyed measurements remain valid circuit IR, but the unitary observable API
  rejects measured circuits. Reset and other unregistered operations remain
  unsupported; no nonunitary semantics are inferred.
- Barriers are preserved in circuit IR and treated as neutral scheduling
  metadata during observable evaluation, never as quantum gate matrices.

Invalid inputs raise ValueError/TypeError (including CircuitValidationError).
Valid input whose exact fallback exceeds its work cap may return
`available=False` with a reason. Its numeric field is not a computed expectation.
Callers must not turn that sentinel into a successful answer.

See `tests/test_query_input_safety.py` for permanent boundary regression coverage.
The tolerance-based qualification establishes the tested scope, not correctness
for every circuit or every resource requirement.
