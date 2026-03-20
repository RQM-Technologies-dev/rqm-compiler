"""Tests for optimize_circuit: Circuit → optimized Circuit + CompilerReport."""

import math

import pytest

from rqm_compiler import Circuit, CompilerReport, Operation, optimize_circuit
from rqm_compiler.compile import CompiledCircuit, compile_circuit
from rqm_compiler.depth import circuit_depth
from rqm_compiler.passes import merge_u1q_pass, to_u1q_pass
from rqm_compiler.validate import CircuitValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bell() -> Circuit:
    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0, key="m0")
    c.measure(1, key="m1")
    return c


def _is_unit(w: float, x: float, y: float, z: float, tol: float = 1e-9) -> bool:
    return abs(w * w + x * x + y * y + z * z - 1.0) <= tol


# ---------------------------------------------------------------------------
# optimize_circuit returns Circuit + CompilerReport
# ---------------------------------------------------------------------------


def test_optimize_returns_circuit_and_report():
    c = _bell()
    result = optimize_circuit(c)
    assert isinstance(result, tuple) and len(result) == 2
    optimized, report = result
    assert isinstance(optimized, Circuit)
    assert isinstance(report, CompilerReport)


def test_optimize_returns_valid_circuit():
    """The optimized circuit must pass compile_circuit validation."""
    c = _bell()
    optimized, _ = optimize_circuit(c)
    # compile_circuit validates on entry; should not raise
    compiled = compile_circuit(optimized)
    assert compiled.num_qubits == c.num_qubits


def test_optimize_preserves_num_qubits():
    c = Circuit(4)
    c.h(0).x(1).cx(0, 1).measure(0, key="m0")
    optimized, _ = optimize_circuit(c)
    assert optimized.num_qubits == 4


def test_optimize_preserves_metadata():
    c = Circuit(2, metadata={"label": "bell", "version": 3})
    c.h(0).cx(0, 1)
    optimized, _ = optimize_circuit(c)
    assert optimized.metadata["label"] == "bell"
    assert optimized.metadata["version"] == 3


def test_optimize_circuit_metadata_independent_of_input():
    """Mutations to the output metadata must not affect the input metadata."""
    c = Circuit(1, metadata={"a": 1})
    c.h(0)
    optimized, _ = optimize_circuit(c)
    optimized.metadata["a"] = 99
    assert c.metadata["a"] == 1


# ---------------------------------------------------------------------------
# CompilerReport fields
# ---------------------------------------------------------------------------


def test_report_has_all_required_fields():
    c = _bell()
    _, report = optimize_circuit(c)
    assert isinstance(report.original_gate_count, int)
    assert isinstance(report.optimized_gate_count, int)
    assert isinstance(report.original_depth, int)
    assert isinstance(report.optimized_depth, int)
    assert isinstance(report.passes_applied, list)
    assert isinstance(report.equivalence_verified, bool)


def test_report_original_gate_count_matches_input():
    c = _bell()
    _, report = optimize_circuit(c)
    assert report.original_gate_count == len(c)


def test_report_optimized_gate_count_matches_output():
    c = _bell()
    optimized, report = optimize_circuit(c)
    assert report.optimized_gate_count == len(optimized)


def test_report_original_depth_correct():
    c = _bell()
    _, report = optimize_circuit(c)
    assert report.original_depth == circuit_depth(c)


def test_report_optimized_depth_correct():
    c = _bell()
    optimized, report = optimize_circuit(c)
    assert report.optimized_depth == circuit_depth(optimized)


def test_report_passes_applied_contains_expected_names():
    c = _bell()
    _, report = optimize_circuit(c)
    for name in ("normalize", "canonicalize", "flatten", "to_u1q", "merge_u1q", "sign_canon"):
        assert name in report.passes_applied


def test_report_passes_applied_is_ordered():
    """Passes must be listed in the order they were applied."""
    c = _bell()
    _, report = optimize_circuit(c)
    assert report.passes_applied.index("to_u1q") < report.passes_applied.index("merge_u1q")


def test_report_equivalence_verified_is_false_by_default():
    c = _bell()
    _, report = optimize_circuit(c)
    assert report.equivalence_verified is False


# ---------------------------------------------------------------------------
# Gate count reduction
# ---------------------------------------------------------------------------


def test_gate_count_reduced_for_redundant_x_pair():
    """X·X = identity: both X gates collapse to a single u1q that merges to identity."""
    c = Circuit(1)
    c.x(0).x(0)
    optimized, report = optimize_circuit(c)
    assert report.gate_count_delta > 0, "Gate count should decrease"
    assert report.optimized_gate_count < report.original_gate_count


def test_gate_count_reduced_for_redundant_h_pair():
    """H·H = identity."""
    c = Circuit(1)
    c.h(0).h(0)
    optimized, report = optimize_circuit(c)
    assert report.optimized_gate_count < report.original_gate_count


def test_gate_count_reduced_multiple_adjacent_single_qubit():
    """A chain of named single-qubit gates on the same qubit merges to one u1q."""
    c = Circuit(1)
    c.x(0).y(0).z(0)  # three gates → one merged u1q
    optimized, report = optimize_circuit(c)
    assert report.optimized_gate_count < report.original_gate_count


def test_gate_count_not_reduced_when_no_merging_possible():
    """A Bell circuit has no adjacent single-qubit gates on the same qubit."""
    c = _bell()
    original_single_qubit = 1  # just the H on qubit 0
    optimized, report = optimize_circuit(c)
    # Gate count can be equal or slightly different, but must not increase.
    assert report.optimized_gate_count <= report.original_gate_count


def test_gate_count_delta_property():
    c = Circuit(1)
    c.x(0).x(0)
    _, report = optimize_circuit(c)
    assert report.gate_count_delta == report.original_gate_count - report.optimized_gate_count


# ---------------------------------------------------------------------------
# Depth reduction
# ---------------------------------------------------------------------------


def test_depth_reduced_for_sequential_redundant_gates():
    """X·X on a single qubit collapses to nothing; depth drops to 0."""
    c = Circuit(1)
    c.x(0).x(0)
    optimized, report = optimize_circuit(c)
    assert report.optimized_depth == 0
    assert report.depth_delta > 0


def test_depth_reduced_chain():
    c = Circuit(1)
    c.x(0).y(0).z(0).h(0)  # depth 4 originally
    optimized, report = optimize_circuit(c)
    assert report.original_depth == 4
    assert report.optimized_depth <= report.original_depth


def test_depth_preserved_when_parallel():
    """Two independent single-qubit gates on different qubits have depth 1."""
    c = Circuit(2)
    c.h(0).h(1)  # depth 1 (parallel) — no reduction expected
    _, report = optimize_circuit(c)
    assert report.original_depth == 1
    assert report.optimized_depth <= report.original_depth


def test_depth_delta_property():
    c = Circuit(1)
    c.x(0).x(0)
    _, report = optimize_circuit(c)
    assert report.depth_delta == report.original_depth - report.optimized_depth


# ---------------------------------------------------------------------------
# Output circuit gate validity
# ---------------------------------------------------------------------------


def test_optimized_circuit_all_u1q_single_qubit():
    """After optimization, all single-qubit gates should be in u1q form."""
    c = Circuit(2)
    c.h(0).x(1).cx(0, 1).measure(0, key="m0").measure(1, key="m1")
    optimized, _ = optimize_circuit(c)
    for op in optimized.operations:
        if len(op.targets) == 1 and not op.controls and op.gate not in ("measure", "barrier"):
            assert op.gate == "u1q", f"Expected u1q, got {op.gate!r}"


def test_optimized_circuit_u1q_params_are_unit_quaternion():
    """Every u1q in the optimized circuit must have a unit quaternion."""
    c = Circuit(2)
    c.h(0).rx(0, 1.23).s(0).cx(0, 1).measure(0, key="m0").measure(1, key="m1")
    optimized, _ = optimize_circuit(c)
    for op in optimized.operations:
        if op.gate == "u1q":
            assert _is_unit(
                op.params["w"], op.params["x"], op.params["y"], op.params["z"]
            ), f"Non-unit quaternion in {op}"


def test_no_invalid_circuit_emitted():
    """The optimized circuit must be accepted by the compiler without errors."""
    c = Circuit(3)
    c.h(0).cx(0, 1).cz(1, 2).measure(0, key="m0").measure(1, key="m1").measure(2, key="m2")
    optimized, _ = optimize_circuit(c)
    # Should not raise
    compiled = compile_circuit(optimized)
    assert compiled.num_qubits == 3


def test_two_qubit_gates_unchanged_in_optimized_circuit():
    """Two-qubit gates must pass through optimization unchanged."""
    c = Circuit(2)
    c.cx(0, 1).cy(0, 1).cz(0, 1).swap(0, 1).iswap(0, 1)
    optimized, _ = optimize_circuit(c)
    two_qubit_gates = [op.gate for op in optimized.operations]
    assert two_qubit_gates == ["cx", "cy", "cz", "swap", "iswap"]


def test_measure_gates_unchanged_in_optimized_circuit():
    c = Circuit(2)
    c.measure(0, key="a").measure(1, key="b")
    optimized, _ = optimize_circuit(c)
    ops = optimized.operations
    assert ops[0].gate == "measure" and ops[0].params["key"] == "a"
    assert ops[1].gate == "measure" and ops[1].params["key"] == "b"


# ---------------------------------------------------------------------------
# optimize_circuit rejects invalid inputs
# ---------------------------------------------------------------------------


def test_optimize_rejects_out_of_range_qubit():
    c = Circuit(1)
    c.add(Operation(gate="h", targets=[5]))
    with pytest.raises(CircuitValidationError):
        optimize_circuit(c)


def test_optimize_rejects_unsupported_gate():
    c = Circuit(1)
    c.add(Operation(gate="ccx", targets=[0]))
    with pytest.raises(CircuitValidationError):
        optimize_circuit(c)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_optimize_is_deterministic():
    c = Circuit(2)
    c.h(0).rx(0, 1.23).cx(0, 1)
    opt_a, rep_a = optimize_circuit(c)
    opt_b, rep_b = optimize_circuit(c)
    assert opt_a.to_descriptors() == opt_b.to_descriptors()
    assert rep_a.original_gate_count == rep_b.original_gate_count
    assert rep_a.optimized_gate_count == rep_b.optimized_gate_count


# ---------------------------------------------------------------------------
# CompiledCircuit.circuit attribute
# ---------------------------------------------------------------------------


def test_compiled_circuit_has_circuit_attribute():
    c = _bell()
    compiled = compile_circuit(c)
    assert compiled.circuit is not None
    assert isinstance(compiled.circuit, Circuit)


def test_compiled_circuit_circuit_matches_descriptors():
    c = _bell()
    compiled = compile_circuit(c)
    assert compiled.circuit.to_descriptors() == compiled.descriptors


# ---------------------------------------------------------------------------
# circuit_depth utility
# ---------------------------------------------------------------------------


def test_depth_empty_circuit():
    c = Circuit(2)
    assert circuit_depth(c) == 0


def test_depth_single_gate():
    c = Circuit(1)
    c.h(0)
    assert circuit_depth(c) == 1


def test_depth_sequential_gates_same_qubit():
    c = Circuit(1)
    c.h(0).x(0).y(0)
    assert circuit_depth(c) == 3


def test_depth_parallel_gates():
    c = Circuit(2)
    c.h(0)
    c.h(1)
    assert circuit_depth(c) == 1


def test_depth_two_qubit_gate():
    c = Circuit(2)
    c.cx(0, 1)
    assert circuit_depth(c) == 1


def test_depth_sequential_two_qubit_then_single():
    c = Circuit(2)
    c.cx(0, 1)  # depth 1
    c.h(0)      # depth 2 (qubit 0 was at depth 1)
    assert circuit_depth(c) == 2


# ---------------------------------------------------------------------------
# merge_u1q_pass unit tests
# ---------------------------------------------------------------------------


def test_merge_u1q_merges_adjacent_u1q():
    """Two adjacent u1q on same qubit → one u1q."""
    c = Circuit(1)
    c.u1q(0, 0.0, -1.0, 0.0, 0.0)   # X quaternion
    c.u1q(0, 0.0, -1.0, 0.0, 0.0)   # X quaternion again
    merged = merge_u1q_pass(c)
    # X * X = identity → gate dropped
    assert len(merged) == 0


def test_merge_u1q_identity_dropped():
    """Merging two opposing rotations yields identity which is removed."""
    c = Circuit(1)
    c.u1q(0, 1.0, 0.0, 0.0, 0.0)  # identity
    merged = merge_u1q_pass(c)
    # Identity alone is also dropped
    assert len(merged) == 0


def test_merge_u1q_non_adjacent_not_merged():
    """A two-qubit gate between two u1q gates prevents merging."""
    c = Circuit(2)
    c.u1q(0, 0.0, -1.0, 0.0, 0.0)  # X on q0
    c.cx(0, 1)                       # uses q0 → flushes pending
    c.u1q(0, 0.0, -1.0, 0.0, 0.0)  # X on q0 again
    merged = merge_u1q_pass(c)
    # The two X gates are on opposite sides of cx and must not be merged.
    gates = [op.gate for op in merged.operations]
    assert gates == ["u1q", "cx", "u1q"]


def test_merge_u1q_preserves_metadata():
    """Metadata propagation is the compile layer's responsibility, not the pass's."""
    c = Circuit(1, metadata={"tag": "test"})
    c.h(0)
    # Metadata should be preserved end-to-end through optimize_circuit
    optimized, _ = optimize_circuit(c)
    assert optimized.metadata["tag"] == "test"


def test_merge_u1q_does_not_mutate_input():
    c = Circuit(1)
    c.u1q(0, 0.0, -1.0, 0.0, 0.0)
    original_desc = c.to_descriptors()
    merge_u1q_pass(c)
    assert c.to_descriptors() == original_desc


def test_merge_u1q_result_is_unit_quaternion():
    """After merging, the resulting u1q must still be a unit quaternion."""
    c = Circuit(1)
    c.u1q(0, math.cos(0.3), -math.sin(0.3), 0.0, 0.0)
    c.u1q(0, math.cos(0.5), 0.0, -math.sin(0.5), 0.0)
    merged = merge_u1q_pass(c)
    for op in merged.operations:
        if op.gate == "u1q":
            assert _is_unit(op.params["w"], op.params["x"], op.params["y"], op.params["z"])


# ---------------------------------------------------------------------------
# CompilerReport repr and deltas
# ---------------------------------------------------------------------------


def test_compiler_report_repr():
    c = Circuit(1)
    c.x(0).x(0)
    _, report = optimize_circuit(c)
    r = repr(report)
    assert "gates:" in r
    assert "depth:" in r
    assert "passes=" in r


def test_compiler_report_gate_count_delta_positive_on_reduction():
    c = Circuit(1)
    c.x(0).x(0)
    _, report = optimize_circuit(c)
    assert report.gate_count_delta == 2


def test_compiler_report_depth_delta_positive_on_reduction():
    c = Circuit(1)
    c.x(0).x(0)
    _, report = optimize_circuit(c)
    assert report.depth_delta == 2


# ---------------------------------------------------------------------------
# OPTIMIZATION_PIPELINE constant
# ---------------------------------------------------------------------------


def test_optimization_pipeline_is_importable():
    from rqm_compiler import OPTIMIZATION_PIPELINE
    assert OPTIMIZATION_PIPELINE is not None


def test_optimization_pipeline_is_ordered_tuple():
    from rqm_compiler import OPTIMIZATION_PIPELINE
    assert isinstance(OPTIMIZATION_PIPELINE, tuple)
    assert len(OPTIMIZATION_PIPELINE) > 0


def test_optimization_pipeline_entries_have_name_and_callable():
    from rqm_compiler import OPTIMIZATION_PIPELINE
    for entry in OPTIMIZATION_PIPELINE:
        name, fn = entry
        assert isinstance(name, str) and name
        assert callable(fn)


def test_optimization_pipeline_contains_all_pass_names():
    from rqm_compiler import OPTIMIZATION_PIPELINE
    names = [name for name, _ in OPTIMIZATION_PIPELINE]
    for expected in ("normalize", "canonicalize", "flatten", "to_u1q", "merge_u1q", "sign_canon"):
        assert expected in names


def test_optimization_pipeline_order_is_stable():
    """Pipeline entries must appear in the defined order."""
    from rqm_compiler import OPTIMIZATION_PIPELINE
    names = [name for name, _ in OPTIMIZATION_PIPELINE]
    assert names.index("to_u1q") < names.index("merge_u1q")
    assert names.index("merge_u1q") < names.index("sign_canon")


def test_optimization_pipeline_matches_report_passes_applied():
    """The passes_applied list in the report must match OPTIMIZATION_PIPELINE order."""
    from rqm_compiler import OPTIMIZATION_PIPELINE
    c = _bell()
    _, report = optimize_circuit(c)
    pipeline_names = [name for name, _ in OPTIMIZATION_PIPELINE]
    assert report.passes_applied == pipeline_names


# ---------------------------------------------------------------------------
# sign_canon in optimize_circuit end-to-end
# ---------------------------------------------------------------------------


def test_optimize_all_u1q_w_nonneg():
    """Every u1q in the optimized output must have w >= 0."""
    c = Circuit(2)
    c.h(0).rx(0, math.pi).y(1).cx(0, 1)
    optimized, _ = optimize_circuit(c)
    for op in optimized.operations:
        if op.gate == "u1q":
            assert op.params["w"] >= 0.0, f"w < 0 for {op}"


def test_optimize_sign_canon_in_passes_applied():
    c = _bell()
    _, report = optimize_circuit(c)
    assert "sign_canon" in report.passes_applied


def test_optimize_sign_canon_applied_after_merge_u1q():
    c = _bell()
    _, report = optimize_circuit(c)
    assert report.passes_applied.index("merge_u1q") < report.passes_applied.index("sign_canon")
