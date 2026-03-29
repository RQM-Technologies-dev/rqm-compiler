"""
rqm_compiler.report
~~~~~~~~~~~~~~~~~~~
Compiler report/result object produced by optimization passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
