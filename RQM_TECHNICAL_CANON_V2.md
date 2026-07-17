# RQM Technical Canon v2 Alignment

`rqm-compiler` owns deterministic normalization, canonicalization, `u1q`
fusion, verification, serialization, and backend-neutral lowering.

The IR is standard-compatible: a unit quaternion and its complete `SU(2)`
matrix encode the same single-qubit rotation information. Phase-safe sign
handling and Hamilton-product order are semantic correctness requirements, not
alternative mechanics.

EXP-003 supports the tested ordered-fusion semantics. EXP-009 Track B did not
show a compiler-runtime advantage and did not pass its universal serialized-size
gate. Do not describe this compiler as quantum-mechanically richer or faster
without a new matched benchmark.

Evidence authority:
`RQM-Technologies-dev/rqm-experiments/docs/RQM_TECHNICAL_CANON_V2.md`.
