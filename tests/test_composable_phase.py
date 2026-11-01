"""Exact SU(2) signs survive optimization and compiler JSON roundtrips."""
import json
import math
import pytest
from rqm_compiler import Circuit, optimize_circuit, compile_representation_aware
from rqm_compiler.verification import verify_equivalence, _circuit_unitary
from rqm_compiler.io import circuit_to_dict, circuit_from_dict

@pytest.mark.parametrize('axis', ['rx','ry','rz'])
@pytest.mark.parametrize('angles', [(2*math.pi,),(-2*math.pi,),(math.pi,math.pi),(2*math.pi,.17,-.17),(2*math.pi,-2*math.pi),(.23,-.11),(1e-8,2e-8)])
def test_rotation_composition_and_json_preserve_phase(axis,angles):
    c=Circuit(2)
    for a in angles:getattr(c,axis)(0,a)
    out,report=optimize_circuit(c)
    restored=circuit_from_dict(json.loads(json.dumps(circuit_to_dict(out))))
    proof=verify_equivalence(c,restored,atol=1e-10,rtol=0)
    assert proof.verified and not proof.phase_invariant
    assert report.equivalence_report['phase_invariant'] is False
    assert len(out)<=len(c)

@pytest.mark.parametrize('width',[1,2,3,4])
def test_representation_aware_dispatch_preserves_minus_identity(width):
    c=Circuit(width);c.rx(0,2*math.pi)
    out=compile_representation_aware(c).circuit
    assert verify_equivalence(c,out,max_dense_qubits=4,atol=1e-10,rtol=0).verified

def test_terminal_equivalence_requires_explicit_opt_in():
    c=Circuit(1);c.rx(0,2*math.pi);identity=Circuit(1)
    assert not verify_equivalence(c,identity).verified
    terminal=verify_equivalence(c,identity,phase_invariant=True)
    assert terminal.verified and terminal.phase_invariant

@pytest.mark.parametrize('gate', ['h','x','y','z','s','t','phaseshift'])
def test_named_u2_gates_keep_scalar_phase(gate):
    c=Circuit(1);getattr(c,gate)(0,*([.27] if gate=='phaseshift' else []));c.rx(0,.21)
    out,_=optimize_circuit(c)
    assert verify_equivalence(c,out,atol=1e-10,rtol=0).verified

def test_safe_noncommuting_composition_is_still_optimized():
    c=Circuit(1);c.rx(0,.12).ry(0,.23).rz(0,.34)
    out,report=optimize_circuit(c)
    assert len(out)==1 and report.optimization_applied
    assert verify_equivalence(c,out,atol=1e-10,rtol=0).verified

@pytest.mark.parametrize('axis',['rx','ry','rz'])
@pytest.mark.parametrize('angle',[2*math.pi,-2*math.pi,3*math.pi,.23])
def test_named_backend_export_preserves_signed_rotation(axis,angle):
    from rqm_compiler import lower_circuit_for_backend
    c=Circuit(1);getattr(c,axis)(0,angle)
    out,_=optimize_circuit(c)
    lowered=lower_circuit_for_backend(out,backend_family='braket_gate_model')
    assert verify_equivalence(c,lowered,atol=1e-10,rtol=0).verified

@pytest.mark.parametrize('axis', ['rx', 'ry', 'rz'])
@pytest.mark.parametrize('angle', [2*math.pi, -2*math.pi, 1e-8, .37])
def test_independent_pauli_formula_inverse_and_control_embedding(axis, angle):
    """Exact lift survives even where terminal ray equivalence would hide sign."""
    import numpy as np
    paulis = {
        'rx': np.array([[0, 1], [1, 0]], dtype=complex),
        'ry': np.array([[0, -1j], [1j, 0]], dtype=complex),
        'rz': np.diag([1, -1]).astype(complex),
    }
    expected = np.cos(angle/2)*np.eye(2)-1j*np.sin(angle/2)*paulis[axis]
    source = Circuit(1)
    getattr(source, axis)(0, angle)
    optimized, _ = optimize_circuit(source)
    actual = np.asarray(_circuit_unitary(optimized))
    assert np.max(np.abs(actual-expected)) < 1e-10
    inverse = Circuit(1)
    getattr(inverse, axis)(0, -angle)
    inv, _ = optimize_circuit(inverse)
    assert np.max(np.abs(np.asarray(_circuit_unitary(inv)) @ actual-np.eye(2))) < 1e-10
    controlled_actual = np.eye(4, dtype=complex)
    controlled_expected = np.eye(4, dtype=complex)
    controlled_actual[2:, 2:] = actual
    controlled_expected[2:, 2:] = expected
    assert np.max(np.abs(controlled_actual-controlled_expected)) < 1e-10
    if abs(angle) == 2*math.pi:
        assert np.max(np.abs(controlled_actual-np.eye(4))) > 1.9
