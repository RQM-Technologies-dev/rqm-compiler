# Direct-star query safety contract

The direct-star global-Z route is optional. Correctness is mandatory; faster
execution never justifies accepting an unproven gate placement.

The recognizer accepts only this ordered shape:

1. Initial single-qubit preparation gates.
2. Uninterrupted hub-leaf two-qubit episodes, each leaf visited once.
3. Final single-qubit gates that preserve Z under the existing numerical check.

A single-qubit gate between interactions causes the specialized route to decline
the circuit, even when a more sophisticated commutation proof might establish
safety. The public planner then uses its existing exact fallback. In particular,
an RZ gate's commutation with the final Z measurement does not justify moving it
past later interactions.

If the fallback exceeds its configured work budget, callers must honor
`available=False`. The result's numeric field is not a valid expectation when
unavailable. No guessed or approximate answer should be substituted as exact.

Permanent coverage in `tests/test_star_placement_safety.py` includes an independent
NumPy statevector oracle, both public query paths, interleaved hub/leaf RZ
counterexamples, a 117-case held-out insertion sweep, budget exhaustion, and
preservation of the narrow safe route. Backend-dependent qualification additionally
compares independent Qiskit statevectors with original and compiled queries.

Require zero failing supported-case checks before accepting a change. Qualification
uses explicit floating-point tolerances; a 100% pass rate for the tested suite is
not a proof of correctness for every possible circuit or unrestricted workload.
