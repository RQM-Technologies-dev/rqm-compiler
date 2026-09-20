"""Validation must not depend on a query's selected representation or cost."""
import pytest
from dataclasses import replace

from rqm_compiler import Circuit, Operation, compile_representation_aware, evaluate_observable, plan_and_evaluate
from rqm_compiler.observables import expectation_pauli
from rqm_compiler.structured_observables import expectation_structured
from rqm_compiler.stable_prototype import expectation_stable
from rqm_compiler.validate import validate_circuit, validate_descriptor


def compiled_query(circuit, pauli, *, max_terms=100000):
    # Deliberately replace a valid compiled object's circuit to verify that the
    # query boundary validates too, rather than relying on prior compilation.
    compiled = compile_representation_aware(Circuit(circuit.num_qubits))
    compiled = replace(compiled, circuit=circuit)
    return plan_and_evaluate(compiled, pauli, max_terms=max_terms)


EVALUATORS = [evaluate_observable, compiled_query, expectation_stable,
              expectation_structured, expectation_pauli]


@pytest.mark.parametrize('evaluate', EVALUATORS)
@pytest.mark.parametrize('closed', [False, True])
@pytest.mark.parametrize('label', ['', 'Z', 'ZZZ', 'QI', 'zI', ' I', ['XX', 'I'], ['I', None], None, 7])
def test_invalid_labels_rejected_before_routing(evaluate, closed, label):
    c = Circuit(2)
    if closed:
        c.rxx(0, 1, .3)
    with pytest.raises((ValueError, TypeError)):
        evaluate(c, label)


@pytest.mark.parametrize('evaluate', EVALUATORS)
@pytest.mark.parametrize('budget', [0, -1, True, 1.5, float('nan'), float('inf'), '1', None])
@pytest.mark.parametrize('label', ['II', 'ZZ', 'XY'])
def test_invalid_budgets_rejected_even_for_trivial_queries(evaluate, budget, label):
    with pytest.raises((ValueError, TypeError), match='max_terms'):
        evaluate(Circuit(2), label, max_terms=budget)


INVALID_OPERATIONS = [
    Operation(gate, targets, params={'angle': value})
    for gate, targets in [('rx', [0]), ('ry', [0]), ('rz', [0]), ('phaseshift', [0]),
                          ('rxx', [0, 1]), ('ryy', [0, 1]), ('rzz', [0, 1])]
    for value in (float('nan'), float('inf'), True, '0.3', None, .3j)
] + [
    Operation('u1q', [0], params={'w': value, 'x': 0., 'y': 0., 'z': 0.})
    for value in (float('nan'), float('inf'), True, '1', 0., 2., 1e308)
] + [
    Operation('x', [-1]), Operation('x', [2]), Operation('x', [.5]), Operation('x', [True]),
    Operation('x', []), Operation('x', [0, 1]), Operation('rxx', [0, 0], params={'angle': .3}),
    Operation('cx', [0], [0]), Operation('cx', [1]), Operation('h', [0], [1]),
    Operation('rxx', [0, 1]), Operation('reset', [0]), Operation('unknown', [0]),
]


@pytest.mark.parametrize('operation', INVALID_OPERATIONS)
def test_invalid_operations_rejected_at_every_boundary(operation):
    c = Circuit(2).add(operation)
    for action in (lambda: validate_circuit(c), lambda: compile_representation_aware(c),
                   lambda: validate_descriptor(operation.to_descriptor(), num_qubits=2)):
        with pytest.raises((ValueError, TypeError)):
            action()
    for evaluate in EVALUATORS:
        with pytest.raises((ValueError, TypeError)):
            evaluate(c, 'ZI')


@pytest.mark.parametrize('evaluate', EVALUATORS)
@pytest.mark.parametrize('position', [0, 1, 2])
def test_keyed_measurement_valid_ir_but_not_unitary_query(evaluate, position):
    operations = Circuit(2).h(0).cx(0, 1).operations
    operations.insert(position, Operation('measure', [0], params={'key': 'm'}))
    c = Circuit(2)
    for operation in operations:
        c.add(operation)
    validate_circuit(c)
    with pytest.raises(ValueError, match='unitary'):
        evaluate(c, 'II', max_terms=1)


@pytest.mark.parametrize('evaluate', EVALUATORS)
@pytest.mark.parametrize('position', [0, 1, 2])
@pytest.mark.parametrize('targets', [[], [0], [0, 1]])
def test_barriers_are_query_neutral_and_preserved(evaluate, position, targets):
    operations = Circuit(2).h(0).cx(0, 1).operations
    operations.insert(position, Operation('barrier', targets))
    c = Circuit(2)
    for operation in operations:
        c.add(operation)
    before = c.to_descriptors()
    result = evaluate(c, 'ZZ')
    assert abs(result.value - 1.) < 1e-12
    assert c.to_descriptors() == before
    compiled = compile_representation_aware(c)
    assert any(op.gate == 'barrier' for op in compiled.circuit.operations)


@pytest.mark.parametrize('evaluate', EVALUATORS)
def test_one_shot_iterable_materialized_once(evaluate):
    result = evaluate(Circuit(2).h(0).cx(0, 1), iter(['X', 'X']))
    assert abs(result.value - 1.) < 1e-12
