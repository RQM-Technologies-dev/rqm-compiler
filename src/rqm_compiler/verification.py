"""Semantic equivalence verification for optimized circuits.

The verifier distinguishes between:

* VERIFIED      — semantic equivalence was checked and passed.
* UNVERIFIED    — optimization succeeded but equivalence was not established.
* COUNTEREXAMPLE— a concrete semantic mismatch was detected.
* UNSUPPORTED   — the verifier cannot analyze this circuit class yet.
* ERROR         — verifier infrastructure failed unexpectedly.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .circuit import Circuit
from .normalize import normalize_circuit
from .passes.canonicalize import canonicalize_pass
from .passes.flatten import flatten_pass
from .passes.merge_u1q import merge_u1q_pass
from .passes.sign_canon import sign_canon_pass
from .passes.to_u1q import to_u1q_pass


class EquivalenceStatus(str, Enum):
    """Semantic verification verdict."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class EquivalenceMethod(str, Enum):
    """Verification method identifier."""

    U1Q_CANONICAL = "U1Q_CANONICAL"
    UNITARY_NUMERICAL = "UNITARY_NUMERICAL"
    GATEWISE_IDENTITY = "GATEWISE_IDENTITY"
    NONE = "NONE"


@dataclass
class EquivalenceReport:
    """Structured semantic equivalence result."""

    status: EquivalenceStatus
    method: str = EquivalenceMethod.NONE.value
    verified: bool | None = None
    phase_invariant: bool = True
    atol: float = 1e-9
    rtol: float = 1e-7
    max_abs_err: float | None = None
    max_rel_err: float | None = None
    notes: list[str] = field(default_factory=list)
    unsupported_reasons: list[str] = field(default_factory=list)
    witness: dict[str, Any] | None = None
    compared_qubits: int | None = None
    compared_gate_count_original: int | None = None
    compared_gate_count_optimized: int | None = None


def verify_equivalence(
    original: Circuit,
    optimized: Circuit,
    *,
    atol: float = 1e-9,
    rtol: float = 1e-7,
    max_dense_qubits: int = 3,
) -> EquivalenceReport:
    """Verify whether *original* and *optimized* implement the same transformation."""

    base = EquivalenceReport(
        status=EquivalenceStatus.UNVERIFIED,
        method=EquivalenceMethod.NONE.value,
        verified=None,
        atol=atol,
        rtol=rtol,
        compared_qubits=original.num_qubits,
        compared_gate_count_original=len(original),
        compared_gate_count_optimized=len(optimized),
    )

    try:
        if original.num_qubits != optimized.num_qubits:
            base.status = EquivalenceStatus.COUNTEREXAMPLE
            base.method = EquivalenceMethod.GATEWISE_IDENTITY.value
            base.verified = False
            base.notes.append("Circuit qubit counts differ.")
            base.witness = {
                "original_num_qubits": original.num_qubits,
                "optimized_num_qubits": optimized.num_qubits,
            }
            return base

        if (
            original.to_descriptors() == optimized.to_descriptors()
            and _is_gatewise_identity_supported(original)
        ):
            base.status = EquivalenceStatus.VERIFIED
            base.method = EquivalenceMethod.GATEWISE_IDENTITY.value
            base.verified = True
            base.notes.append("Descriptor-identical circuits are semantically equivalent.")
            return base

        # Stage A: exact 1-qubit canonical-u1q check.
        stage_a = _verify_single_qubit_u1q_canonical(original, optimized, atol=atol, rtol=rtol)
        if stage_a is not None:
            return stage_a

        # Stage B: numerical unitary verification for small supported circuits.
        return _verify_dense_unitary(
            original,
            optimized,
            atol=atol,
            rtol=rtol,
            max_dense_qubits=max_dense_qubits,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        base.status = EquivalenceStatus.ERROR
        base.method = EquivalenceMethod.NONE.value
        base.verified = None
        base.notes.append(f"Verifier error: {exc!r}")
        return base


def _verify_single_qubit_u1q_canonical(
    original: Circuit,
    optimized: Circuit,
    *,
    atol: float,
    rtol: float,
) -> EquivalenceReport | None:
    if original.num_qubits != 1 or optimized.num_qubits != 1:
        return None

    if not (_is_unitary_supported(original) and _is_unitary_supported(optimized)):
        return None

    left = _canonical_u1q_single_qubit(original)
    right = _canonical_u1q_single_qubit(optimized)

    if left == right:
        report = EquivalenceReport(
            status=EquivalenceStatus.VERIFIED,
            method=EquivalenceMethod.U1Q_CANONICAL.value,
            verified=True,
            atol=atol,
            rtol=rtol,
            compared_qubits=1,
            compared_gate_count_original=len(original),
            compared_gate_count_optimized=len(optimized),
        )
        report.notes.append("Single-qubit canonical u1q representatives match exactly.")
        return report

    return None


def _canonical_u1q_single_qubit(circuit: Circuit) -> list[dict[str, Any]]:
    working = normalize_circuit(circuit)
    working = canonicalize_pass(working)
    working = flatten_pass(working)
    working = to_u1q_pass(working)
    working = merge_u1q_pass(working)
    working = sign_canon_pass(working)
    return working.to_descriptors()


def _verify_dense_unitary(
    original: Circuit,
    optimized: Circuit,
    *,
    atol: float,
    rtol: float,
    max_dense_qubits: int,
) -> EquivalenceReport:
    report = EquivalenceReport(
        status=EquivalenceStatus.UNVERIFIED,
        method=EquivalenceMethod.UNITARY_NUMERICAL.value,
        verified=None,
        atol=atol,
        rtol=rtol,
        compared_qubits=original.num_qubits,
        compared_gate_count_original=len(original),
        compared_gate_count_optimized=len(optimized),
    )

    if not _is_unitary_supported(original) or not _is_unitary_supported(optimized):
        report.status = EquivalenceStatus.UNSUPPORTED
        report.method = EquivalenceMethod.NONE.value
        report.unsupported_reasons.extend(
            _unsupported_reasons(original) + _unsupported_reasons(optimized)
        )
        report.unsupported_reasons = sorted(set(report.unsupported_reasons))
        return report

    if original.num_qubits > max_dense_qubits:
        report.status = EquivalenceStatus.UNVERIFIED
        report.notes.append(
            f"Dense unitary verification limited to <= {max_dense_qubits} qubits."
        )
        return report

    u = _circuit_unitary(original)
    v = _circuit_unitary(optimized)
    phase, max_abs_err, max_rel_err, pivot, notes = compare_unitaries_up_to_global_phase(
        u,
        v,
        atol=atol,
        rtol=rtol,
    )
    report.notes.extend(notes)
    report.max_abs_err = max_abs_err
    report.max_rel_err = max_rel_err

    if max_abs_err <= atol + rtol * max(1.0, _matrix_max_abs(v)):
        report.status = EquivalenceStatus.VERIFIED
        report.verified = True
        report.notes.append("Numerical unitary comparison passed up to global phase.")
        return report

    report.status = EquivalenceStatus.COUNTEREXAMPLE
    report.verified = False
    i, j = pivot
    report.witness = {
        "pivot": {"row": i, "col": j},
        "phase": {"real": phase.real, "imag": phase.imag},
        "u_ij": {"real": u[i][j].real, "imag": u[i][j].imag},
        "phase_v_ij": {"real": (phase * v[i][j]).real, "imag": (phase * v[i][j]).imag},
        "abs_err": abs(u[i][j] - phase * v[i][j]),
    }
    return report


def compare_unitaries_up_to_global_phase(
    u: list[list[complex]],
    v: list[list[complex]],
    *,
    atol: float,
    rtol: float,
) -> tuple[complex, float, float, tuple[int, int], list[str]]:
    """Return best-fit phase and error metrics for ``u ≈ e^{iφ} v``."""

    notes: list[str] = []
    n = len(u)
    if n == 0 or len(v) != n or any(len(row) != n for row in u + v):
        raise ValueError("Unitary matrices must be square and of equal shape.")

    pivot = (0, 0)
    best_mag = 0.0
    for i in range(n):
        for j in range(n):
            score = abs(u[i][j]) * abs(v[i][j])
            if score > best_mag:
                best_mag = score
                pivot = (i, j)

    i, j = pivot
    denom = v[i][j]
    num = u[i][j]

    if abs(num) <= atol or abs(denom) <= atol:
        # Fallback to inner-product phase estimator.
        numer = 0j
        for r in range(n):
            for c in range(n):
                numer += u[r][c] * v[r][c].conjugate()
        if abs(numer) <= atol:
            phase = 1.0 + 0.0j
            notes.append("Weak phase conditioning: overlap nearly zero; defaulting phase to 1.")
        else:
            phase = numer / abs(numer)
            notes.append("Phase derived from matrix inner product due weak pivot.")
    else:
        ratio = num / denom
        phase = ratio / abs(ratio)

    max_abs_err = 0.0
    max_rel_err = 0.0
    max_idx = (0, 0)
    for r in range(n):
        for c in range(n):
            ref = phase * v[r][c]
            err = abs(u[r][c] - ref)
            if err > max_abs_err:
                max_abs_err = err
                max_idx = (r, c)
            denom_rel = max(abs(u[r][c]), abs(ref), atol)
            max_rel_err = max(max_rel_err, err / denom_rel)

    tol_bound = atol + rtol * max(1.0, _matrix_max_abs(v))
    if max_abs_err > tol_bound:
        pivot = max_idx

    return phase, max_abs_err, max_rel_err, pivot, notes


def _matrix_max_abs(m: list[list[complex]]) -> float:
    return max(abs(x) for row in m for x in row)


def _circuit_unitary(circuit: Circuit) -> list[list[complex]]:
    n = circuit.num_qubits
    dim = 1 << n
    out: list[list[complex]] = [[0j for _ in range(dim)] for _ in range(dim)]

    for col in range(dim):
        state = [0j] * dim
        state[col] = 1.0 + 0.0j
        for op in circuit.operations:
            state = _apply_gate_to_state(state, op, n)
        for row in range(dim):
            out[row][col] = state[row]

    return out


def _apply_gate_to_state(state: list[complex], op: Any, num_qubits: int) -> list[complex]:
    gate = op.gate

    if gate in {"measure", "barrier"}:
        raise ValueError(f"Non-unitary gate {gate!r} in unitary simulation path.")

    if gate in {"x", "y", "z", "h", "s", "sdg", "t", "tdg", "i", "id", "rx", "ry", "rz", "p", "phase", "phaseshift", "u", "u3", "u1q"}:
        target = op.targets[0]
        m = _single_qubit_matrix(op)
        return _apply_single_qubit(state, target, m, num_qubits)

    if gate in {"cx", "cy", "cz"}:
        control = op.controls[0]
        target = op.targets[0]
        base = {
            "cx": [[0, 1], [1, 0]],
            "cy": [[0, -1j], [1j, 0]],
            "cz": [[1, 0], [0, -1]],
        }[gate]
        return _apply_controlled_single_qubit(state, control, target, base, num_qubits)

    if gate == "swap":
        a, b = op.targets
        return _apply_swap(state, a, b, num_qubits)

    raise ValueError(f"Unsupported gate in unitary simulation: {gate!r}")


def _single_qubit_matrix(op: Any) -> list[list[complex]]:
    g = op.gate
    p = op.params

    if g in {"i", "id"}:
        return [[1, 0], [0, 1]]
    if g == "x":
        return [[0, 1], [1, 0]]
    if g == "y":
        return [[0, -1j], [1j, 0]]
    if g == "z":
        return [[1, 0], [0, -1]]
    if g == "h":
        s = 1 / math.sqrt(2)
        return [[s, s], [s, -s]]
    if g == "s":
        return [[1, 0], [0, 1j]]
    if g == "sdg":
        return [[1, 0], [0, -1j]]
    if g == "t":
        return [[1, 0], [0, cmath.exp(1j * math.pi / 4)]]
    if g == "tdg":
        return [[1, 0], [0, cmath.exp(-1j * math.pi / 4)]]
    if g == "rx":
        a = _require_real_param(p, "angle")
        c, s = math.cos(a / 2), math.sin(a / 2)
        return [[c, -1j * s], [-1j * s, c]]
    if g == "ry":
        a = _require_real_param(p, "angle")
        c, s = math.cos(a / 2), math.sin(a / 2)
        return [[c, -s], [s, c]]
    if g == "rz":
        a = _require_real_param(p, "angle")
        return [[cmath.exp(-1j * a / 2), 0], [0, cmath.exp(1j * a / 2)]]
    if g in {"p", "phase", "phaseshift"}:
        a = _require_real_param(p, "angle")
        return [[1, 0], [0, cmath.exp(1j * a)]]
    if g in {"u", "u3"}:
        theta = _require_real_param(p, "theta")
        phi = _require_real_param(p, "phi")
        lam = _require_real_param(p, "lambda")
        return [
            [math.cos(theta / 2), -cmath.exp(1j * lam) * math.sin(theta / 2)],
            [cmath.exp(1j * phi) * math.sin(theta / 2), cmath.exp(1j * (phi + lam)) * math.cos(theta / 2)],
        ]
    if g == "u1q":
        w = _require_real_param(p, "w")
        x = _require_real_param(p, "x")
        y = _require_real_param(p, "y")
        z = _require_real_param(p, "z")
        return [
            [complex(w, -z), complex(-y, -x)],
            [complex(y, -x), complex(w, z)],
        ]

    raise ValueError(f"Unsupported single-qubit gate {g!r}")


def _apply_single_qubit(
    state: list[complex],
    qubit: int,
    m: list[list[complex]],
    num_qubits: int,
) -> list[complex]:
    out = list(state)
    stride = 1 << qubit
    span = stride << 1
    dim = 1 << num_qubits
    for base in range(0, dim, span):
        for offset in range(stride):
            i0 = base + offset
            i1 = i0 + stride
            a0, a1 = state[i0], state[i1]
            out[i0] = m[0][0] * a0 + m[0][1] * a1
            out[i1] = m[1][0] * a0 + m[1][1] * a1
    return out


def _apply_controlled_single_qubit(
    state: list[complex],
    control: int,
    target: int,
    m: list[list[complex]],
    num_qubits: int,
) -> list[complex]:
    out = list(state)
    stride = 1 << target
    span = stride << 1
    dim = 1 << num_qubits
    control_mask = 1 << control

    for base in range(0, dim, span):
        for offset in range(stride):
            i0 = base + offset
            i1 = i0 + stride
            if (i0 & control_mask) == 0:
                continue
            a0, a1 = state[i0], state[i1]
            out[i0] = m[0][0] * a0 + m[0][1] * a1
            out[i1] = m[1][0] * a0 + m[1][1] * a1
    return out


def _apply_swap(state: list[complex], a: int, b: int, num_qubits: int) -> list[complex]:
    if a == b:
        return list(state)
    out = list(state)
    dim = 1 << num_qubits
    ma, mb = 1 << a, 1 << b
    for i in range(dim):
        abit = 1 if i & ma else 0
        bbit = 1 if i & mb else 0
        if abit == bbit:
            continue
        j = i ^ ma ^ mb
        if i < j:
            out[i], out[j] = state[j], state[i]
    return out


def _require_real_param(params: dict[str, Any], name: str) -> float:
    if name not in params:
        raise ValueError(f"Missing parameter {name!r}")
    val = params[name]
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"Parameter {name!r} must be a real number, got {val!r}")
    return float(val)


def _is_unitary_supported(circuit: Circuit) -> bool:
    return not _unsupported_reasons(circuit)


def _unsupported_reasons(circuit: Circuit) -> list[str]:
    reasons: list[str] = []
    supported = {
        "id", "i", "x", "y", "z", "h", "s", "sdg", "t", "tdg",
        "rx", "ry", "rz", "p", "phase", "phaseshift", "u", "u3", "u1q",
        "cx", "cy", "cz", "swap",
    }
    for idx, op in enumerate(circuit.operations):
        if op.gate in {"measure", "barrier"}:
            reasons.append(f"Operation[{idx}] gate {op.gate!r} is non-unitary.")
            continue
        if op.gate not in supported:
            reasons.append(f"Operation[{idx}] gate {op.gate!r} is not supported by verifier.")
            continue
        try:
            if op.gate in {"rx", "ry", "rz", "p", "phase", "phaseshift"}:
                _require_real_param(op.params, "angle")
            elif op.gate in {"u", "u3"}:
                _require_real_param(op.params, "theta")
                _require_real_param(op.params, "phi")
                _require_real_param(op.params, "lambda")
            elif op.gate == "u1q":
                _require_real_param(op.params, "w")
                _require_real_param(op.params, "x")
                _require_real_param(op.params, "y")
                _require_real_param(op.params, "z")
        except ValueError as exc:
            reasons.append(f"Operation[{idx}] unresolved/symbolic params: {exc}")
    return reasons


def _is_gatewise_identity_supported(circuit: Circuit) -> bool:
    """Return True when exact descriptor identity is accepted as a verifier result."""
    for op in circuit.operations:
        for value in op.params.values():
            if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                return False
            if isinstance(value, str):
                # Symbolic parameter strings should stay UNVERIFIED until evaluator support exists.
                return False
    return True
