# Generalized transfer and bounded-frontier queries

`evaluate_observable` and `plan_and_evaluate` accept one I/X/Y/Z label per qubit
in qubit-number order. One-pass stars now support any hub, arbitrary product
Pauli observables, arbitrary product preparations, and final local rotations.
The old global-Z helper remains compatible. Local operators are remapped by
hub/leaf identity, never by the numeric ordering of the original wire names.

After the specialized routes, the planner attempts chronological frontier
transfer with `max_frontier_qubits=4` by default. It first removes gates outside
a conservative backwards query-support cone and delays separable preparation.
A qubit is traced out with its requested observable after its last retained use.
This allows local queries, chain products, interleaved stars and limited revisits
without enumerating a global Pauli expansion when the active frontier is small.

The plan computes peak active width before allocating numeric frontier tensors.
A width w bounds an individual frontier tensor to 4**w complex entries; input
storage, cached local matrices and simultaneous temporaries are additional.
Rejected schedules fall back to the existing Pauli evaluator, whose `max_terms`
budget is independent and can overshoot after a gate expansion. Neither budget
is a universal process-memory limit. Width rejection does not prove optimal
contraction width or intrinsic hardness. Set `max_frontier_qubits=0` to disable
the new route when comparing with the Pauli fallback.

`evaluate_observables(compiled, labels)` evaluates a batch, reusing up to 16
frontier plans and their local matrices. Reuse requires identical circuit digest,
query support, and frontier budget. Returned numeric values are never cached.
Circuit mutation invalidates reuse, including mutations between generator yields.
Specialized star/chain/topology routes currently do not share this plan cache.
Each QueryResult records its own `plan_reused`, `frontier_width`, intermediate
size/unit and rejection reason; the mutable CompilerReport describes the last
query. No cross-call/global cache is retained.

These routes remain numerical computations: algebraic exactness does not remove
floating-point error. Independent reference tests cover all 64 three-qubit
Pauli products for each hub position, random wire orders and angles, near-zero
and cancellation cases, selective SU(4) output, and cache mutation guards.
