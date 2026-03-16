"""
rqm_compiler.descriptors
~~~~~~~~~~~~~~~~~~~~~~~~
Canonical gate name registry and descriptor utilities.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Supported gate names (v0 canonical set)
# ---------------------------------------------------------------------------

#: Single-qubit gates that take no parameters.
SINGLE_QUBIT_GATES: frozenset[str] = frozenset(
    {"i", "x", "y", "z", "h", "s", "t"}
)

#: Single-qubit parameterised gates.  Each maps to the parameter name it expects.
PARAMETRIC_SINGLE_QUBIT_GATES: dict[str, tuple[str, ...]] = {
    "rx": ("angle",),
    "ry": ("angle",),
    "rz": ("angle",),
    "phaseshift": ("angle",),
}

#: Two-qubit gates that take no parameters.
TWO_QUBIT_GATES: frozenset[str] = frozenset({"cx", "cy", "cz", "swap", "iswap"})

#: Measurement and barrier gates.
OTHER_GATES: frozenset[str] = frozenset({"measure", "barrier"})

#: The complete set of gate names recognised by the compiler.
SUPPORTED_GATES: frozenset[str] = (
    SINGLE_QUBIT_GATES
    | frozenset(PARAMETRIC_SINGLE_QUBIT_GATES)
    | TWO_QUBIT_GATES
    | OTHER_GATES
)


def make_descriptor(
    gate: str,
    targets: list[int],
    *,
    controls: list[int] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical gate descriptor dictionary.

    Args:
        gate: Gate name (case-insensitive; stored lowercase).
        targets: Target qubit indices.
        controls: Control qubit indices (default: empty list).
        params: Gate parameters (default: empty dict).

    Returns:
        A canonical descriptor conforming to the rqm-compiler IR schema.
    """
    return {
        "gate": gate.lower(),
        "targets": list(targets),
        "controls": list(controls) if controls is not None else [],
        "params": dict(params) if params is not None else {},
    }


def is_supported_gate(name: str) -> bool:
    """Return ``True`` if *name* is a recognised canonical gate."""
    return name.lower() in SUPPORTED_GATES
