# Composable phase contract

The default optimizer/verifier preserve the complete unitary, including global phase, within their declared numerical tolerance. RX/RY/RZ(2pi) equal -I and must remain distinguishable from I when a block is controlled. Quaternion q and -q therefore remain distinct in exact compilation. Named U(2) gates whose scalar phase is not represented in u1q stay named; exact cancellation of adjacent involutions remains allowed. Core Euler lowering retains the SU(2) lift and does not wrap individual angles modulo 2pi.

verify_equivalence defaults to phase_invariant=False. Explicit phase_invariant=True is terminal-circuit evidence only and cannot authorize coherent or controlled reuse. The corresponding low-level to_u1q_pass/sign_canon_pass option is opt-in. The historical standalone normalize_quaternion helper retains its legacy default; exact compiler paths explicitly disable sign canonicalization.

Verification failure retains the original candidate rather than weakening the tolerance. Compiler JSON descriptors preserve u1q signs. Cross-package bridge serialization, circuit-global phase metadata and controlled composite gates require separate qualification; this contract does not add support for those operations. The independent controlled-embedding tests check the resulting matrix, not a provider controlled-gate path.

This candidate depends on the matching rqm-core phase-preserving Euler lowering fix. The unchanged dependency range alone does not establish that an installed core contains that fix. Qualification must record source revisions, and a released dependency profile must be tested before release. This change is a local source candidate, not a deployed release.
