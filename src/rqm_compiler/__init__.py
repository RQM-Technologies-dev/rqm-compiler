"""
rqm_compiler
~~~~~~~~~~~~
Backend-neutral circuit compiler for the RQM quantum ecosystem.

Public API::

    from rqm_compiler import Circuit, Operation, compile_circuit

    c = Circuit(2)
    c.h(0)
    c.cx(0, 1)
    c.measure(0, key="m0")
    c.measure(1, key="m1")

    compiled = compile_circuit(c)
    print(compiled.descriptors)
"""

from importlib.metadata import PackageNotFoundError, version

from .circuit import Circuit
from .compile import CompiledCircuit, compile_circuit
from .ops import Operation
from .validate import CircuitValidationError

__all__ = [
    "Circuit",
    "Operation",
    "CompiledCircuit",
    "compile_circuit",
    "CircuitValidationError",
]

try:
    __version__ = version("rqm-compiler")
except PackageNotFoundError:
    __version__ = "unknown"
