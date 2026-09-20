# Compiler acceptance and the OpenQSE / ORNL execution workstream

Scope corrected September 20, 2026. The earlier version of this document
combined compiler release acceptance with production execution integration.
This document replaces that combined gate; earlier text remains in Git history.

## Compiler release scope

`rqm-compiler` owns backend-neutral compilation, query planning, exactness
guards, backend materialization planning and compiler reports. The completed
IBM Marrakesh and Rigetti/Braket experiments supply bounded real-hardware
validation. Consolidate their evidence and check applicability to the released
code; do not require another hardware integration project to publish the
compiler. See [0.3.8 acceptance](RELEASE_0_3_8_ACCEPTANCE.md).

Final acceptance covers public-package installation, certified-source parity,
affected regression checks, numerical/benchmark/hardware evidence and accurate
documentation. Wider frontier research, new planner routes and new provider
features are outside this frozen pass.

## Separate OpenQSE-rqm-adapter / ORNL workstream

The following are integration deliverables, not compiler publication gates:

- Use `openqse-rqm-adapter` for scientific interoperability and the authorized
  ORNL/OpenQSE execution path.
- Keep the provider abstraction and common execution/provenance record in
  `rqm-api` and the appropriate bridges.
- Qualify durable cross-provider submission, polling, retrieval, restart and
  explanation behavior through the API when developing that integration.
- Keep credentials, target observations, spending authorization and commercial
  accounting outside the compiler.
- Preserve actual provider/device identities, submitted and native artifacts,
  job IDs, measurements, reference comparisons and cost observations.

The completed research dispatches do not certify a production HTTP execution
workflow. The two providers are distinct stacks; both tested devices are
superconducting, so the evidence does not demonstrate different modalities.

## Post-0.4.0 OpenQSE Show and Tell

After compiler 0.4.0 is released and its evidence is frozen, prepare the
OpenQSE Compiler Working Group Show and Tell using reproducible workloads,
repeated-run statistics, raw evidence and exact software versions. Separate
compile-time, circuit-quality and execution-time results. Retain workloads
where RQM does not outperform the reference. Publication of the presentation
and ORNL integration are separate from compiler release acceptance.
