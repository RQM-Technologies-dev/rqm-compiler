"""
rqm_compiler.passes.basis
~~~~~~~~~~~~~~~~~~~~~~~~~~
Basis check pass — verifies that all gates in a circuit are within a given basis set.
"""

from __future__ import annotations

from ..circuit import Circuit
from ..descriptors import SUPPORTED_GATES


def check_basis(circuit: Circuit, *, basis: frozenset[str] | None = None) -> list[str]:
    """Check which gates in *circuit* are outside the given *basis* set.

    Args:
        circuit: The circuit to inspect.
        basis: Set of allowed gate names (lowercase).  Defaults to the full
               :data:`~rqm_compiler.descriptors.SUPPORTED_GATES` set.

    Returns:
        A list of gate names (lowercased, deduplicated) that are not in the basis.
        An empty list means the circuit is fully within the basis.
    """
    allowed = basis if basis is not None else SUPPORTED_GATES
    outside: list[str] = []
    seen: set[str] = set()
    for op in circuit.operations:
        gate = op.gate.lower()
        if gate not in allowed and gate not in seen:
            outside.append(gate)
            seen.add(gate)
    return outside
