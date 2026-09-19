"""Exact Pauli-observable evaluation without materializing a 2**n statevector.

The evaluator propagates a Pauli expansion backwards through the compiled
circuit (Heisenberg picture) and then evaluates it on |0...0>.  Cost is driven
by Pauli-term growth rather than Hilbert-space dimension.  This is exact up to
floating-point roundoff and supports the compiler's 1Q/2Q unitary gate set,
including su4q blocks.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable

import numpy as np

from .circuit import Circuit
from .su4_blocks import _operation_matrix, _single_qubit_matrix

_PAULI = {
    "I": np.asarray([[1, 0], [0, 1]], dtype=np.complex128),
    "X": np.asarray([[0, 1], [1, 0]], dtype=np.complex128),
    "Y": np.asarray([[0, -1j], [1j, 0]], dtype=np.complex128),
    "Z": np.asarray([[1, 0], [0, -1]], dtype=np.complex128),
}
_LABELS = ("I", "X", "Y", "Z")


class ObservableExpansionExceeded(RuntimeError):
    """Raised when exact Pauli expansion exceeds a caller-supplied work cap.

    The cap is checked after a gate expansion; peak_terms records the observed
    overshoot, not a claim that the allocation was bounded by max_terms.
    """

    def __init__(self, message: str, *, peak_terms: int | None = None,
                 operations_processed: int | None = None):
        super().__init__(message)
        self.peak_terms = peak_terms
        self.operations_processed = operations_processed


@dataclass(frozen=True)
class ObservableResult:
    value: complex
    final_terms: int
    peak_terms: int
    operations_processed: int


def _decompose_1q(matrix: np.ndarray, *, cutoff: float) -> list[tuple[str, complex]]:
    out: list[tuple[str, complex]] = []
    for label in _LABELS:
        coeff = np.trace(_PAULI[label] @ matrix) / 2.0
        if abs(coeff) > cutoff:
            out.append((label, complex(coeff)))
    return out


def _basis_2q(a: str, b: str) -> np.ndarray:
    # Pair convention matches su4_blocks: pair[0] is the least-significant
    # qubit and therefore the right Kronecker factor.
    return np.kron(_PAULI[b], _PAULI[a])


def _decompose_2q(matrix: np.ndarray, *, cutoff: float) -> list[tuple[tuple[str, str], complex]]:
    out: list[tuple[tuple[str, str], complex]] = []
    for a, b in product(_LABELS, repeat=2):
        basis = _basis_2q(a, b)
        coeff = np.trace(basis @ matrix) / 4.0
        if abs(coeff) > cutoff:
            out.append(((a, b), complex(coeff)))
    return out


def expectation_pauli(
    circuit: Circuit,
    pauli: str | Iterable[str],
    *,
    cutoff: float = 1e-13,
    max_terms: int = 250_000,
) -> ObservableResult:
    """Return ``<0|U† P U|0>`` without constructing ``|psi>``.

    ``pauli`` is indexed by compiler qubit number: character 0 applies to q0.
    Supported symbols are I/X/Y/Z.
    """
    labels = tuple(pauli) if not isinstance(pauli, str) else tuple(pauli)
    if len(labels) != circuit.num_qubits:
        raise ValueError("Pauli string length must equal circuit.num_qubits")
    if any(label not in _LABELS for label in labels):
        raise ValueError("Pauli string may contain only I, X, Y, Z")

    terms: dict[tuple[str, ...], complex] = {labels: 1.0 + 0.0j}
    peak = 1
    processed = 0

    for op in reversed(circuit.operations):
        if op.gate in {"barrier"}:
            continue
        if op.gate == "measure":
            raise ValueError("Observable evaluator requires a unitary circuit")
        touched = sorted(set(op.targets) | set(op.controls))
        if not touched or len(touched) > 2:
            raise ValueError(f"unsupported operation locality for {op.gate!r}")

        updated: dict[tuple[str, ...], complex] = {}
        if len(touched) == 1:
            q = touched[0]
            u = _single_qubit_matrix(op)
            cache: dict[str, list[tuple[str, complex]]] = {}
            for key, coeff in terms.items():
                local = key[q]
                expansion = cache.get(local)
                if expansion is None:
                    transformed = u.conj().T @ _PAULI[local] @ u
                    expansion = _decompose_1q(transformed, cutoff=cutoff)
                    cache[local] = expansion
                for replacement, factor in expansion:
                    new_key = list(key); new_key[q] = replacement; nk = tuple(new_key)
                    updated[nk] = updated.get(nk, 0j) + coeff * factor
        else:
            pair = (touched[0], touched[1])
            u = _operation_matrix(op, pair)
            cache2: dict[tuple[str, str], list[tuple[tuple[str, str], complex]]] = {}
            for key, coeff in terms.items():
                local = (key[pair[0]], key[pair[1]])
                expansion = cache2.get(local)
                if expansion is None:
                    transformed = u.conj().T @ _basis_2q(*local) @ u
                    expansion = _decompose_2q(transformed, cutoff=cutoff)
                    cache2[local] = expansion
                for replacement, factor in expansion:
                    new_key = list(key)
                    new_key[pair[0]], new_key[pair[1]] = replacement
                    nk = tuple(new_key)
                    updated[nk] = updated.get(nk, 0j) + coeff * factor

        terms = {k: v for k, v in updated.items() if abs(v) > cutoff}
        processed += 1
        peak = max(peak, len(terms))
        if len(terms) > max_terms:
            raise ObservableExpansionExceeded(
                f"Pauli expansion exceeded max_terms={max_terms} after {processed} operations",
                peak_terms=peak, operations_processed=processed
            )

    value = sum(
        coeff for key, coeff in terms.items() if all(label in {"I", "Z"} for label in key)
    )
    return ObservableResult(complex(value), len(terms), peak, processed)
