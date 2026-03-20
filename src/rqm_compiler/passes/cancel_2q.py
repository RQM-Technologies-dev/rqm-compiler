"""
rqm_compiler.passes.cancel_2q
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pass that cancels adjacent self-inverse two-qubit gates on the same qubit pair.

Several common two-qubit gates are *involutory* (self-inverse):

* ``cx``   — CNOT:     CX² = I
* ``cy``   — CY:       CY² = I
* ``cz``   — CZ:       CZ² = I
* ``swap`` — SWAP:     SWAP² = I

When two identical self-inverse gates appear consecutively on exactly the same
qubit pair, with no intervening gate touching either qubit, the pair can be
removed entirely — their combined action is the identity.

This is the two-qubit analogue of the single-qubit ``merge_u1q_pass`` identity
check: pure algebraic cleanup that reduces gate count and circuit depth without
any approximation.

Excluded gate
~~~~~~~~~~~~~
``iswap`` is *not* self-inverse (ISWAP² = Z⊗Z ≠ I), so it is never cancelled
by this pass.

Algorithm
~~~~~~~~~
The pass makes a single left-to-right sweep.  For each operation it maintains a
*pending* slot per qubit-pair.  A slot is a self-inverse gate that has been
emitted but can still be cancelled if the very next gate on both those qubits is
the same gate.  Any gate that touches either qubit of a pending slot *without*
cancelling it immediately invalidates the slot (the two gates are no longer
adjacent from the perspective of those qubits).

The emitted gate is recorded at its position in the output list as a tombstone
(``None``) if later cancelled, and the final circuit is built by filtering out
all tombstones.

Key correctness properties
~~~~~~~~~~~~~~~~~~~~~~~~~~
* Non-self-inverse gates (``iswap``, single-qubit gates, measurements, …) pass
  through untouched.
* Two-qubit self-inverse gates that do *not* form an adjacent identical pair
  also pass through untouched.
* The gate signature used for matching is the exact IR representation:
  ``(gate, tuple(targets), tuple(controls))``.  This means ``cx(0, 1)`` and
  ``cx(1, 0)`` are treated as distinct operations and are not cancelled against
  each other, even though both are self-inverse individually.
* The pass is idempotent: applying it twice yields the same result as applying
  it once.
* The pass does not mutate the input circuit.
"""

from __future__ import annotations

from ..circuit import Circuit
from ..ops import Operation

#: Gates that satisfy G² = I (self-inverse / involutory).
SELF_INVERSE_TWO_QUBIT_GATES: frozenset[str] = frozenset({"cx", "cy", "cz", "swap"})


def _gate_signature(op: Operation) -> tuple[str, tuple[int, ...], tuple[int, ...]]:
    """Return a hashable tuple that uniquely identifies the gate and its qubit assignment."""
    return (op.gate, tuple(op.targets), tuple(op.controls))


def cancel_2q_pass(circuit: Circuit) -> Circuit:
    """Return a new circuit with adjacent self-inverse two-qubit gate pairs cancelled.

    Consecutive identical self-inverse two-qubit gates on the same qubit pair
    (``cx``, ``cy``, ``cz``, ``swap``) with no intervening operation on either
    qubit are removed entirely.  All other gates are emitted unchanged.

    Args:
        circuit: Source circuit (not mutated).

    Returns:
        A new :class:`~rqm_compiler.circuit.Circuit` with cancelled gate pairs
        removed.

    Example::

        from rqm_compiler import Circuit
        from rqm_compiler.passes import cancel_2q_pass

        c = Circuit(2)
        c.cx(0, 1)
        c.cx(0, 1)   # cancels with the first

        result = cancel_2q_pass(c)
        assert len(result) == 0

    Example — intervening gate prevents cancellation::

        c = Circuit(2)
        c.cx(0, 1)
        c.h(0)       # touches qubit 0 → breaks adjacency
        c.cx(0, 1)

        result = cancel_2q_pass(c)
        assert len(result) == 3   # none cancelled
    """
    # output_ops[i] is an Operation, or None (tombstone = cancelled).
    output_ops: list[Operation | None] = []

    # pending_by_pair: frozenset({q1, q2}) -> index in output_ops of the pending
    # self-inverse gate, or None when no gate is currently pending on that pair.
    pending_by_pair: dict[frozenset[int], int | None] = {}

    for op in circuit.operations:
        qubits: frozenset[int] = frozenset(list(op.targets) + list(op.controls))

        if op.gate in SELF_INVERSE_TWO_QUBIT_GATES and len(qubits) == 2:
            key = qubits
            pending_idx = pending_by_pair.get(key)

            if pending_idx is not None:
                pending_op = output_ops[pending_idx]
                if (
                    pending_op is not None
                    and _gate_signature(pending_op) == _gate_signature(op)
                ):
                    # Cancel both gates: tombstone the pending one, skip the current.
                    output_ops[pending_idx] = None
                    pending_by_pair[key] = None
                    # No other overlapping pending pairs can exist here: any pending
                    # pair that shared a qubit with this pair was invalidated when
                    # the first occurrence of this gate was processed.
                    continue

            # Not cancelled.  Invalidate all other pending pairs that share a
            # qubit with this gate (they are no longer adjacent to their match).
            for k in list(pending_by_pair):
                if k is not key and k & qubits:
                    pending_by_pair[k] = None

            # Record this gate as pending and emit it.
            pending_by_pair[key] = len(output_ops)
            output_ops.append(op)

        else:
            # Non-self-inverse gate.  Invalidate all pending pairs that share a
            # qubit with this gate.
            for k in list(pending_by_pair):
                if k & qubits:
                    pending_by_pair[k] = None
            output_ops.append(op)

    out = Circuit(circuit.num_qubits)
    for op in output_ops:
        if op is not None:
            out.add(op)
    return out
