"""
rqm_compiler.io.to_dict
~~~~~~~~~~~~~~~~~~~~~~~
Serialize a :class:`~rqm_compiler.circuit.Circuit` to a plain dictionary.
"""

from __future__ import annotations

from typing import Any

from ..circuit import Circuit


def circuit_to_dict(circuit: Circuit) -> dict[str, Any]:
    """Serialize *circuit* to a JSON-compatible dictionary.

    The returned structure has the form::

        {
            "num_qubits": 2,
            "operations": [
                {"gate": "h", "targets": [0], "controls": [], "params": {}},
                ...
            ]
        }

    Args:
        circuit: The circuit to serialize.

    Returns:
        A plain :class:`dict` suitable for JSON serialization.
    """
    return {
        "num_qubits": circuit.num_qubits,
        "operations": circuit.to_descriptors(),
    }
