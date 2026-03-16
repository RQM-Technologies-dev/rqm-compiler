"""
rqm_compiler.passes.canonicalize
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Canonicalization pass — ensures every operation is in the canonical IR form.
"""

from __future__ import annotations

from ..circuit import Circuit
from ..normalize import normalize_operation


def canonicalize_pass(circuit: Circuit) -> Circuit:
    """Return a new :class:`~rqm_compiler.circuit.Circuit` with every operation canonicalized.

    In v0 the canonicalization step is equivalent to full normalization: gate names are
    lowercased, list fields are materialized, and param dicts are regularized.

    Args:
        circuit: Source circuit (not mutated).

    Returns:
        A new :class:`~rqm_compiler.circuit.Circuit` with canonicalized operations.
    """
    out = Circuit(circuit.num_qubits)
    for op in circuit.operations:
        out.add(normalize_operation(op))
    return out
