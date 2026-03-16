"""
rqm_compiler.ops
~~~~~~~~~~~~~~~~
Core operation data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Operation:
    """A single quantum gate or measurement operation.

    Attributes:
        gate: Lowercase gate name (e.g. ``"h"``, ``"cx"``, ``"measure"``).
        targets: Qubit indices the gate acts on.
        controls: Qubit indices that are control qubits.
        params: Gate-specific parameters (e.g. ``{"angle": 1.5707963267948966}``).
    """

    gate: str
    targets: list[int] = field(default_factory=list)
    controls: list[int] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.gate = self.gate.lower()
        self.targets = list(self.targets)
        self.controls = list(self.controls)
        self.params = dict(self.params)

    def to_descriptor(self) -> dict[str, Any]:
        """Return the canonical descriptor dictionary for this operation."""
        return {
            "gate": self.gate,
            "targets": list(self.targets),
            "controls": list(self.controls),
            "params": dict(self.params),
        }

    @classmethod
    def from_descriptor(cls, descriptor: dict[str, Any]) -> "Operation":
        """Create an :class:`Operation` from a canonical descriptor dictionary."""
        return cls(
            gate=descriptor["gate"],
            targets=list(descriptor.get("targets", [])),
            controls=list(descriptor.get("controls", [])),
            params=dict(descriptor.get("params", {})),
        )
