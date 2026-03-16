"""
rqm_compiler.io.from_dict
~~~~~~~~~~~~~~~~~~~~~~~~~
Deserialize a :class:`~rqm_compiler.circuit.Circuit` from a plain dictionary.
"""

from __future__ import annotations

from typing import Any

from ..circuit import Circuit
from ..ops import Operation


def circuit_from_dict(data: dict[str, Any]) -> Circuit:
    """Reconstruct a :class:`~rqm_compiler.circuit.Circuit` from a serialized dictionary.

    The *data* dict must contain:

    * ``"num_qubits"`` (:class:`int`) — the number of qubits.
    * ``"operations"`` (:class:`list`) — a list of canonical descriptor dicts.

    Args:
        data: A dictionary previously produced by
              :func:`~rqm_compiler.io.to_dict.circuit_to_dict`.

    Returns:
        A reconstructed :class:`~rqm_compiler.circuit.Circuit`.

    Raises:
        KeyError: If required keys are missing from *data*.
        ValueError: If ``num_qubits`` is invalid.
    """
    num_qubits: int = int(data["num_qubits"])
    circuit = Circuit(num_qubits)
    for descriptor in data.get("operations", []):
        circuit.add(Operation.from_descriptor(descriptor))
    return circuit
