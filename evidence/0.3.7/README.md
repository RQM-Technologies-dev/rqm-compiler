# 0.3.7 candidate integration evidence

Status: compiler and targeted API integration checks passed; both real-hardware
demonstrations remain pending. This is a provisional candidate benchmark, not
release acceptance. Rerun after the hardware runs on the deployed artifacts.

Compiler source: `baba100a7715b783671d92066a15804aa08e1e99`.
Package metadata remains 0.3.0 from the repository; identify this candidate by
commit and wheel SHA-256, not its pre-existing version string. No release was
published or moved to 0.4.0.

408 compiler tests passed, 1 skipped, against the installed candidate wheel.
Eight focused API tests passed, including restart recovery, hinge translation,
report preservation, and independent dense equivalence of a regional SU(4)
fallback on nonzero global qubit indices. The full API suite was not run.

All 21 frozen conditions (seven families at 4, 8 and 12 qubits) produced exact
answers within 1e-9; maximum error was 2.11e-15. All 21 committed optimizations
with regional proofs. This does not prove that every optimized circuit is
better for every device or query.

| Family | Exact | Median end-to-end reference/RQM ratio |
| --- | ---: | ---: |
| local | 3/3 | 1.970x |
| clifford | 3/3 | 1.318x |
| star | 3/3 | 1.589x |
| chain | 3/3 | 2.330x |
| clifford_t | 3/3 | 1.544x |
| hardware_efficient | 3/3 | 0.607x |
| random_sparse | 3/3 | 0.606x |

A ratio above 1 favors RQM. These are small, two-repeat smoke measurements,
not statistically established performance claims. The conventional reference
is Qiskit level-3 transpilation plus Aer statevector execution; the RQM path is
regional compilation plus an exact observable query. Their work is different:
this is a query end-to-end comparison, not a universal compiler speedup.
Compilation and readout times are separately recorded in the raw rows.

Query evaluation uses the retained, verified-equivalent input to preserve
recognized star/chain structure. The compiled output is separately verified;
mutation of either circuit invalidates the source-selection guard. Raw rows
record this basis explicitly. Circuit representation counts and query work
are different quantities. Pauli terms, leaf/edge transfers and complex tensor
entries carry different units. Unmeasured hardware-topology contraction width
is null. Promotion counts describe committed transformations, not adjacent
gates with different representation levels.

Correctness guards reject invalid Pauli strings and exclude interleaved local
operations from the star specialization. Regional compilation preserves
measurement/barrier boundaries, shares adaptive work budgets across regions,
rolls back on failed proofs, and remaps nested SU(4) fallback descriptors.

Random sparse circuits remain a performance/expansion boundary; this candidate
adds no claim of bounded intermediate size for arbitrary hinge networks.
The max_terms limit applies to the structured Pauli route, not a universal
memory budget for every topology route.

Reproduction: install the recorded compiler and entanglement wheels, recreate
the observed dependencies, and run `benchmarks/job_taxonomy.py` with
`RQM_CANDIDATE_WHEEL` set to the compiler wheel and `RQM_CANDIDATE_COMMIT` set to
the source commit above. The benchmark records the installed module location,
versions, wheel hash, optimization status, proof method and query telemetry.
See job_taxonomy.json for raw rows and provenance. The artifact archive retains
both exact wheels and their SHA-256 manifest.
