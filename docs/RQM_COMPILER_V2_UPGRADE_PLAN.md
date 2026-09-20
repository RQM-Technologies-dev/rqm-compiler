# RQM Compiler 0.4.0 Upgrade Plan

> **Status:** Working upgrade plan. The current stable prototype is the proving
> ground for the future main `rqm-compiler` 0.4.0. Features described as stable
> below have passed the repository's exact-reference gates in their stated
> scope. Experimental features do not become 0.4 defaults until independently
> validated.

## Executive summary

RQM Compiler v1 is principally a **quaternionic circuit optimizer**. It already
provides the foundation that 0.4 keeps: backend-neutral circuit IR, quaternionic
SU(2) operations, structured two-qubit machinery, canonicalization,
merge/cancellation passes, adaptive Cartan machinery, verification, and
backend lowering.

RQM Compiler 0.4 upgrades that foundation into a **representation-aware,
query-aware quantum computation planner**.

The central rule is:

> **Use the least-general exact mathematical representation that preserves both
> algebraic closure and all information required by the requested computation.**

Instead of forcing every job through one representation/readout strategy, 0.4
recognizes mathematical and topological structure, selects a validated exact
route, and promotes/falls back conservatively when that route does not apply.

## What stays from the current compiler

0.4 is an upgrade, not a rewrite. It retains the existing compiler foundation:

- backend-neutral circuit representation;
- quaternionic / SU(2) single-qubit representation;
- structured two-qubit representations and Cartan machinery;
- normalization and canonicalization;
- quaternion merge and cancellation;
- adaptive representation machinery;
- exact/equivalence verification;
- backend-neutral descriptors and target lowering.

The prototype currently lives in the same repository and deliberately reuses
these components.

## What 0.4 adds

### 1. Representation-aware compilation

Representation becomes an optimization variable. Conceptually, 0.4 reasons over
a promotion hierarchy such as

```text
Quaternion
  -> AxisHinge
  -> Cartan / structured relation
  -> boundary / topology representation
  -> general exact representation
```

The compiler stays in the smallest representation known to be exact and
promotes only when closure or information requirements demand it.

### 2. Representation complexity: C_R

0.4 exposes representation-owned complexity accounting:

```text
C_R = size of the minimum closed RQM representation required by the computation
```

This is not a claim that every n-qubit state has a compact representation. It
measures the representation actually required by a particular structured
computation.

Measured examples in the current benchmark families include:

- validated star family: `C_R(n) = 11n - 3`;
- validated chain family: `C_R(n) = 7n - 3`.

These formulas are empirical statements about those benchmark families only.

### 3. Query-aware compilation

v1 primarily asks how to optimize the supplied circuit. 0.4 additionally treats
the requested observable/query as compiler input.

Conceptually:

```text
(circuit, query)
    -> structure analysis
    -> least-general exact representation
    -> exact query plan
    -> result
```

A request for one observable does not automatically require materializing all
information needed to reconstruct the full state.

### 4. Query complexity: C_Q

0.4 distinguishes the cost of maintaining the computation from the cost of
extracting the requested answer:

```text
C_R = representation complexity
C_Q = query/readout complexity
```

This distinction was decisive for chains. At n=12 the circuit representation
was already compact (`C_R = 81`), while the old readout reached 96,899 work
units. The validated boundary-transfer path reduced the query work to 11.

### 5. Topology-aware readout planning

0.4 recognizes validated interaction/topology classes and dispatches to
specialized exact readout algorithms.

The current stable selector is conceptually:

```text
global-Z query
  |
  +-- validated star
  |     -> direct_star_relational
  |
  +-- validated chain
  |     -> chain_boundary_transfer
  |
  +-- validated fixed-depth 1D hardware-efficient
  |     -> topology_hardware_1d
  |
  +-- otherwise
        -> structured/general exact fallback
```

Recognizers are deliberately strict. A fast path is not used outside its
validated scope.

### 6. Direct relational star readout

For the validated star/global-Z family, 0.4 avoids full-state or large observable
expansion and performs `n - 1` relational contractions.

The algorithm was independently checked against exact references at tractable
sizes and then exercised through 512 qubits without the exponential reference.

### 7. Exact chain boundary transfer

For the validated chain family, 0.4 carries an exact map-valued boundary object

```text
T : O_boundary -> O'_boundary
```

instead of allowing the observable expansion to explode.

In the taxonomy development sequence, query work changed from

```text
18 -> 1,457 -> 96,899
```

to

```text
3 -> 7 -> 11
```

for `n = 4, 8, 12`, while retaining machine-precision agreement with the
reference.

### 8. Topology-aware fixed-depth hardware-efficient contraction

The original structured observable route grew from 126 to 20,163 terms and
then exceeded the 250,000-term budget at n=12.

The validated topology-aware path instead contracts the circuit's space-time
network in a favorable order. For the tested two-layer 1D nearest-neighbor
family, the largest intermediate was

```text
16, 32, 32
```

at `n = 4, 8, 12`.

A stress test across 11 conditions covering qubit count and depths 2-4 passed
11/11 exact-reference gates, with maximum error approximately
`5.55e-16`.

At fixed depth 2, the largest intermediate remained 32 through n=20 in the
tested family. Increasing depth increased intermediate size substantially,
providing evidence that contraction/boundary width and depth can be more
important than qubit count alone for this structured workload.

This is empirical evidence, not a general asymptotic theorem.

### 9. Information closure

0.4 strengthens the old notion of algebraic closure.

Research experiments showed that a representation may remain algebraically
closed while discarding information needed by a later observable. Therefore a
representation may remain compact only when it satisfies both:

```text
algebraic closure
+
query-information closure
```

This is a core promotion/demotion criterion for 0.4.

### 10. Conservative promotion and fail-closed behavior

Specialized algorithms are used only when a validated recognizer accepts the
job. Otherwise 0.4 falls back to a more general exact representation/evaluator.

If an exact route exceeds a configured safe budget and no validated
specialization applies, the compiler should report that condition rather than
silently substitute an unvalidated approximation.

### 11. Explainable compiler reports

0.4 should make representation decisions visible in `CompilerReport`.
Target telemetry includes:

```text
representation
C_R
query / observable
C_Q or work units
recognized topology
selected readout strategy
promotion count
maximum representation level
contraction / boundary width when applicable
largest intermediate when applicable
fallback used
exactness / validation metadata
```

This makes it possible to explain not only what was compiled, but why a
particular mathematical route was selected and where complexity arose.

### 12. Modality separation

0.4 should preserve a modality-independent optimization layer and separate it
from backend/modality lowering.

The intended architecture is:

```text
program / interoperable IR
        |
        v
RQM representation-aware optimization
        |
        v
backend capability model
        |
        +--> superconducting
        +--> trapped ion
        +--> neutral atom
        +--> spin
        +--> other gate-model targets
```

The current mathematical optimizer is largely gate-model/modality independent;
full support for fundamentally different computational models such as general
photonic mode/CV programs requires additional IR and capability work.

The design principle is: **RQM optimizes the computation; adapters lower it to
the modality.**

## Current benchmark snapshot

The latest seven-family taxonomy uses n=4,8,12 and exactness gate
`abs(error) <= 1e-9`.

All 21 tested conditions were exact-valid.

| Family | Tested coverage | Median RQM end-to-end ratio vs Qiskit/Aer | Stable route |
| --- | ---: | ---: | --- |
| Local | 100% | 3.37x faster | general exact |
| Clifford | 100% | 1.44x faster | general exact |
| Star | 100% | 2.64x faster | direct relational |
| Chain | 100% | 2.02x faster | boundary transfer |
| Clifford+T | 100% | 1.84x faster | general exact |
| Hardware-efficient | 100% | 0.69x (slower median at these sizes) | topology-aware |
| Random sparse | 100% | 0.34x (slower) | general exact |

These numbers are benchmark-specific, environment-sensitive measurements, not
universal performance claims. Speedups are reported only for exact-valid
conditions.

The dedicated hardware-efficient stress test also demonstrated the expected
large-size crossover against the repository's independent exact state-vector
reference; that comparison is distinct from Qiskit/Aer and should not be mixed
with the taxonomy ratios.

## Stable versus experimental

### Stable / eligible for 0.4 integration

- existing quaternionic compiler foundation;
- representation-owned `C_R`;
- structured exact observable propagation;
- direct relational star/global-Z path;
- exact chain boundary-transfer path;
- exact map-valued boundary-transfer primitive;
- validated topology-aware fixed-depth 1D hardware-efficient path;
- strict recognizers and general exact fallback.

### Experimental / not a 0.4 default

- minimal Quaternionic Spectral Transfer (QST) parameterizations;
- rotor-only recursive readout;
- rotor + one-relation recursive readout;
- fixed-operator Cartan recursive readout;
- unvalidated general tree/graph contractions;
- any claim of polynomial simulation for arbitrary quantum circuits.

Experimental work must not be promoted merely because it is compact or fast.

## Graduation policy

A new specialized representation or readout path should enter the stable 0.4
surface only after:

1. an independent exact reference is available at tractable sizes;
2. every headline benchmark condition passes `abs(error) <= 1e-9`;
3. the candidate path does not secretly materialize the representation it
   claims to avoid;
4. its applicability is protected by a strict recognizer/capability gate;
5. regression tests assert both correct selection and correct fallback;
6. benchmark workflows remain under the project's 10-minute test limit.

## Planned 0.4 public architecture

The intended evolution is:

```text
Current RQM Compiler
  quaternionic circuit optimizer
             |
             v
RQM Compiler 0.4
  representation-aware quantum computation planner
             |
             +-- structure recognition
             +-- least-general exact representation
             +-- C_R accounting
             +-- query-information closure
             +-- topology/query planner
             +-- C_Q / readout accounting
             +-- specialized exact algorithms
             +-- conservative promotion/fallback
             +-- explainable CompilerReport
             +-- modality/backend capability boundary
```

## Relationship to OpenQSE

`openqse-rqm-adapter` should consume proven 0.4 capabilities rather than become
the research laboratory where they are invented.

The desired boundary is:

```text
OpenQSE / standard IR
        |
        v
RQM Compiler 0.4 optimization domain
        |
        v
standard target IR / runtime / modality adapter
```

This lets RQM remain a specialized representation-aware compiler technology
inside an interoperable ecosystem rather than requiring the ecosystem to adopt
RQM's internal mathematical representations.

## Definition of 0.4 success

RQM Compiler 0.4 is successful when it can reliably answer:

1. What mathematical structure does this computation contain?
2. What is the least-general exact representation that preserves it?
3. What information does the requested query actually require?
4. What topology/contraction strategy minimizes exact work?
5. When must the representation be promoted?
6. What backend/modality constraints apply only at lowering time?
7. Can the compiler explain and measure every one of those decisions?

In short:

> **v1 optimizes quaternionic circuits. 0.4 plans exact quantum computations
> using the smallest validated representation appropriate to the circuit,
> query, topology, and target.**

## Frozen release benchmark

The 0.4 development line has a canonical reproducible Qiskit/Aer comparison defined by [benchmarks/BASELINE.md](../benchmarks/BASELINE.md) and the `Release benchmark baseline` workflow. Its JSON, CSV and Markdown outputs are uploaded as immutable per-run GitHub Actions artifacts. The baseline uses the public representation-aware API rather than importing prototype internals.


## 0.3.x -> 0.4.0 release milestones

### 0.3.4 — Backend/modality capability boundary

Acceptance requires a public `BackendCapabilityModel`, capability-driven
materialization planning, backend telemetry in `CompilerReport`, and
regression evidence that existing backend lowering semantics are unchanged.

### 0.3.5 — Cross-stack release qualification

Qualify the compiler against the required RQM ecosystem bridges, API, Studio,
OpenQSE adapter, packaging and clean-install paths.

### 0.3.6 — Public documentation and claim freeze

Publish migration guidance, examples, benchmark methodology, architecture and
scientific claim boundaries.

### 0.3.7 — Frozen compiler and coordinated package certification

The published prototype freezes the compiler runtime and qualifies its wheels,
source distributions, released dependency floors, numerical boundaries and
cross-stack interfaces. See [the feature freeze](RELEASE_0_3_7_FREEZE.md) and
[retained certification](../evidence/0.3.7-release-20260920/README.md).

Real-hardware testing has already been completed on IBM Marrakesh and Rigetti
Cepheus-1-108Q through Amazon Braket. These bounded experiments validate the
submitted workloads; they do not establish a hardware speedup or universal
compiler correctness. Their retained records and applicability to the released
compiler are consolidated in [final acceptance](RELEASE_0_3_8_ACCEPTANCE.md).

### 0.3.8 — Final release acceptance

This milestone closes the compiler's evidence and packaging work before a
separate decision to promote `rqm-compiler 0.4.0`:

1. Verify clean installation and compatibility using released dependencies.
2. Compare published wheel and sdist runtime payloads with certified code;
   rerun checks affected by dependency, packaging or runtime changes.
3. Consolidate benchmark, numerical and completed hardware evidence, preserving
   revisions, hashes, measurement limitations and all unavailable cases.
4. Reconcile documentation and release configuration with this scope.

Reuse unchanged certified artifacts and historical hardware records. A changed
archive hash alone is not a runtime change; source payload and dependency
comparisons establish which evidence can be reused. Replaying retained hardware
inputs offline checks applicability without claiming a new QPU execution.

The compiler release does not require API deployment, production job lifecycle,
provider credentials, billing, or integration with ORNL. API orchestration,
provider integration, durable submission/retrieval and ORNL/OpenQSE execution
belong to the separate **openqse-rqm-adapter / ORNL workstream**, with `rqm-api`
and provider bridges owning the appropriate implementation boundaries.
See [the workstream boundary](RELEASE_0_3_7_EXECUTION_PROGRAM.md).

A generated release PR is preparation, not acceptance or authorization to publish
0.4.0. Keep the released version in the manifest until its successor is merged;
remove the one-time 0.3.7 version override so a documentation/patch successor
can be prepared normally. No new compiler features are required by this pass.


## 0.3.6 public release contract

The 0.3.6 milestone freezes the public explanation surface in the README,
migration guide, representation-aware API guide, CompilerReport field guide,
claims/limitations document, runnable public example, frozen benchmark
contract, backend capability documentation, and documentation-contract CI.

Exit gate: a developer unfamiliar with RQM must be able to install the package,
run the public example, understand C_R/C_Q and specialized/fallback routing,
interpret CompilerReport, understand backend materialization boundaries, and
distinguish demonstrated benchmark results from research hypotheses using the
public repository alone.
