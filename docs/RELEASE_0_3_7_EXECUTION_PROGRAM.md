# RQM Compiler 0.3.7 Execution Program

0.3.7 is the first RQM Studio full-stack execution proof as well as the final
research/performance milestone before release acceptance.

## 0.3.7A — Provider abstraction and execution record

Acceptance:

- `QuantumExecutionProvider` contract is stable in `rqm-api`;
- canonical `RQMExecutionRecord` is stable;
- target selection and spending authorization are separate;
- provider observations are not embedded in `rqm-compiler`;
- tests prove null commercial facts remain unknown rather than zero.

## 0.3.7B — First real QPU

Execute one bounded workload through:

`rqm-api -> rqm-compiler -> provider adapter -> real QPU`.

Retain the complete execution record and independent reference comparison.

## 0.3.7C — Second real hardware stack

Repeat through a distinct real hardware stack. Prefer a different modality.
Do not weaken the evidence contract to accommodate provider differences.

## 0.3.7D — Cross-provider + agent-ready workflow

Demonstrate that the same outcome-oriented API workflow can discover/estimate
targets, obtain authorization, execute, retrieve and explain without requiring
the browser Studio. Compare provider-specific materialization and results
without declaring a universal provider winner.

## 0.3.7E — Random-sparse C_Q frontier

Return to the frozen random-sparse family. Profile the first query-expansion
event, test validated contraction-order machinery before inventing a new
representation, and either graduate a proven improvement or record the family
as a promotion/performance boundary.

## Hardware requirement

At least two real hardware stacks remain mandatory. An authorized
ORNL/QSC/QSE-connected target is preferred additional evidence.

## Post-0.4.0 OpenQSE Show and Tell

After RQM Compiler 0.4.0 is released and its benchmark evidence is frozen, prepare a post for the OpenQSE Compiler Working Group `openQSE/wg-compiler` **Show and Tell** page.

The post should compare RQM Compiler 0.4.0 against a conventional/reference quantum compiler on the same reproducible benchmark workloads and environment. Report measured wall-clock compile time, scaling with circuit size/depth, output-circuit metrics where relevant, and resulting speedup ratios. Include methodology, hardware/software versions, repeated-run statistics, raw benchmark artifacts, and links to reproducible code.

Only claim speedups actually demonstrated by the benchmark evidence. Separate compile-time improvements from circuit-quality, execution-time, or asymptotic-complexity claims, and include workloads where RQM does not outperform the reference. The goal is a reproducible technical Show and Tell demonstrating where 0.4.0's representation-aware compiler architecture produces measured advantages.


## Provider-boundary implementation rule

Do not pre-build a broad speculative provider framework before 0.3.7B/0.3.7C. The two real hardware integrations must force the smallest provider abstraction that satisfies both stacks. Stabilize that observed common contract in `rqm-api` only after the evidence exists.

`rqm-compiler` ends at validated target-appropriate computational artifacts and associated compiler evidence. Authentication, account state, cost authorization, provider submission, polling/retrieval, remote execution state, and provider lifecycle belong outside the compiler in `rqm-api` and provider adapters.
