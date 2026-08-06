"""
rqm_compiler.report
~~~~~~~~~~~~~~~~~~~
Compiler report/result object produced by optimization passes.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


def _copy_report_value(value: Any) -> Any:
    """Copy a JSON-shaped report value without dataclass reflection overhead."""

    value_type = type(value)
    if value is None or value_type in (str, int, float, bool):
        return value
    if value_type is dict:
        return {
            _copy_report_value(key): _copy_report_value(item)
            for key, item in value.items()
        }
    if value_type is list:
        return [_copy_report_value(item) for item in value]
    if value_type is tuple:
        return tuple(_copy_report_value(item) for item in value)
    # Preserve the historical ``asdict`` behavior for any future uncommon
    # value type instead of returning a live reference.
    return copy.deepcopy(value)


@dataclass
class CompilerReport:
    """Summary produced by :func:`~rqm_compiler.compile.optimize_circuit`.

    Attributes:
        original_gate_count: Number of operations in the input circuit.
        optimized_gate_count: Number of operations in the optimized circuit.
        original_depth: Circuit depth of the input circuit.
        optimized_depth: Circuit depth of the optimized circuit.
        passes_applied: Ordered list of pass names that were committed.
            If optimization falls back to the original circuit, this list is empty.
        equivalence_status: Semantic equivalence status of the returned circuit.
            For fail-closed optimization this is always ``VERIFIED``.
        equivalence_report: Full semantic equivalence report payload for the
            committed output.
        equivalence_verified: Backward-compatible summary; ``True`` for the
            fail-closed committed output.
        equivalence_guaranteed: Explicit proof-gated guarantee for the returned
            circuit.
        optimization_applied: Whether an optimized candidate was verified and
            committed.
        fallback_reason: Optional machine-readable fallback reason when
            optimization was withheld.
    """

    original_gate_count: int
    optimized_gate_count: int
    original_depth: int
    optimized_depth: int
    passes_applied: list[str] = field(default_factory=list)
    equivalence_status: str = "VERIFIED"
    equivalence_report: dict[str, Any] | None = None
    equivalence_verified: bool = True
    equivalence_guaranteed: bool = True
    optimization_applied: bool = False
    fallback_reason: str | None = None
    su4q_candidates: list[dict[str, Any]] = field(default_factory=list)
    nonlocal_fingerprints: list[str] = field(default_factory=list)
    weyl_classes: list[str] = field(default_factory=list)
    candidate_reconstruction_errors: list[float] = field(default_factory=list)
    candidate_original_operation_ranges: list[list[int]] = field(default_factory=list)
    selected_two_qubit_strategy: str = "original_operations"
    adaptive_routing: dict[str, Any] = field(default_factory=dict)
    stage_timings_ns: dict[str, int] = field(default_factory=dict)

    @property
    def gate_count_delta(self) -> int:
        """Reduction in gate count (positive means fewer gates after optimization)."""
        return self.original_gate_count - self.optimized_gate_count

    @property
    def depth_delta(self) -> int:
        """Reduction in depth (positive means shallower circuit after optimization)."""
        return self.original_depth - self.optimized_depth

    def __repr__(self) -> str:
        return (
            f"CompilerReport("
            f"gates: {self.original_gate_count}->{self.optimized_gate_count}, "
            f"depth: {self.original_depth}->{self.optimized_depth}, "
            f"equivalence_status={self.equivalence_status}, "
            f"passes={self.passes_applied})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation of the compiler report."""

        return {
            "original_gate_count": self.original_gate_count,
            "optimized_gate_count": self.optimized_gate_count,
            "original_depth": self.original_depth,
            "optimized_depth": self.optimized_depth,
            "passes_applied": list(self.passes_applied),
            "equivalence_status": self.equivalence_status,
            "equivalence_report": _copy_report_value(self.equivalence_report),
            "equivalence_verified": self.equivalence_verified,
            "equivalence_guaranteed": self.equivalence_guaranteed,
            "optimization_applied": self.optimization_applied,
            "fallback_reason": self.fallback_reason,
            "su4q_candidates": _copy_report_value(self.su4q_candidates),
            "nonlocal_fingerprints": list(self.nonlocal_fingerprints),
            "weyl_classes": list(self.weyl_classes),
            "candidate_reconstruction_errors": list(
                self.candidate_reconstruction_errors
            ),
            "candidate_original_operation_ranges": _copy_report_value(
                self.candidate_original_operation_ranges
            ),
            "selected_two_qubit_strategy": self.selected_two_qubit_strategy,
            "adaptive_routing": _copy_report_value(self.adaptive_routing),
            "stage_timings_ns": dict(self.stage_timings_ns),
        }
