"""Opt-in proof-gated extraction of internal quaternion-Cartan blocks."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray
from rqm_entanglement import (
    I2,
    X,
    XX,
    Y,
    YY,
    Z,
    ZZ,
    QuaternionCartanBlock,
    classify_su4,
    phase_aligned_operator_error,
    quaternion_to_su2_matrix,
)

from .circuit import Circuit
from .depth import circuit_depth
from .ops import Operation
from .report import CompilerReport
from .verification import verify_equivalence

SU4QMode = Literal["analyze_only", "emit_candidate", "replace_if_backend_requests"]
_UNITARY_GATES = frozenset(
    {
        "i",
        "x",
        "y",
        "z",
        "h",
        "s",
        "t",
        "rx",
        "ry",
        "rz",
        "phaseshift",
        "u1q",
        "cx",
        "cy",
        "cz",
        "swap",
        "iswap",
        "rxx",
        "ryy",
        "rzz",
        "su4q",
    }
)


def _finite_angle(op: Operation) -> float:
    value = op.params.get("angle")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"unresolved angle for {op.gate}")
    angle = float(value)
    if not math.isfinite(angle):
        raise ValueError(f"non-finite angle for {op.gate}")
    return angle


def _single_qubit_matrix(op: Operation) -> NDArray[np.complex128]:
    gate = op.gate
    if gate == "i":
        return I2
    if gate == "x":
        return X
    if gate == "y":
        return Y
    if gate == "z":
        return Z
    if gate == "h":
        return np.asarray([[1, 1], [1, -1]], dtype=np.complex128) / math.sqrt(2.0)
    if gate == "s":
        return np.asarray([[1, 0], [0, 1j]], dtype=np.complex128)
    if gate == "t":
        return np.asarray([[1, 0], [0, np.exp(1j * math.pi / 4)]], dtype=np.complex128)
    if gate in {"rx", "ry", "rz"}:
        angle = _finite_angle(op)
        generator = {"rx": X, "ry": Y, "rz": Z}[gate]
        return np.asarray(
            math.cos(angle / 2.0) * I2 - 1j * math.sin(angle / 2.0) * generator,
            dtype=np.complex128,
        )
    if gate == "phaseshift":
        angle = _finite_angle(op)
        return np.asarray([[1, 0], [0, np.exp(1j * angle)]], dtype=np.complex128)
    if gate == "u1q":
        values = []
        for name in ("w", "x", "y", "z"):
            value = op.params.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("unresolved u1q component")
            values.append(float(value))
        return quaternion_to_su2_matrix(values)
    raise ValueError(f"unsupported single-qubit operation {gate}")


def _controlled_matrix(
    control: int, target: int, base: NDArray[np.complex128]
) -> NDArray[np.complex128]:
    matrix = np.zeros((4, 4), dtype=np.complex128)
    for column in range(4):
        bits = [(column >> 1) & 1, column & 1]
        if bits[control] == 0:
            matrix[column, column] = 1.0
            continue
        for output_bit in (0, 1):
            output = list(bits)
            output[target] = output_bit
            row = 2 * output[0] + output[1]
            matrix[row, column] = base[output_bit, bits[target]]
    return matrix


def _operation_matrix(op: Operation, pair: tuple[int, int]) -> NDArray[np.complex128]:
    touched = set(op.targets) | set(op.controls)
    if not touched.issubset(pair):
        raise ValueError("operation touches a qubit outside the candidate pair")
    if len(touched) == 1:
        local = _single_qubit_matrix(op)
        return np.kron(local, I2) if next(iter(touched)) == pair[0] else np.kron(I2, local)
    if op.gate in {"cx", "cy", "cz"}:
        control = pair.index(op.controls[0])
        target = pair.index(op.targets[0])
        base = {"cx": X, "cy": Y, "cz": Z}[op.gate]
        return _controlled_matrix(control, target, base)
    if op.gate == "swap":
        return np.asarray(
            [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]],
            dtype=np.complex128,
        )
    if op.gate == "iswap":
        return np.asarray(
            [[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]],
            dtype=np.complex128,
        )
    if op.gate in {"rxx", "ryy", "rzz"}:
        angle = _finite_angle(op)
        generator = {"rxx": XX, "ryy": YY, "rzz": ZZ}[op.gate]
        return np.asarray(
            math.cos(angle / 2.0) * np.eye(4)
            - 1j * math.sin(angle / 2.0) * generator,
            dtype=np.complex128,
        )
    if op.gate == "su4q":
        block = QuaternionCartanBlock.from_dict(op.params["block"])
        matrix = block.to_unitary()
        if tuple(op.targets) != pair:
            swap = _operation_matrix(Operation("swap", list(pair)), pair)
            matrix = swap @ matrix @ swap
        return matrix
    raise ValueError(f"unsupported two-qubit operation {op.gate}")


def _window_unitary(operations: list[Operation], pair: tuple[int, int]) -> NDArray[np.complex128]:
    unitary = np.eye(4, dtype=np.complex128)
    for operation in operations:
        unitary = _operation_matrix(operation, pair) @ unitary
    return unitary


def _copy_circuit(circuit: Circuit) -> Circuit:
    copied = Circuit(circuit.num_qubits, metadata=dict(circuit.metadata))
    for operation in circuit.operations:
        copied.add(Operation.from_descriptor(operation.to_descriptor()))
    return copied


def _candidate_windows(circuit: Circuit) -> list[tuple[int, int, tuple[int, int]]]:
    windows: list[tuple[int, int, tuple[int, int]]] = []
    start: int | None = None
    pair_members: set[int] = set()
    operations = circuit.operations

    def finish(end: int) -> None:
        nonlocal start, pair_members
        if start is not None and len(pair_members) == 2:
            windows.append((start, end, tuple(sorted(pair_members))))  # type: ignore[arg-type]
        start = None
        pair_members = set()

    for index, operation in enumerate(operations):
        touched = set(operation.targets) | set(operation.controls)
        if operation.gate not in _UNITARY_GATES or operation.gate in {"measure", "barrier"}:
            finish(index)
            continue
        if not touched or len(touched) > 2:
            finish(index)
            continue
        if start is None:
            start = index
            pair_members = set(touched)
            continue
        if len(pair_members | touched) > 2:
            finish(index)
            start = index
            pair_members = set(touched)
            continue
        pair_members |= touched
    finish(len(operations))
    return windows


def extract_su4q_blocks(
    circuit: Circuit,
    *,
    mode: SU4QMode = "analyze_only",
    backend_requests_su4q: bool = False,
    tolerance: float = 1e-10,
    max_window_operations: int = 64,
) -> tuple[Circuit, CompilerReport]:
    """Analyze or explicitly replace maximal verified two-qubit unitary windows."""
    if mode not in {"analyze_only", "emit_candidate", "replace_if_backend_requests"}:
        raise ValueError(f"unsupported su4q extraction mode: {mode}")
    if max_window_operations < 1:
        raise ValueError("max_window_operations must be positive")

    public_candidates: list[dict[str, Any]] = []
    replacements: dict[int, tuple[int, Operation]] = {}
    skipped_reasons: list[str] = []
    operations = circuit.operations
    for start, end, pair in _candidate_windows(circuit):
        window = operations[start:end]
        if len(window) > max_window_operations:
            skipped_reasons.append(f"window[{start}:{end}] exceeds dense verification limit")
            continue
        try:
            unitary = _window_unitary(window, pair)
            descriptor_payload = [operation.to_descriptor() for operation in window]
            source_hash = hashlib.sha256(
                json.dumps(descriptor_payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            block = QuaternionCartanBlock.from_unitary(unitary, source_hash=source_hash)
            validation = block.validate()
            reconstruction_error, _ = phase_aligned_operator_error(unitary, block.to_unitary())
            if not validation["valid"] or reconstruction_error > tolerance:
                skipped_reasons.append(f"window[{start}:{end}] failed reconstruction proof")
                continue
            classification = classify_su4(block, tolerance=tolerance)
        except (ImportError, KeyError, TypeError, ValueError) as exc:
            skipped_reasons.append(f"window[{start}:{end}] not emitted: {exc}")
            continue

        operation = Operation(gate="su4q", targets=list(pair), params={"block": block.to_dict()})
        candidate = {
            "descriptor": operation.to_descriptor(),
            "original_operations": descriptor_payload,
            "original_operation_range": [start, end],
            "nonlocal_fingerprint": block.nonlocal_fingerprint(),
            "weyl_class": classification.class_label,
            "proof": {
                "dense_numerical_equivalence": True,
                "qubit_ordering": list(pair),
                "block_validation": True,
                "reconstruction_error": reconstruction_error,
                "tolerance": tolerance,
            },
        }
        public_candidates.append(candidate)
        replacements[start] = (end, operation)

    should_replace = mode == "replace_if_backend_requests" and backend_requests_su4q
    output = _copy_circuit(circuit)
    fallback_reason: str | None = None
    selected_strategy = "original_operations"
    passes: list[str] = []
    if should_replace and replacements:
        candidate_output = Circuit(circuit.num_qubits, metadata=dict(circuit.metadata))
        index = 0
        while index < len(operations):
            replacement = replacements.get(index)
            if replacement is None:
                candidate_output.add(Operation.from_descriptor(operations[index].to_descriptor()))
                index += 1
                continue
            end, operation = replacement
            candidate_output.add(operation)
            index = end
        proof = verify_equivalence(circuit, candidate_output, max_dense_qubits=8)
        if proof.verified:
            output = candidate_output
            selected_strategy = "su4q"
            passes = ["extract_su4q_blocks"]
        else:
            fallback_reason = "replacement_verification_failed"
    elif mode == "replace_if_backend_requests" and not backend_requests_su4q:
        fallback_reason = "backend_did_not_request_su4q"
    elif not public_candidates and skipped_reasons:
        fallback_reason = "no_proven_su4q_candidate"

    report = CompilerReport(
        original_gate_count=len(circuit),
        optimized_gate_count=len(output),
        original_depth=circuit_depth(circuit),
        optimized_depth=circuit_depth(output),
        passes_applied=passes,
        equivalence_status="VERIFIED",
        equivalence_report={
            "status": "VERIFIED",
            "verified": True,
            "mode": mode,
            "backend_requests_su4q": backend_requests_su4q,
            "su4q_skipped_reasons": skipped_reasons,
        },
        equivalence_verified=True,
        equivalence_guaranteed=True,
        optimization_applied=selected_strategy == "su4q",
        fallback_reason=fallback_reason,
        su4q_candidates=public_candidates,
        nonlocal_fingerprints=[
            str(candidate["nonlocal_fingerprint"]) for candidate in public_candidates
        ],
        weyl_classes=[str(candidate["weyl_class"]) for candidate in public_candidates],
        candidate_reconstruction_errors=[
            float(candidate["proof"]["reconstruction_error"]) for candidate in public_candidates
        ],
        candidate_original_operation_ranges=[
            list(candidate["original_operation_range"]) for candidate in public_candidates
        ],
        selected_two_qubit_strategy=selected_strategy,
    )
    return output, report


def analyze_two_qubit_blocks(
    circuit: Circuit,
    *,
    tolerance: float = 1e-10,
    max_window_operations: int = 64,
) -> CompilerReport:
    """Return proof-gated analysis without changing the input circuit."""
    _, report = extract_su4q_blocks(
        circuit,
        mode="analyze_only",
        tolerance=tolerance,
        max_window_operations=max_window_operations,
    )
    return report
