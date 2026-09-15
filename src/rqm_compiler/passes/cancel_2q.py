"""Exact two-qubit cleanup and relational compression.

Besides cancelling adjacent involutions, this pass keeps canonical XX/YY/ZZ
interactions in the smallest closed representation: a contiguous run on one
qubit pair is accumulated as rqm-entanglement AxisHinge/CartanRelation data and
emitted as at most one RXX, RYY and RZZ operation.  Because XX, YY and ZZ
commute, this is exact and avoids dense SU(4)/KAK work.
"""

from __future__ import annotations

import math

from rqm_entanglement import AxisHinge, CartanRelation, compose_relations

from ..circuit import Circuit
from ..ops import Operation

SELF_INVERSE_TWO_QUBIT_GATES: frozenset[str] = frozenset({"cx", "cy", "cz", "swap"})
_PAIR_ROTATIONS = frozenset({"rxx", "ryy", "rzz"})
_AXIS = {"rxx": "xx", "ryy": "yy", "rzz": "zz"}
_GATE = {"xx": "rxx", "yy": "ryy", "zz": "rzz"}
_TOL = 1e-12


def _gate_signature(op: Operation) -> tuple[str, tuple[int, ...], tuple[int, ...]]:
    return (op.gate, tuple(op.targets), tuple(op.controls))


def _finite_angle(op: Operation) -> float | None:
    value = op.params.get("angle")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    angle = float(value)
    return angle if math.isfinite(angle) else None


def _flush_relational_run(
    output: list[Operation], pair: tuple[int, int] | None, relation: AxisHinge | CartanRelation | None
) -> None:
    if pair is None or relation is None:
        return
    cartan = relation.promote() if isinstance(relation, AxisHinge) else relation
    for axis, angle in (("xx", cartan.c1), ("yy", cartan.c2), ("zz", cartan.c3)):
        if abs(angle) > _TOL:
            output.append(Operation(gate=_GATE[axis], targets=list(pair), params={"angle": angle}))


def _compress_relational_runs(operations: list[Operation]) -> list[Operation]:
    output: list[Operation] = []
    pair: tuple[int, int] | None = None
    relation: AxisHinge | CartanRelation | None = None

    for op in operations:
        qubits = tuple(sorted(set(op.targets) | set(op.controls)))
        angle = _finite_angle(op) if op.gate in _PAIR_ROTATIONS else None
        if op.gate in _PAIR_ROTATIONS and len(qubits) == 2 and angle is not None:
            current = AxisHinge(_AXIS[op.gate], angle)
            if pair == qubits and relation is not None:
                relation = compose_relations(relation, current)
            else:
                _flush_relational_run(output, pair, relation)
                pair = qubits
                relation = current
            continue
        _flush_relational_run(output, pair, relation)
        pair = None
        relation = None
        output.append(op)

    _flush_relational_run(output, pair, relation)
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
