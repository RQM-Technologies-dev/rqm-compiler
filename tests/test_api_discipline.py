"""
Tests for API discipline, IR correctness, canonical structure, and backend isolation.

Covers the requirements from the problem statement:
1. IR correctness — Circuit stores Operations; Operation fields are correct.
2. Canonical structure — exactly one IR container (Circuit) and one instruction type (Operation).
3. No backend leakage — no qiskit / braket imports anywhere in the package.
4. API discipline — public API matches the Tier 1 / Tier 2 structure.
5. Round-trip sanity — Circuit → operations list → same descriptor structure.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys

import pytest

import rqm_compiler
from rqm_compiler import Circuit, Operation, compile_circuit, optimize_circuit
from rqm_compiler.compile import CompiledCircuit
from rqm_compiler.report import CompilerReport


# ---------------------------------------------------------------------------
# 1. IR correctness
# ---------------------------------------------------------------------------


class TestIRCorrectness:
    """Circuit stores Operations; Operation fields match the canonical schema."""

    def test_circuit_stores_operations(self):
        c = Circuit(2)
        op_h = Operation(gate="h", targets=[0])
        op_cx = Operation(gate="cx", targets=[1], controls=[0])
        c.add(op_h)
        c.add(op_cx)
        assert len(c) == 2
        stored = c.operations
        assert stored[0].gate == "h"
        assert stored[1].gate == "cx"

    def test_operation_has_required_fields(self):
        op = Operation(gate="rx", targets=[0], controls=[], params={"angle": 1.0})
        assert hasattr(op, "gate")
        assert hasattr(op, "targets")
        assert hasattr(op, "controls")
        assert hasattr(op, "params")

    def test_operation_gate_is_lowercase(self):
        op = Operation(gate="RX", targets=[0], params={"angle": 1.0})
        assert op.gate == "rx"

    def test_operation_targets_is_list(self):
        op = Operation(gate="h", targets=[0])
        assert isinstance(op.targets, list)

    def test_operation_controls_is_list(self):
        op = Operation(gate="h", targets=[0])
        assert isinstance(op.controls, list)

    def test_operation_controls_empty_by_default(self):
        op = Operation(gate="h", targets=[0])
        assert op.controls == []

    def test_operation_params_is_dict(self):
        op = Operation(gate="h", targets=[0])
        assert isinstance(op.params, dict)

    def test_operation_params_empty_by_default(self):
        op = Operation(gate="h", targets=[0])
        assert op.params == {}

    def test_operation_to_descriptor_schema(self):
        op = Operation(gate="cx", targets=[1], controls=[0], params={})
        d = op.to_descriptor()
        assert d == {"gate": "cx", "targets": [1], "controls": [0], "params": {}}

    def test_operation_from_descriptor_roundtrip(self):
        d = {"gate": "ry", "targets": [0], "controls": [], "params": {"angle": 0.5}}
        op = Operation.from_descriptor(d)
        assert op.to_descriptor() == d

    def test_circuit_to_descriptors_canonical_shape(self):
        c = Circuit(2)
        c.h(0)
        c.cx(0, 1)
        for d in c.to_descriptors():
            assert set(d.keys()) == {"gate", "targets", "controls", "params"}
            assert isinstance(d["gate"], str)
            assert isinstance(d["targets"], list)
            assert isinstance(d["controls"], list)
            assert isinstance(d["params"], dict)


# ---------------------------------------------------------------------------
# 2. Canonical structure — exactly one IR container, one instruction type
# ---------------------------------------------------------------------------


class TestCanonicalStructure:
    """The only canonical container is Circuit; the only instruction type is Operation."""

    def test_circuit_is_the_canonical_container(self):
        c = Circuit(1)
        assert isinstance(c, Circuit)

    def test_operations_list_contains_operation_instances(self):
        c = Circuit(1)
        c.h(0)
        for op in c.operations:
            assert isinstance(op, Operation), f"Expected Operation, got {type(op)}"

    def test_no_duplicate_ir_classes_exported(self):
        """__all__ must not expose classes that shadow Circuit or Operation."""
        all_names = set(rqm_compiler.__all__)
        # Circuit and Operation are the canonical IR classes
        assert "Circuit" in all_names
        assert "Operation" in all_names
        # Sanity: no 'Gate', 'Instruction', 'Node', or other IR synonyms
        forbidden_synonyms = {"Gate", "Instruction", "Node", "GateOp", "Qubit"}
        leaking = all_names & forbidden_synonyms
        assert not leaking, f"Unexpected IR synonym(s) in __all__: {leaking}"

    def test_compiled_circuit_is_not_an_alternative_ir(self):
        """CompiledCircuit is a result wrapper, not a circuit builder."""
        c = Circuit(1)
        c.h(0)
        compiled = compile_circuit(c)
        # CompiledCircuit wraps descriptors; it is NOT a Circuit subclass
        assert not isinstance(compiled, Circuit)
        assert isinstance(compiled, CompiledCircuit)


# ---------------------------------------------------------------------------
# 3. No backend leakage
# ---------------------------------------------------------------------------


class TestNoBackendLeakage:
    """rqm_compiler must not import qiskit, braket, or any vendor execution library."""

    _FORBIDDEN_PREFIXES = ("qiskit", "braket", "amazon", "cirq", "pennylane", "pyquil")

    def _collect_rqm_compiler_modules(self) -> list[str]:
        """Return all submodule names loaded under rqm_compiler."""
        import rqm_compiler as _pkg

        modules = []
        for importer, modname, ispkg in pkgutil.walk_packages(
            path=_pkg.__path__,
            prefix=_pkg.__name__ + ".",
        ):
            modules.append(modname)
        return modules

    def test_no_qiskit_in_sys_modules_after_import(self):
        """Importing rqm_compiler must not pull qiskit into sys.modules."""
        import rqm_compiler  # noqa: F401 — ensure it's imported

        loaded = [m for m in sys.modules if m.startswith("qiskit")]
        assert not loaded, f"qiskit modules found in sys.modules: {loaded}"

    def test_no_braket_in_sys_modules_after_import(self):
        import rqm_compiler  # noqa: F401

        loaded = [m for m in sys.modules if m.startswith("braket")]
        assert not loaded, f"braket modules found in sys.modules: {loaded}"

    def test_no_forbidden_top_level_imports_in_package_source(self):
        """
        Walk every rqm_compiler submodule and assert that none of the
        FORBIDDEN_PREFIXES appear as imports.

        This test imports each submodule and inspects sys.modules, ensuring
        the package is fully self-contained.
        """
        module_names = self._collect_rqm_compiler_modules()
        for mod_name in module_names:
            importlib.import_module(mod_name)

        leaked = [
            m
            for m in sys.modules
            if any(m.startswith(prefix) for prefix in self._FORBIDDEN_PREFIXES)
        ]
        assert not leaked, f"Backend modules leaked into rqm_compiler: {leaked}"

    def test_rqm_compiler_has_no_backend_dependency_in_pyproject(self):
        """
        pyproject.toml must not list qiskit, braket, or vendor SDKs as
        project dependencies.
        """
        import pathlib
        import re

        pyproject = pathlib.Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        for prefix in self._FORBIDDEN_PREFIXES:
            assert not re.search(
                rf"\b{re.escape(prefix)}\b", content, re.IGNORECASE
            ), f"Found backend dependency '{prefix}' in pyproject.toml"


# ---------------------------------------------------------------------------
# 4. API discipline — Tier 1 / Tier 2 structure
# ---------------------------------------------------------------------------


class TestAPIDiscipline:
    """Public __all__ exposes exactly the expected Tier 1 and Tier 2 symbols."""

    # Tier 1 — stable build API
    TIER1_SYMBOLS = {"Circuit", "Operation"}

    # Tier 2 — experimental transformation API (entry-point functions only)
    TIER2_SYMBOLS = {"compile_circuit", "optimize_circuit"}

    # Return types for Tier 2 functions — importable for type-hinting
    TIER2_RESULT_TYPES = {"CompiledCircuit", "CompilerReport"}

    # Additional exposed constants / exceptions (subject to change; Tier 3)
    ADDITIONAL_SYMBOLS = {"OPTIMIZATION_PIPELINE", "cancel_2q_pass", "CircuitValidationError"}

    def test_tier1_symbols_in_public_api(self):
        all_names = set(rqm_compiler.__all__)
        missing = self.TIER1_SYMBOLS - all_names
        assert not missing, f"Tier 1 symbols missing from __all__: {missing}"

    def test_tier2_symbols_in_public_api(self):
        all_names = set(rqm_compiler.__all__)
        missing = self.TIER2_SYMBOLS - all_names
        assert not missing, f"Tier 2 symbols missing from __all__: {missing}"

    def test_tier2_result_types_in_public_api(self):
        """Return types for Tier 2 functions must be importable (for type-hinting)."""
        all_names = set(rqm_compiler.__all__)
        missing = self.TIER2_RESULT_TYPES - all_names
        assert not missing, f"Tier 2 result types missing from __all__: {missing}"

    def test_tier1_circuit_is_importable_directly(self):
        from rqm_compiler import Circuit as C
        assert C is Circuit

    def test_tier1_operation_is_importable_directly(self):
        from rqm_compiler import Operation as O
        assert O is Operation

    def test_tier2_compile_circuit_is_callable(self):
        from rqm_compiler import compile_circuit as cc
        assert callable(cc)

    def test_tier2_optimize_circuit_is_callable(self):
        from rqm_compiler import optimize_circuit as oc
        assert callable(oc)

    def test_tier2_compile_circuit_returns_compiled_circuit(self):
        c = Circuit(1)
        c.h(0)
        result = compile_circuit(c)
        assert isinstance(result, CompiledCircuit)

    def test_tier2_optimize_circuit_returns_circuit_and_report(self):
        c = Circuit(1)
        c.h(0)
        result = optimize_circuit(c)
        assert isinstance(result, tuple) and len(result) == 2
        out_circuit, out_report = result
        assert isinstance(out_circuit, Circuit)
        assert isinstance(out_report, CompilerReport)

    def test_tier1_circuit_usable_without_tier2(self):
        """Building and exporting a circuit must not require compile_circuit."""
        c = Circuit(2)
        c.h(0).cx(0, 1).measure_all()
        descriptors = c.to_descriptors()
        assert len(descriptors) == 4  # h, cx, measure(0), measure(1)


# ---------------------------------------------------------------------------
# 5. Round-trip sanity: Circuit → operations → same descriptor structure
# ---------------------------------------------------------------------------


class TestRoundTripSanity:
    """Circuit → list[Operation] → descriptors matches original descriptors."""

    def test_operations_roundtrip_bell(self):
        c = Circuit(2)
        c.h(0).cx(0, 1).measure(0, key="m0").measure(1, key="m1")
        original = c.to_descriptors()

        # Reconstruct from the operations list
        c2 = Circuit(c.num_qubits)
        for op in c.operations:
            c2.add(op)
        assert c2.to_descriptors() == original

    def test_operations_roundtrip_parametric(self):
        c = Circuit(1)
        c.rx(0, 1.23).ry(0, 0.45).rz(0, 0.78)
        original = c.to_descriptors()

        c2 = Circuit(c.num_qubits)
        for op in c.operations:
            c2.add(op)
        assert c2.to_descriptors() == original

    def test_descriptor_roundtrip_via_from_descriptor(self):
        c = Circuit(2)
        c.h(0).cx(0, 1).measure_all()
        for d in c.to_descriptors():
            op = Operation.from_descriptor(d)
            assert op.to_descriptor() == d

    def test_compile_circuit_output_is_stable(self):
        c = Circuit(2)
        c.h(0).cx(0, 1).measure_all()
        d1 = compile_circuit(c).descriptors
        d2 = compile_circuit(c).descriptors
        assert d1 == d2


# ---------------------------------------------------------------------------
# 6. measure_all convenience method
# ---------------------------------------------------------------------------


class TestMeasureAll:
    """Circuit.measure_all() is a Tier-1 convenience that measures every qubit."""

    def test_measure_all_single_qubit(self):
        c = Circuit(1)
        c.measure_all()
        ops = c.operations
        assert len(ops) == 1
        assert ops[0].gate == "measure"
        assert ops[0].targets == [0]
        assert ops[0].params["key"] == "m0"

    def test_measure_all_three_qubits(self):
        c = Circuit(3)
        c.measure_all()
        ops = c.operations
        assert len(ops) == 3
        for i, op in enumerate(ops):
            assert op.gate == "measure"
            assert op.targets == [i]
            assert op.params["key"] == f"m{i}"

    def test_measure_all_returns_self(self):
        c = Circuit(2)
        result = c.measure_all()
        assert result is c

    def test_measure_all_is_chainable(self):
        c = Circuit(2)
        c.h(0).cx(0, 1).measure_all()
        gates = [op.gate for op in c.operations]
        assert gates == ["h", "cx", "measure", "measure"]

    def test_measure_all_compiles_cleanly(self):
        c = Circuit(2)
        c.h(0).cx(0, 1).measure_all()
        compiled = compile_circuit(c)
        assert compiled.num_qubits == 2
        measure_ops = [d for d in compiled.descriptors if d["gate"] == "measure"]
        assert len(measure_ops) == 2
