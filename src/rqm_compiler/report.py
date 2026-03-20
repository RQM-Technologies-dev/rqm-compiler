"""
rqm_compiler.report
~~~~~~~~~~~~~~~~~~~
Compiler report/result object produced by optimization passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CompilerReport:
    """Summary produced by :func:`~rqm_compiler.compile.optimize_circuit`.

    Attributes:
        original_gate_count: Number of operations in the input circuit.
        optimized_gate_count: Number of operations in the optimized circuit.
        original_depth: Circuit depth of the input circuit.
        optimized_depth: Circuit depth of the optimized circuit.
        passes_applied: Ordered list of pass names that were applied.
        equivalence_verified: ``True`` if the optimizer verified semantic
            equivalence between the input and output circuits.
    """

    original_gate_count: int
    optimized_gate_count: int
    original_depth: int
    optimized_depth: int
    passes_applied: list[str] = field(default_factory=list)
    equivalence_verified: bool = False

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
            f"passes={self.passes_applied})"
        )
