"""
rqm_compiler.passes.sign_canon
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Sign-canonicalization pass for u1q gates.

Because ``q`` and ``-q`` represent the same SU(2) element, there is a degree
of freedom in how a unit quaternion is stored.  This pass enforces the
canonical convention::

    w ≥ 0

for every ``u1q`` gate in the circuit, which gives:

* **Deterministic equality** — two circuits that encode the same sequence of
  rotations will compare equal as descriptors without needing ``±q`` checks.
* **Cache stability** — quaternion tuples can be safely used as dict keys or
  in sets without collision between ``q`` and ``-q``.
* **Optimization stability** — downstream passes (e.g. further merging or CSE)
  can rely on a single canonical form.

Non-u1q gates are passed through unchanged.

This pass is the final step in the default optimization pipeline, applied after
:func:`~rqm_compiler.passes.merge_u1q.merge_u1q_pass`.  It is also safe to
apply independently to any circuit that contains ``u1q`` gates.
"""

from __future__ import annotations

from ..circuit import Circuit
from ..normalize import normalize_quaternion
from ..ops import Operation


def sign_canon_pass(circuit: Circuit) -> Circuit:
    """Return a new circuit with all u1q quaternions in canonical form (w ≥ 0).

    Every ``u1q`` operation whose ``w`` component is negative is replaced with
    its sign-negated equivalent ``(-w, -x, -y, -z)``, which represents the same
    SU(2) element.  All other gates are copied unchanged.

    Args:
        circuit: Source circuit (not mutated).

    Returns:
        A new :class:`~rqm_compiler.circuit.Circuit` where every ``u1q``
        quaternion satisfies ``w ≥ 0``.

    Example::

        from rqm_compiler import Circuit
        from rqm_compiler.passes import sign_canon_pass

        c = Circuit(1)
        c.u1q(0, -1.0, 0.0, 0.0, 0.0)   # w < 0 — non-canonical

        canon = sign_canon_pass(c)
        d = canon.to_descriptors()[0]
        assert d["params"]["w"] >= 0      # now w = 1.0
    """
    out = Circuit(circuit.num_qubits)
    for op in circuit.operations:
        if op.gate == "u1q":
            w, x, y, z = normalize_quaternion(
                op.params["w"],
                op.params["x"],
                op.params["y"],
                op.params["z"],
                allow_renormalization=True,
            )
            out.add(
                Operation(
                    gate="u1q",
                    targets=list(op.targets),
                    controls=list(op.controls),
                    params={"w": w, "x": x, "y": y, "z": z},
                )
            )
        else:
            out.add(op)
    return out
