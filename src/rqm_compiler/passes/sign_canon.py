"""Normalize quaternion length while retaining its SU(2) sign.

The historical name is retained for compatibility. q and -q are distinct
composable operators; SO(3) sign folding requires explicit phase_invariant=True for terminal use.
"""
from ..circuit import Circuit
from ..normalize import normalize_quaternion
from ..ops import Operation

def sign_canon_pass(circuit: Circuit, *, phase_invariant: bool = False) -> Circuit:
    """Copy the circuit, normalizing eligible u1q gates without phase loss."""
    out = Circuit(circuit.num_qubits, metadata=dict(circuit.metadata))
    for op in circuit.operations:
        if op.gate == "u1q" and len(op.targets) == 1 and not op.controls:
            w, x, y, z = normalize_quaternion(
                op.params["w"], op.params["x"], op.params["y"], op.params["z"],
                allow_renormalization=True, canonicalize_sign=phase_invariant,
            )
            out.add(Operation(gate="u1q", targets=list(op.targets),
                              params={"w": w, "x": x, "y": y, "z": z}))
        else:
            out.add(op)
    return out
