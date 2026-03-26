"""
rqm_compiler
~~~~~~~~~~~~
Backend-neutral optimization and rewriting engine for the RQM quantum ecosystem.

rqm-compiler is the internal compiler layer that sits between the canonical
external circuit IR (rqm-circuits) and backend execution bridges
(rqm-qiskit, rqm-braket).  Typical flow::

    rqm-circuits payload → bridge/import → rqm-compiler optimization → backend lowering

Public API::

    from rqm_compiler import Circuit, Operation, optimize_circuit

    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure_all()

    # Tier 2 — preferred entry point: optimize then export to backend
    optimized, report = optimize_circuit(c)
    print(report)
    print(optimized.to_descriptors())  # internal compiler descriptor format

    # Tier 2 — lightweight compile (no optimization)
    from rqm_compiler import compile_circuit
    compiled = compile_circuit(c)
    print(compiled.descriptors)  # internal compiler descriptor format

    # Reconstruct a compiler circuit from internal descriptors
    restored = Circuit.from_descriptors(compiled.descriptors, num_qubits=c.num_qubits)
"""

from importlib.metadata import PackageNotFoundError, version

from .circuit import Circuit
from .compile import (
    OPTIMIZATION_PIPELINE,
    CompiledCircuit,
    compile_circuit,
    optimize_circuit,
)
from .ops import Operation
from .passes.cancel_2q import cancel_2q_pass
from .report import CompilerReport
from .validate import CircuitValidationError

__all__ = [
    "Circuit",
    "Operation",
    "CompiledCircuit",
    "CompilerReport",
    "OPTIMIZATION_PIPELINE",
    "cancel_2q_pass",
    "compile_circuit",
    "optimize_circuit",
    "CircuitValidationError",
]

try:
    __version__ = version("rqm-compiler")
except PackageNotFoundError:
    __version__ = "unknown"
