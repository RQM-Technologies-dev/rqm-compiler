"""Exact two-qubit cleanup and relational compression.

Canonical XX/YY/ZZ runs are kept in the smallest closed representation.  When
the adaptive relational API is installed, rqm-entanglement owns composition;
a coordinate-addition compatibility path preserves identical semantics for the
currently published 0.2.x package until the next package release lands.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from ..circuit import Circuit
from ..ops import Operation

SELF_INVERSE_TWO_QUBIT_GATES: frozenset[str] = frozenset({"cx", "cy", "cz", "swap"})
_PAIR_ROTATIONS = frozenset({"rxx", "ryy", "rzz"})
_AXIS_INDEX = {"rxx": 0, "ryy": 1, "rzz": 2}
_GATE = ("rxx", "ryy", "rzz")
_TOL = 1e-12


def _gate_signature(op: Operation) -> tuple[str, tuple[int, ...], tuple[int, ...]]:
    return (op.gate, tuple(op.targets), tuple(op.controls))


def _finite_angle(op: Operation) -> float | None:
    value = op.params.get("angle")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    angle = float(value)
    return angle if math.isfinite(angle) else None


@lru_cache(maxsize=1)
def _relational_api() -> tuple[Any, Any, Any] | None:
    """Resolve optional symbols once, including absence in older installations.

    Resolution is lazy to avoid import cycles. Dependency upgrades take effect
    in a new process; failed compositions do not change the cached capability.
    """
    try:
        from rqm_entanglement import AxisHinge, CartanRelation, compose_relations
    except (ImportError, AttributeError):
        return None
    return AxisHinge, CartanRelation, compose_relations


def _compose_coordinates(coords: tuple[float, float, float], gate: str, angle: float) -> tuple[float, float, float]:
    """Compose through rqm-entanglement when its relational API is available."""
    api = _relational_api()
    if api is not None:
        AxisHinge, CartanRelation, compose_relations = api
        try:
            relation: Any = CartanRelation(*coords)
            merged = compose_relations(relation, AxisHinge(gate[1:], angle))
            cartan = merged.promote() if isinstance(merged, AxisHinge) else merged
            if isinstance(cartan, CartanRelation):
                return cartan.c1, cartan.c2, cartan.c3
        except (ImportError, AttributeError):
            pass
    values = list(coords)
    values[_AXIS_INDEX[gate]] += angle
    return values[0], values[1], values[2]


def _flush(output: list[Operation], pair: tuple[int, int] | None, coords: tuple[float, float, float]) -> None:
    if pair is None:
        return
    for gate, angle in zip(_GATE, coords, strict=True):
        if abs(angle) > _TOL:
            output.append(Operation(gate=gate, targets=list(pair), params={"angle": angle}))


def _compress_relational_runs(operations: list[Operation]) -> list[Operation]:
    output: list[Operation] = []
    pair: tuple[int, int] | None = None
    coords = (0.0, 0.0, 0.0)
    for op in operations:
        qubits = tuple(sorted(set(op.targets) | set(op.controls)))
        angle = _finite_angle(op) if op.gate in _PAIR_ROTATIONS else None
        if op.gate in _PAIR_ROTATIONS and len(qubits) == 2 and angle is not None:
            if pair != qubits:
                _flush(output, pair, coords)
                pair, coords = qubits, (0.0, 0.0, 0.0)
            coords = _compose_coordinates(coords, op.gate, angle)
            continue
        _flush(output, pair, coords)
        pair, coords = None, (0.0, 0.0, 0.0)
        output.append(op)
    _flush(output, pair, coords)
    return output


def cancel_2q_pass(circuit: Circuit) -> Circuit:
    """Cancel exact involutions and compress closed XX/YY/ZZ relational runs."""
    output_ops: list[Operation | None] = []
    pending_by_pair: dict[frozenset[int], int | None] = {}
    for op in circuit.operations:
        qubits = frozenset(list(op.targets) + list(op.controls))
        if op.gate in SELF_INVERSE_TWO_QUBIT_GATES and len(qubits) == 2:
            key = qubits
            pending_idx = pending_by_pair.get(key)
            if pending_idx is not None:
                pending_op = output_ops[pending_idx]
                if pending_op is not None and _gate_signature(pending_op) == _gate_signature(op):
                    output_ops[pending_idx] = None
                    pending_by_pair[key] = None
                    continue
            for other in list(pending_by_pair):
                if other != key and other & qubits:
                    pending_by_pair[other] = None
            pending_by_pair[key] = len(output_ops)
            output_ops.append(op)
        else:
            for other in list(pending_by_pair):
                if other & qubits:
                    pending_by_pair[other] = None
            output_ops.append(op)

    compact = _compress_relational_runs([op for op in output_ops if op is not None])
    out = Circuit(circuit.num_qubits, metadata=dict(circuit.metadata))
    for op in compact:
        out.add(op)
    return out
