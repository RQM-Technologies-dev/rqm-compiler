from __future__ import annotations

import math
from pathlib import Path

import pytest
from rqm_entanglement import QuaternionCartanBlock, cartan_core_from_weyl

from rqm_compiler import (
    Circuit,
    analyze_two_qubit_blocks,
    extract_su4q_blocks,
    optimize_circuit,
    verify_equivalence,
)
from rqm_compiler.ops import Operation
from rqm_compiler.validate import validate_circuit


def _identity_block() -> QuaternionCartanBlock:
    identity = (1.0, 0.0, 0.0, 0.0)
    return QuaternionCartanBlock.from_components(
        left_q0=identity,
        left_q1=identity,
        cartan_a=0.0,
        cartan_b=0.0,
        cartan_c=0.0,
        right_q0=identity,
        right_q1=identity,
    )


def test_su4q_descriptor_round_trip_and_validation() -> None:
    circuit = Circuit(2).su4q(0, 1, _identity_block())
    validate_circuit(circuit)
    restored = Circuit.from_descriptors(circuit.to_descriptors(), num_qubits=2)
    assert restored.to_descriptors() == circuit.to_descriptors()
    assert restored.operations[0].params["block"]["convention_version"].startswith("rqm-su4q-v1")


def test_standard_pair_rotations_have_dense_semantics() -> None:
    circuit = Circuit(2).rxx(0, 1, 0.31).ryy(0, 1, -0.19).rzz(0, 1, 0.47)
    assert verify_equivalence(circuit, circuit).verified
    report = analyze_two_qubit_blocks(circuit)
    assert len(report.su4q_candidates) == 1
    assert report.candidate_reconstruction_errors[0] <= 1e-10


@pytest.mark.parametrize(
    "build",
    [
        lambda c: c.cx(0, 1),
        lambda c: c.iswap(0, 1),
        lambda c: c.swap(0, 1),
        lambda c: c.rzz(0, 1, 0.73),
        lambda c: c.rxx(0, 1, 0.42).ryy(0, 1, 0.21).rzz(0, 1, -0.17),
    ],
)
def test_requested_workload_families_emit_proven_candidate(build) -> None:
    circuit = Circuit(2)
    build(circuit)
    report = analyze_two_qubit_blocks(circuit)
    assert report.su4q_candidates
    proof = report.su4q_candidates[0]["proof"]
    assert proof["dense_numerical_equivalence"] is True
    assert proof["block_validation"] is True
    assert proof["reconstruction_error"] <= 1e-10


def test_generic_interior_block_can_be_added_directly() -> None:
    block = QuaternionCartanBlock.from_unitary(cartan_core_from_weyl(0.61, 0.27, -0.13))
    circuit = Circuit(2).su4q(0, 1, block)
    report = analyze_two_qubit_blocks(circuit)
    assert report.weyl_classes == ["generic_interior"]


def test_local_only_window_is_classified_without_entanglement_claim() -> None:
    circuit = Circuit(2).h(0).x(1)
    report = analyze_two_qubit_blocks(circuit)
    assert report.weyl_classes == ["local_identity"]


def test_measurement_barrier_and_third_qubit_split_windows() -> None:
    circuit = Circuit(3).h(0).cx(0, 1).barrier(0, 1).h(2).rzz(0, 1, 0.2)
    circuit.measure(0, key="m0")
    report = analyze_two_qubit_blocks(circuit)
    assert len(report.su4q_candidates) == 2
    assert report.candidate_original_operation_ranges == [[0, 2], [4, 5]]


def test_unresolved_parameter_fails_closed_and_preserves_original() -> None:
    circuit = Circuit(2)
    circuit.add(Operation("rzz", [0, 1], params={"angle": "theta"}))
    output, report = extract_su4q_blocks(circuit, mode="emit_candidate")
    assert output.to_descriptors() == circuit.to_descriptors()
    assert report.su4q_candidates == []
    assert report.fallback_reason == "no_proven_su4q_candidate"


def test_replacement_requires_explicit_backend_request() -> None:
    circuit = Circuit(2).h(0).cx(0, 1)
    withheld, withheld_report = extract_su4q_blocks(
        circuit,
        mode="replace_if_backend_requests",
        backend_requests_su4q=False,
    )
    assert withheld.to_descriptors() == circuit.to_descriptors()
    assert withheld_report.fallback_reason == "backend_did_not_request_su4q"

    replaced, report = extract_su4q_blocks(
        circuit,
        mode="replace_if_backend_requests",
        backend_requests_su4q=True,
    )
    assert [operation.gate for operation in replaced.operations] == ["su4q"]
    assert report.selected_two_qubit_strategy == "su4q"
    assert verify_equivalence(circuit, replaced).verified


def test_failed_candidate_proof_preserves_original(monkeypatch: pytest.MonkeyPatch) -> None:
    import rqm_compiler.su4_blocks as module

    monkeypatch.setattr(module, "phase_aligned_operator_error", lambda *_: (1.0, 0.0))
    circuit = Circuit(2).cx(0, 1)
    output, report = extract_su4q_blocks(
        circuit,
        mode="replace_if_backend_requests",
        backend_requests_su4q=True,
    )
    assert output.to_descriptors() == circuit.to_descriptors()
    assert report.su4q_candidates == []


def test_default_optimization_pipeline_never_introduces_su4q() -> None:
    circuit = Circuit(2).h(0).cx(0, 1)
    optimized, report = optimize_circuit(circuit)
    assert all(operation.gate != "su4q" for operation in optimized.operations)
    assert "extract_su4q_blocks" not in report.passes_applied


def test_compiler_source_contains_no_qiskit_import() -> None:
    source_root = Path(__file__).parents[1] / "src" / "rqm_compiler"
    text = "\n".join(path.read_text() for path in source_root.rglob("*.py"))
    assert "import qiskit" not in text.lower()
    assert "from qiskit" not in text.lower()


def test_dense_window_limit_fails_closed() -> None:
    circuit = Circuit(2)
    for _ in range(4):
        circuit.rzz(0, 1, math.pi / 13)
    output, report = extract_su4q_blocks(circuit, max_window_operations=3)
    assert output.to_descriptors() == circuit.to_descriptors()
    assert report.su4q_candidates == []
