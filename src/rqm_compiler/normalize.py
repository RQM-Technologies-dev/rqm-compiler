"""
rqm_compiler.normalize
~~~~~~~~~~~~~~~~~~~~~~
Normalization utilities that ensure operations conform to the canonical IR shape.
"""

from __future__ import annotations

from typing import Any

from .circuit import Circuit
from .ops import Operation


def normalize_operation(op: Operation) -> Operation:
    """Return a new :class:`Operation` with a fully normalised canonical shape.

    Normalisation steps:

    * Gate name is lowercased.
    * ``targets`` is guaranteed to be a list.
    * ``controls`` is guaranteed to be a list.
    * ``params`` is guaranteed to be a dict.

    The original operation is not mutated.
    """
    return Operation(
        gate=op.gate.lower(),
        targets=list(op.targets),
        controls=list(op.controls),
        params=dict(op.params),
    )


def normalize_circuit(circuit: Circuit) -> Circuit:
    """Return a new :class:`Circuit` with all operations normalised.

    The original circuit is not mutated.

    Args:
        circuit: The source circuit.

    Returns:
        A new :class:`Circuit` containing normalised copies of all operations.
    """
    normalised = Circuit(circuit.num_qubits)
    for op in circuit.operations:
        normalised.add(normalize_operation(op))
    return normalised


def normalize_descriptor(descriptor: dict[str, Any]) -> dict[str, Any]:
    """Return a normalised copy of a canonical descriptor dictionary.

    Args:
        descriptor: A raw descriptor (possibly with mixed-case gate name, etc.).

    Returns:
        A new descriptor dictionary with all fields in canonical form.
    """
    return {
        "gate": str(descriptor.get("gate", "")).lower(),
        "targets": list(descriptor.get("targets", [])),
        "controls": list(descriptor.get("controls", [])),
        "params": dict(descriptor.get("params", {})),
    }
