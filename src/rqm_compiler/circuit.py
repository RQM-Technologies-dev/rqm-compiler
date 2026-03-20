"""
rqm_compiler.circuit
~~~~~~~~~~~~~~~~~~~~
Canonical circuit container with builder convenience API.
"""

from __future__ import annotations

import math
from typing import Any

from .ops import Operation


class Circuit:
    """A backend-neutral quantum circuit.

    Args:
        num_qubits: The number of qubits in the circuit.
        metadata: Optional dictionary of user-defined circuit metadata.  The
            compiler preserves this dictionary through all passes and
            propagates it to the optimized output circuit.

    Example::

        from rqm_compiler import Circuit

        c = Circuit(2)
        c.h(0)
        c.cx(0, 1)
        c.measure(0, key="m0")
        c.measure(1, key="m1")

        descriptors = c.to_descriptors()
    """

    def __init__(self, num_qubits: int, *, metadata: dict[str, Any] | None = None) -> None:
        if num_qubits < 1:
            raise ValueError(f"num_qubits must be >= 1, got {num_qubits}")
        self._num_qubits: int = num_qubits
        self._ops: list[Operation] = []
        self.metadata: dict[str, Any] = dict(metadata) if metadata is not None else {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def num_qubits(self) -> int:
        """Number of qubits in this circuit."""
        return self._num_qubits

    @property
    def operations(self) -> list[Operation]:
        """Ordered list of :class:`~rqm_compiler.ops.Operation` objects."""
        return list(self._ops)

    # ------------------------------------------------------------------
    # Core mutation
    # ------------------------------------------------------------------

    def add(self, op: Operation) -> "Circuit":
        """Append an :class:`~rqm_compiler.ops.Operation` to the circuit.

        Args:
            op: The operation to append.

        Returns:
            ``self`` to allow method chaining.
        """
        if not isinstance(op, Operation):
            raise TypeError(f"Expected Operation, got {type(op).__name__}")
        self._ops.append(op)
        return self

    # ------------------------------------------------------------------
    # Export / import
    # ------------------------------------------------------------------

    def to_descriptors(self) -> list[dict[str, Any]]:
        """Export the circuit as a list of canonical descriptor dictionaries."""
        return [op.to_descriptor() for op in self._ops]

    @classmethod
    def from_descriptors(
        cls,
        descriptors: list[dict[str, Any]],
        num_qubits: int,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> "Circuit":
        """Construct a :class:`Circuit` from a list of canonical descriptor dicts.

        This is the inverse of :meth:`to_descriptors`.  It is useful for API
        ingestion, backend-to-compiler roundtrips, debugging, and
        reproducibility.

        Args:
            descriptors: Ordered list of canonical descriptor dictionaries, each
                with keys ``"gate"``, ``"targets"``, ``"controls"``, and
                ``"params"``.
            num_qubits: Number of qubits in the resulting circuit.
            metadata: Optional metadata dictionary to attach to the circuit.
                Defaults to ``None``, which results in an empty ``{}`` metadata
                dict on the returned circuit (same behaviour as
                ``Circuit(num_qubits)`` with no *metadata* argument).

        Returns:
            A new :class:`Circuit` containing one :class:`~rqm_compiler.ops.Operation`
            per descriptor, in order.

        Example::

            descriptors = [
                {"gate": "h",  "targets": [0], "controls": [], "params": {}},
                {"gate": "cx", "targets": [1], "controls": [0], "params": {}},
            ]
            c = Circuit.from_descriptors(descriptors, num_qubits=2)
        """
        circuit = cls(num_qubits, metadata=metadata)
        for descriptor in descriptors:
            circuit.add(Operation.from_descriptor(descriptor))
        return circuit

    # ------------------------------------------------------------------
    # Builder convenience API — single-qubit no-parameter gates
    # ------------------------------------------------------------------

    def _single(self, gate: str, qubit: int) -> "Circuit":
        return self.add(Operation(gate=gate, targets=[qubit]))

    def i(self, qubit: int) -> "Circuit":
        """Identity gate on *qubit*."""
        return self._single("i", qubit)

    def x(self, qubit: int) -> "Circuit":
        """Pauli-X gate on *qubit*."""
        return self._single("x", qubit)

    def y(self, qubit: int) -> "Circuit":
        """Pauli-Y gate on *qubit*."""
        return self._single("y", qubit)

    def z(self, qubit: int) -> "Circuit":
        """Pauli-Z gate on *qubit*."""
        return self._single("z", qubit)

    def h(self, qubit: int) -> "Circuit":
        """Hadamard gate on *qubit*."""
        return self._single("h", qubit)

    def s(self, qubit: int) -> "Circuit":
        """S gate on *qubit*."""
        return self._single("s", qubit)

    def t(self, qubit: int) -> "Circuit":
        """T gate on *qubit*."""
        return self._single("t", qubit)

    # ------------------------------------------------------------------
    # Builder convenience API — single-qubit parameterised gates
    # ------------------------------------------------------------------

    def rx(self, qubit: int, angle: float) -> "Circuit":
        """Rotation around X-axis by *angle* radians."""
        return self.add(Operation(gate="rx", targets=[qubit], params={"angle": angle}))

    def ry(self, qubit: int, angle: float) -> "Circuit":
        """Rotation around Y-axis by *angle* radians."""
        return self.add(Operation(gate="ry", targets=[qubit], params={"angle": angle}))

    def rz(self, qubit: int, angle: float) -> "Circuit":
        """Rotation around Z-axis by *angle* radians."""
        return self.add(Operation(gate="rz", targets=[qubit], params={"angle": angle}))

    def phaseshift(self, qubit: int, angle: float) -> "Circuit":
        """Phase-shift gate by *angle* radians."""
        return self.add(Operation(gate="phaseshift", targets=[qubit], params={"angle": angle}))

    def u1q(self, qubit: int, w: float, x: float, y: float, z: float) -> "Circuit":
        """General single-qubit gate in quaternion form.

        The parameters *w*, *x*, *y*, *z* are the components of a unit quaternion
        ``q = w + x·i + y·j + z·k`` satisfying ``w² + x² + y² + z² = 1``.  This
        quaternion uniquely identifies an element of SU(2), which backend translators
        use to construct the corresponding unitary matrix.

        Args:
            qubit: Target qubit index.
            w: Real (scalar) component of the unit quaternion.
            x: i-component of the unit quaternion.
            y: j-component of the unit quaternion.
            z: k-component of the unit quaternion.
        """
        return self.add(
            Operation(gate="u1q", targets=[qubit], params={"w": w, "x": x, "y": y, "z": z})
        )

    # ------------------------------------------------------------------
    # Builder convenience API — two-qubit gates
    # ------------------------------------------------------------------

    def cx(self, control: int, target: int) -> "Circuit":
        """CNOT (controlled-X) gate."""
        return self.add(Operation(gate="cx", targets=[target], controls=[control]))

    def cy(self, control: int, target: int) -> "Circuit":
        """Controlled-Y gate."""
        return self.add(Operation(gate="cy", targets=[target], controls=[control]))

    def cz(self, control: int, target: int) -> "Circuit":
        """Controlled-Z gate."""
        return self.add(Operation(gate="cz", targets=[target], controls=[control]))

    def swap(self, qubit_a: int, qubit_b: int) -> "Circuit":
        """SWAP gate between *qubit_a* and *qubit_b*."""
        return self.add(Operation(gate="swap", targets=[qubit_a, qubit_b]))

    def iswap(self, qubit_a: int, qubit_b: int) -> "Circuit":
        """iSWAP gate between *qubit_a* and *qubit_b*."""
        return self.add(Operation(gate="iswap", targets=[qubit_a, qubit_b]))

    # ------------------------------------------------------------------
    # Builder convenience API — measurement and barrier
    # ------------------------------------------------------------------

    def measure(self, qubit: int, *, key: str | None = None) -> "Circuit":
        """Measurement on *qubit*.

        Args:
            qubit: The qubit to measure.
            key: Optional classical register key (defaults to ``"m{qubit}"``).
        """
        resolved_key = key if key is not None else f"m{qubit}"
        return self.add(Operation(gate="measure", targets=[qubit], params={"key": resolved_key}))

    def measure_all(self) -> "Circuit":
        """Measure all qubits using default keys ``m0``, ``m1``, …

        This is a Tier-1 convenience wrapper that calls :meth:`measure` for
        every qubit in order.  Keys follow the convention ``"m{qubit}"``.

        Returns:
            ``self`` to allow method chaining.
        """
        for qubit in range(self._num_qubits):
            self.measure(qubit)
        return self

    def barrier(self, *qubits: int) -> "Circuit":
        """Barrier across *qubits* (or all qubits if none given)."""
        target_list = list(qubits) if qubits else list(range(self._num_qubits))
        return self.add(Operation(gate="barrier", targets=target_list))

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._ops)

    def __repr__(self) -> str:
        return f"Circuit(num_qubits={self._num_qubits}, ops={len(self._ops)})"
