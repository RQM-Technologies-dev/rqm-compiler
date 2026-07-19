# EXP-012 `su4q` compiler boundary

The internal `su4q` descriptor consumes `QuaternionCartanBlock` from
`rqm-entanglement` commit `f2105bb694764d8d73798d3f482a598db39226e0`, whose source evidence is EXP-012 commit
`615de9f5143ed603ca732b33a287e3e4f654c4c9`.

The compiler does not implement KAK/Weyl decomposition and contains no Qiskit
imports. It constructs exact dense 4×4 windows, delegates decomposition and
reconstruction, and emits a candidate only after validation and numerical
equivalence within `1e-10`.

Extraction defaults to `analyze_only`. `emit_candidate` keeps the original
circuit and records the candidate in `CompilerReport`.
`replace_if_backend_requests` replaces a verified window only when the caller
explicitly sets `backend_requests_su4q=True`; a final circuit-level verifier is
still required. The standard `optimize_circuit` pipeline remains unchanged.

This is standard complex quantum mechanics. It makes no unique-information,
native quaternionic-composite, gate-count, synthesis, runtime, or IBM hardware
advantage claim.
