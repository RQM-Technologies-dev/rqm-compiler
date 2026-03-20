"""
rqm_compiler
~~~~~~~~~~~~
Backend-neutral circuit compiler for the RQM quantum ecosystem.

Public API::

    from rqm_compiler import Circuit, Operation, compile_circuit, optimize_circuit

    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0, key="m0")
    c.measure(1, key="m1")

    compiled = compile_circuit(c)
    print(compiled.descriptors)

    optimized, report = optimize_circuit(c)
    print(report)
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
