from __future__ import annotations

import json

import pytest

from rqm_compiler import Circuit, optimize_circuit_regions
from rqm_compiler.verification import EquivalenceMethod, EquivalenceReport, EquivalenceStatus


def test_large_circuit_commits_only_verified_small_regions() -> None:
    circuit = Circuit(6, metadata={"name": "large"})
    for qubit in range(6):
        circuit.rx(qubit, 0.2).ry(qubit, -0.3).rz(qubit, 0.4)

    optimized, report = optimize_circuit_regions(circuit)

    assert report.committed is True
    assert report.changed_region_count >= 2
    assert report.original_gate_count == 18
    assert report.optimized_gate_count == 6
    assert all(len(region.qubits) <= 3 for region in report.regions)
    assert all(region.verification_status == "VERIFIED" for region in report.regions)
    assert optimized.metadata == {"name": "large"}
    assert len(optimized) == 6
    json.dumps(report.to_dict(), allow_nan=False)


def test_measurements_and_barriers_are_exact_boundaries() -> None:
    circuit = Circuit(4)
    circuit.rx(0, 0.1).ry(0, 0.2)
    circuit.barrier(0, 1, 2, 3)
    circuit.rx(2, 0.3).rz(2, 0.4)
    circuit.measure(0, key="left")
    circuit.measure(2, key="right")

    optimized, report = optimize_circuit_regions(circuit)
    descriptors = optimized.to_descriptors()

    assert report.boundary_operation_count == 3
    assert [item for item in descriptors if item["gate"] == "barrier"] == [
        circuit.to_descriptors()[2]
    ]
    assert [item for item in descriptors if item["gate"] == "measure"] == [
        circuit.to_descriptors()[-2],
        circuit.to_descriptors()[-1],
    ]


def test_failed_changed_region_withholds_all_tentative_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    circuit = Circuit(4)
    circuit.rx(0, 0.1).ry(0, 0.2)
    circuit.rx(3, 0.3).rz(3, 0.4)
    original = circuit.to_descriptors()

    def reject(*args: object, **kwargs: object) -> EquivalenceReport:
        return EquivalenceReport(
            status=EquivalenceStatus.UNVERIFIED,
            method=EquivalenceMethod.NONE.value,
            verified=None,
        )

    monkeypatch.setattr("rqm_compiler.regional.verify_equivalence", reject)
    optimized, report = optimize_circuit_regions(circuit)

    assert optimized.to_descriptors() == original
    assert report.committed is False
    assert report.equivalence_status == "UNVERIFIED"
    assert report.fallback_reason == "regional_verification_not_established"
    assert all(region.changed for region in report.regions)


def test_regional_optimization_is_deterministic_and_does_not_mutate_input() -> None:
    circuit = Circuit(5)
    circuit.rx(0, 0.1).ry(0, 0.2).rz(0, 0.3)
    circuit.cx(0, 1).cx(0, 1)
    circuit.rx(4, -0.7).ry(4, 0.9)
    original = circuit.to_descriptors()

    left, left_report = optimize_circuit_regions(circuit)
    right, right_report = optimize_circuit_regions(circuit)

    assert circuit.to_descriptors() == original
    assert left.to_descriptors() == right.to_descriptors()
    assert left_report.to_dict() == right_report.to_dict()


@pytest.mark.parametrize("value", [0, 4, -1])
def test_invalid_region_bound_rejected(value: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 3"):
        optimize_circuit_regions(Circuit(1), max_region_qubits=value)
