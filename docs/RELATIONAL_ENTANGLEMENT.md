# Relational Entanglement in rqm-compiler

`rqm-compiler` uses a promotion hierarchy for two-qubit structure:

```text
Bell
  ⊂ AxisHinge
  ⊂ CartanRelation
  ⊂ QuaternionCartanBlock
  ⊂ U(4)
```

These are increasingly general **representations**, not different physical categories of entanglement.

## Design rule

The compiler's preferred flow is:

```text
recognize → compress → propagate relationally → promote if closure breaks → materialize
```

The goal is to retain the smallest exact representation for as long as possible.

### Bell

Bell-sector coordinates are the most specialized representation. They can encode special parity/relative-phase relationships without introducing a general interaction block.

### AxisHinge

`AxisHinge` represents a single exact nonlocal axis and angle. Its portable materializations are the canonical `rxx`, `ryy`, and `rzz` circuit operations.

### CartanRelation

`CartanRelation` carries the commuting nonlocal Cartan coordinates needed when a window spans multiple interaction axes. It represents the nonlocal content without unnecessarily carrying local factors or a dense matrix.

### QuaternionCartanBlock

`QuaternionCartanBlock` combines local quaternion/SU(2) factors with the Cartan nonlocal relation. This is the structured general two-qubit representation used by the RQM entanglement/compiler boundary. The existing internal `su4q` descriptor is a materialized compiler block carrying this representation.

### U(4)

A dense `U(4)` matrix is the fully general mathematical envelope. It remains appropriate for verification, reconstruction, interoperability, and fallback, but is not the preferred working representation when a smaller exact form is available.

## Compiler ownership

`rqm-compiler` owns recognition and optimization policy, but not the underlying decomposition mathematics. `rqm-entanglement` owns two-qubit relational geometry, Cartan decomposition/reconstruction, classification, and associated mathematical operations. `rqm-core` owns local quaternion/SU(2) mathematics.

The public `rqm-circuits` boundary remains standard-compatible. Relational compiler metadata must not force private structured representations into the public wire format. Backends receive materialized operations such as RXX/RYY/RZZ or a backend-specific decomposition when required.

## Promotion and demotion

A relational representation may remain at its current level while composition stays closed there. The compiler promotes upward only when exact representation at the current level is insufficient. Optimization may also expose a smaller exact representation again, allowing a block to be demoted before backend materialization.

This policy is intended to avoid representational expansion, not to bypass semantic verification. Existing proof-gated/fail-closed compiler rules still apply.

## Backend boundary

Backends should consume the simplest form they natively support. An axis hinge should lower directly to RXX/RYY/RZZ where the provider supports those gates. More general Cartan or quaternion-Cartan structure may require synthesis into the backend's native gate set.

Performance claims remain workload- and backend-specific. The hierarchy defines compiler semantics and representation strategy; it does not by itself establish a universal runtime or fidelity advantage.
