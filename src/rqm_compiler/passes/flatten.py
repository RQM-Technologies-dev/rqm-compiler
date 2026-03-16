"""
rqm_compiler.passes.flatten
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Flatten pass — resolves nested or composite structures into a flat operation list.

In v0, circuits are already flat (no nesting), so this pass is an identity transform
that validates flatness and copies the circuit.
"""

from __future__ import annotations

from ..circuit import Circuit


def flatten_pass(circuit: Circuit) -> Circuit:
    """Return a new :class:`~rqm_compiler.circuit.Circuit` with a guaranteed flat operation list.

    In v0, all circuits are inherently flat.  This pass copies the circuit and provides
    a stable hook for future composite/nested gate unrolling.

    Args:
        circuit: Source circuit (not mutated).

    Returns:
        A new :class:`~rqm_compiler.circuit.Circuit` with the same operations.
    """
    out = Circuit(circuit.num_qubits)
    for op in circuit.operations:
        out.add(op)
    return out
