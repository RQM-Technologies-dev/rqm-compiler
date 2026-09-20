"""Compiler gate-to-quaternion adaptation; canonical algebra stays in rqm-core."""
from rqm_core import Quaternion
from .passes.to_u1q import _gate_to_quaternion


def operation_quaternion(op):
    values=tuple(op.params[x] for x in ('w','x','y','z')) if op.gate=='u1q' else _gate_to_quaternion(op.gate,op.params)
    return Quaternion(*values)


def local_pauli_expansions(op, cutoff=1e-13):
    """Coefficients of U† P U, without materializing U or P matrices."""
    inverse=operation_quaternion(op).conjugate()
    out={'I':[('I',1.+0j)]}
    for label,axis in zip('XYZ',((1,0,0),(0,1,0),(0,0,1))):
        values=inverse.rotate_vector(axis)
        out[label]=[(p,complex(v)) for p,v in zip('XYZ',values) if abs(v)>cutoff]
    return out


def prepared_coefficients(operations):
    """I/X/Y/Z coefficients of a locally prepared |0> density operator."""
    q=Quaternion.identity()
    for op in operations:q=operation_quaternion(op)*q
    return (1.,*q.rotate_vector((0.,0.,1.)))


def observable_coefficients(label, operations):
    """Coefficients of the requested Pauli in its final local measurement frame."""
    if label=='I':return (1.,0.,0.,0.)
    q=Quaternion.identity()
    for op in operations:q=operation_quaternion(op)*q
    axis={'X':(1,0,0),'Y':(0,1,0),'Z':(0,0,1)}[label]
    return (0.,*q.conjugate().rotate_vector(axis))
