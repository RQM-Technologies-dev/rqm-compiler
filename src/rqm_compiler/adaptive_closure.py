"""Representation-owned closure accounting for the adaptive RQM compiler.

The metric in this module is deliberately scoped to the compiler's working
representation.  It is *not* the dimension of an arbitrary n-qubit quantum
state and must not be presented as such.

``minimum_closed_representation_size`` counts the coordinate capacity of the
least-general exact representation currently owned by the compiler for each
operation.  This makes C_R reproducible from representation semantics instead
of serialized-dictionary size.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .circuit import Circuit
from .ops import Operation


# Coordinate capacities of compiler-owned exact representations.  These are
# representation semantics, not Python object sizes.
REPRESENTATION_COORDINATES: dict[str, int] = {
    "identity": 0,
    "local_quaternion": 4,
    "bell": 2,
    "axis_hinge": 2,          # discrete axis label + continuous angle
    "cartan_relation": 3,     # (c1, c2, c3)
    "quaternion_cartan_block": 19,  # four SU(2) quaternions + 3 Cartan coords
    "u4_dense": 32,           # 16 complex entries; verification fallback only
    "opaque_operation": 1,
}

REPRESENTATION_LEVEL: dict[str, int] = {
    "identity": 0,
    "local_quaternion": 1,
    "bell": 2,
    "axis_hinge": 3,
    "cartan_relation": 4,
    "quaternion_cartan_block": 5,
    "u4_dense": 6,
    "opaque_operation": 7,
}


@dataclass(frozen=True)
class ClosureAccounting:
    """Exact accounting inside the compiler-owned representation hierarchy."""

    minimum_closed_representation_size: int
    maximum_representation_level: int
    representation_histogram: dict[str, int]
    representation_trajectory: tuple[str, ...]
    scope: str = "compiler_working_representation"
    exact_within_scope: bool = True
    quantum_state_dimension_claim: bool = False

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["representation_trajectory"] = list(self.representation_trajectory)
        return result


def minimal_representation(operation: Operation) -> str:
    """Return the least-general exact compiler representation for ``operation``.

    Classification is intentionally conservative.  We only claim a compact
    level when the current IR proves membership in that level.  Unknown or
    unsupported structures are marked opaque rather than guessed downward.
    """
    gate = operation.gate.lower()
    touched = len(set(operation.targets) | set(operation.controls))

    if gate in {"barrier", "measure"}:
        return "identity"
    if touched <= 1:
        # Named one-qubit gates and u1q are all exactly contained in SU(2)/U(2)
        # quaternion working form used by the compiler.  Global phase is not a
        # separately evolved state coordinate here.
        return "local_quaternion"
    if gate in {"rxx", "ryy", "rzz"}:
        return "axis_hinge"
    if gate == "su4q":
        block = operation.params.get("block") if isinstance(operation.params, dict) else None
        if isinstance(block, dict):
            cartan = block.get("cartan")
            # A materialized su4q is conservatively a full structured block;
            # future recognizers may prove Bell/Axis/Cartan demotions before it
            # reaches this point.
            if cartan is not None:
                return "quaternion_cartan_block"
        return "quaternion_cartan_block"
    if gate in {"cx", "cy", "cz", "swap", "iswap"}:
        # These fixed native 2Q gates are exact special points in U(4), but the
        # current adaptive hierarchy does not yet expose a proof object that
        # safely demotes every one to Bell/AxisHinge/CartanRelation.  Count them
        # as structured Cartan relations rather than inventing a Bell claim.
        return "cartan_relation"
    return "opaque_operation"


def account_closed_representation(circuit: Circuit) -> ClosureAccounting:
    """Measure C_R for the compiler's currently materialized working IR.

    This is representation-owned accounting: sizes come from the algebraic
    representation classes above, never from descriptor serialization or
    Python memory layout.
    """
    trajectory = tuple(minimal_representation(op) for op in circuit.operations)
    histogram: dict[str, int] = {}
    for name in trajectory:
        histogram[name] = histogram.get(name, 0) + 1
    size = sum(REPRESENTATION_COORDINATES[name] for name in trajectory)
    level = max((REPRESENTATION_LEVEL[name] for name in trajectory), default=0)
    return ClosureAccounting(
        minimum_closed_representation_size=size,
        maximum_representation_level=level,
        representation_histogram=histogram,
        representation_trajectory=trajectory,
    )
