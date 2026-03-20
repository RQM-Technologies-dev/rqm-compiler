"""
rqm_compiler.depth
~~~~~~~~~~~~~~~~~~
Circuit depth computation utilities.
"""

from __future__ import annotations

from .circuit import Circuit


def circuit_depth(circuit: Circuit) -> int:
    """Compute the depth of *circuit*.

    The depth is the number of time-steps required to execute the circuit when
    operations on disjoint qubits are executed in parallel.

    Args:
        circuit: The circuit to measure.

    Returns:
        The circuit depth (0 for an empty circuit).
    """
    if not circuit.operations:
        return 0

    qubit_depth: dict[int, int] = {q: 0 for q in range(circuit.num_qubits)}

    for op in circuit.operations:
        qubits = set(op.targets) | set(op.controls)
        if not qubits:
            continue
        layer = max(qubit_depth.get(q, 0) for q in qubits) + 1
        for q in qubits:
            qubit_depth[q] = layer

    return max(qubit_depth.values()) if qubit_depth else 0
