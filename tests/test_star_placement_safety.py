"""Independent dense-oracle regressions for the direct-star placement boundary."""
import random

import numpy as np
import pytest

from rqm_compiler import Circuit, compile_representation_aware, evaluate_observable, plan_and_evaluate
from rqm_compiler.direct_readout import global_z_star


def _circuit(n, seed, placement):
    rng = random.Random(seed)
    c = Circuit(n)
    for q in range(n):
        c.ry(q, rng.uniform(-1.2, 1.2))
        c.rx(q, rng.uniform(-1.2, 1.2))
    for leaf in range(1, n):
        c.rxx(0, leaf, rng.uniform(-1.2, 1.2))
        if leaf == 1 and placement == 'inside':
            c.rz(leaf, .83)
        c.rzz(0, leaf, rng.uniform(-1.2, 1.2))
        c.cx(0, leaf)
        if leaf == 1 and placement == 'between':
            c.rz(0, .73)
    return c


def _dense_z(c):
    """Literal Pauli rotations and basis permutations; no compiler matrix helpers."""
    identity = np.eye(2, dtype=complex)
    paulis = {'x': np.array([[0, 1], [1, 0]], complex),
              'y': np.array([[0, -1j], [1j, 0]], complex),
              'z': np.diag([1., -1.])}
    size = 2 ** c.num_qubits
    state = np.zeros(size, complex)
    state[0] = 1
    for gate in c.operations:
        if gate.gate == 'cx':
            control, target = gate.controls[0], gate.targets[0]
            permutation = [i ^ (1 << target) if i & (1 << control) else i for i in range(size)]
            state = state[permutation]
        else:
            axis = gate.gate[1]
            matrix = np.ones((1, 1), complex)
            for q in reversed(range(c.num_qubits)):
                matrix = np.kron(matrix, paulis[axis] if q in gate.targets else identity)
            theta = gate.params['angle']
            state = np.cos(theta / 2) * state - 1j * np.sin(theta / 2) * (matrix @ state)
    parity = np.array([(-1) ** i.bit_count() for i in range(size)])
    return np.vdot(state, parity * state)


@pytest.mark.parametrize('n', [3, 4, 6])
@pytest.mark.parametrize('seed', [211, 307, 509])
@pytest.mark.parametrize('placement', ['inside', 'between'])
def test_interleaved_rz_uses_correct_fallback(n, seed, placement):
    c = _circuit(n, seed, placement)
    direct = global_z_star(c)
    assert not direct.available
    assert direct.reason == 'interleaved single-qubit gate'
    expected = _dense_z(c)
    compiled = compile_representation_aware(c)
    for result in (evaluate_observable(c, 'Z' * n), plan_and_evaluate(compiled, 'Z' * n)):
        assert result.available and result.exact
        assert result.method == 'general_pauli_promoted'
        assert abs(result.value - expected) < 1e-9
    assert compiled.report.query_fallback_used


@pytest.mark.parametrize('placement', ['inside', 'between'])
def test_unsafe_route_does_not_bypass_fallback_budget(placement):
    result = evaluate_observable(_circuit(4, 307, placement), 'ZZZZ', max_terms=1)
    assert not result.available
    assert result.method == 'structured_exact'
    assert result.reason


@pytest.mark.parametrize('final_rotations', [False, True])
def test_safe_three_phase_route_remains_correct(final_rotations):
    c = _circuit(4, 307, 'none')
    if final_rotations:
        for q in range(4):
            c.rz(q, .37)
    result = evaluate_observable(c, 'ZZZZ')
    assert result.available and result.exact
    assert result.method == 'direct_star_relational'
    assert abs(result.value - _dense_z(c)) < 1e-9


def test_conservatively_rejects_disjoint_interleaving():
    c = Circuit(3).rxx(0, 1, .2).rz(1, .3).rxx(0, 2, .4)
    assert not global_z_star(c).available


@pytest.mark.parametrize('gate', ['rx', 'ry', 'rz'])
@pytest.mark.parametrize('target', [0, 1, 2])
@pytest.mark.parametrize('position', range(13))
def test_every_rotation_insertion_position_matches_dense_oracle(gate, target, position):
    # A separate held-out seed; insert before, inside, between and after all
    # episodes, including on a qubit disjoint from the next interaction.
    from rqm_compiler.ops import Operation
    original = _circuit(3, 997, 'none')
    operations = list(original.operations)
    operations.insert(position, Operation(gate, [target], params={'angle': .713}))
    c = Circuit(3)
    for operation in operations:
        c.add(operation)
    if 6 < position < 12:
        assert not global_z_star(c).available
    expected = _dense_z(c)
    for result in (evaluate_observable(c, 'ZZZ'),
                   plan_and_evaluate(compile_representation_aware(c), 'ZZZ')):
        assert result.available and result.exact
        assert abs(result.value - expected) < 1e-9
