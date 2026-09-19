# Native observable kernels

Single-qubit observable propagation uses the canonical rqm-core quaternion
rotation. Global phase drops out of U†PU; the compiler only adapts gate names.

Fresh-leaf stars and the validated hinge chain contract real I/X/Y/Z
coefficients using analytic rxx/ryy/rzz and signed CX actions from
rqm_entanglement.pauli_transfer. Generic star gates retain the dense pair route.

Frontier plans consisting of local gates, hinges and CX close exactly on real
Pauli coefficient tensors. Other pair gates retain the existing complex density
route. Admission still checks the chronological frontier width before numeric
evaluation. This is not an optimal-width search or a factorization theorem:
entries still scale as 4**width. Each real entry is 8 bytes versus 16 for the
complex fallback; process memory includes plans, caches and temporary arrays.
Query telemetry identifies these entries as `real_pauli_coefficients`.

Cartan promotion skips reconstruction and KAK only when the supplied rotation
coordinates already map exactly into the canonical Weyl chamber. Local frames
and their global phase are retained by QuaternionCartanBlock.from_components;
noncanonical coordinates retain exact decomposition. Generic composition and
verification remain unchanged.

These candidate paths require the companion rqm-entanglement analytic transfer
implementation. Install the exact sibling wheels pinned by the adapter's
candidate manifest; package version labels alone do not identify these candidates.

Reproduce staged runtime, matrix helper calls, NumPy allocation API calls and
tracemalloc measurements with the adapter's scripts/probe_native_kernels.py.
Tracemalloc snapshot block counts are retained allocations, not total allocation
traffic. Timing is collected separately from tracing and instrumentation.
