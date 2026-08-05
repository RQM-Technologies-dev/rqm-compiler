"""Verified regional optimization for circuits larger than the dense proof bound."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .circuit import Circuit
from .compile import optimize_circuit
from .ops import Operation
from .validate import validate_circuit
from .verification import EquivalenceStatus, verify_equivalence


_BOUNDARY_GATES = frozenset({"measure", "barrier"})


@dataclass(frozen=True)
class RegionalOptimizationRecord:
    """Proof and metric record for one contiguous optimization region."""

    region_index: int
    source_start: int
    source_end: int
    qubits: list[int]
    original_gate_count: int
    optimized_gate_count: int
    changed: bool
    verification_status: str
    verification_method: str
    max_abs_err: float | None
    passes_applied: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return asdict(self)


@dataclass
class RegionalCompilerReport:
    """All-or-nothing report returned by :func:`optimize_circuit_regions`."""

    max_region_qubits: int
    original_gate_count: int
    optimized_gate_count: int
    regions: list[RegionalOptimizationRecord] = field(default_factory=list)
    boundary_operation_count: int = 0
    changed_region_count: int = 0
    committed: bool = False
    equivalence_status: str = EquivalenceStatus.VERIFIED.value
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "max_region_qubits": self.max_region_qubits,
            "original_gate_count": self.original_gate_count,
            "optimized_gate_count": self.optimized_gate_count,
            "regions": [record.to_dict() for record in self.regions],
            "boundary_operation_count": self.boundary_operation_count,
            "changed_region_count": self.changed_region_count,
            "committed": self.committed,
            "equivalence_status": self.equivalence_status,
            "fallback_reason": self.fallback_reason,
        }


@dataclass(frozen=True)
class _Region:
    source_start: int
    source_end: int
    operations: list[Operation]
    qubits: list[int]


def _clone_circuit(circuit: Circuit) -> Circuit:
    clone = Circuit(circuit.num_qubits, metadata=dict(circuit.metadata))
    for operation in circuit.operations:
        clone.add(Operation.from_descriptor(operation.to_descriptor()))
    return clone


def _operation_qubits(operation: Operation) -> set[int]:
    return set(operation.targets) | set(operation.controls)


def _partition_regions(circuit: Circuit, max_region_qubits: int) -> list[_Region]:
    regions: list[_Region] = []
    pending: list[Operation] = []
    pending_qubits: set[int] = set()
    pending_start = 0

    def flush(end: int) -> None:
        nonlocal pending, pending_qubits, pending_start
        if not pending:
            return
        regions.append(
            _Region(
                source_start=pending_start,
                source_end=end,
                operations=pending,
                qubits=sorted(pending_qubits),
            )
        )
        pending = []
        pending_qubits = set()

    for index, operation in enumerate(circuit.operations):
        if operation.gate in _BOUNDARY_GATES:
            flush(index)
            continue
        touched = _operation_qubits(operation)
        if pending and len(pending_qubits | touched) > max_region_qubits:
            flush(index)
        if not pending:
            pending_start = index
        pending.append(operation)
        pending_qubits.update(touched)
    flush(len(circuit.operations))
    return regions


def _localize(region: _Region) -> tuple[Circuit, dict[int, int]]:
    global_to_local = {qubit: index for index, qubit in enumerate(region.qubits)}
    local = Circuit(len(region.qubits))
    for operation in region.operations:
        local.add(
            Operation(
                gate=operation.gate,
                targets=[global_to_local[qubit] for qubit in operation.targets],
                controls=[global_to_local[qubit] for qubit in operation.controls],
                params=dict(operation.params),
            )
        )
    return local, global_to_local


def _globalize(circuit: Circuit, qubits: list[int]) -> list[Operation]:
    return [
        Operation(
            gate=operation.gate,
            targets=[qubits[index] for index in operation.targets],
            controls=[qubits[index] for index in operation.controls],
            params=dict(operation.params),
        )
        for operation in circuit.operations
    ]


def optimize_circuit_regions(
    circuit: Circuit,
    *,
    max_region_qubits: int = 3,
) -> tuple[Circuit, RegionalCompilerReport]:
    """Optimize contiguous small regions and commit only if every change is verified.

    Measurement and barrier operations are preserved verbatim and form region
    boundaries. Regions are deterministic contiguous slices whose union of
    touched qubits is no larger than ``max_region_qubits``. If verification of
    any changed region is not established, the exact input structure is returned
    and every tentative regional change is withheld.
    """

    if not 1 <= max_region_qubits <= 3:
        raise ValueError("max_region_qubits must be between 1 and 3 inclusive")
    validate_circuit(circuit)

    source_operations = circuit.operations
    regions = _partition_regions(circuit, max_region_qubits)
    report = RegionalCompilerReport(
        max_region_qubits=max_region_qubits,
        original_gate_count=len(source_operations),
        optimized_gate_count=len(source_operations),
        boundary_operation_count=sum(
            int(operation.gate in _BOUNDARY_GATES) for operation in source_operations
        ),
    )

    replacements: dict[int, tuple[int, list[Operation]]] = {}
    proof_failed = False
    for region_index, region in enumerate(regions):
        local, _ = _localize(region)
        optimized, compiler_report = optimize_circuit(local)
        changed = optimized.to_descriptors() != local.to_descriptors()
        proof = verify_equivalence(local, optimized)
        verified = proof.status is EquivalenceStatus.VERIFIED and proof.verified is True
        if changed and not verified:
            proof_failed = True
        if changed and verified:
            replacements[region.source_start] = (
                region.source_end,
                _globalize(optimized, region.qubits),
            )
        report.regions.append(
            RegionalOptimizationRecord(
                region_index=region_index,
                source_start=region.source_start,
                source_end=region.source_end,
                qubits=list(region.qubits),
                original_gate_count=len(local),
                optimized_gate_count=len(optimized),
                changed=changed,
                verification_status=proof.status.value,
                verification_method=proof.method,
                max_abs_err=proof.max_abs_err,
                passes_applied=list(compiler_report.passes_applied) if changed else [],
            )
        )

    if proof_failed:
        report.equivalence_status = EquivalenceStatus.UNVERIFIED.value
        report.fallback_reason = "regional_verification_not_established"
        return _clone_circuit(circuit), report

    output = Circuit(circuit.num_qubits, metadata=dict(circuit.metadata))
    index = 0
    while index < len(source_operations):
        replacement = replacements.get(index)
        if replacement is not None:
            end, operations = replacement
            for operation in operations:
                output.add(operation)
            index = end
            continue
        output.add(Operation.from_descriptor(source_operations[index].to_descriptor()))
        index += 1

    report.changed_region_count = len(replacements)
    report.committed = bool(replacements)
    report.optimized_gate_count = len(output)
    return output, report
