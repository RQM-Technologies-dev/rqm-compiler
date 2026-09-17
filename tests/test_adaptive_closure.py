from rqm_compiler import Circuit
from rqm_compiler.adaptive_closure import account_closed_representation, minimal_representation


def test_local_quaternion_accounting_is_representation_owned():
    circuit = Circuit(2)
    circuit.h(0).t(1)
    result = account_closed_representation(circuit)
    assert result.minimum_closed_representation_size == 8
    assert result.representation_histogram == {"local_quaternion": 2}
    assert result.exact_within_scope is True
    assert result.quantum_state_dimension_claim is False


def test_axis_hinge_is_smaller_than_general_structured_block():
    circuit = Circuit(2)
    circuit.rxx(0, 1, 0.25)
    result = account_closed_representation(circuit)
    assert result.minimum_closed_representation_size == 2
    assert result.representation_trajectory == ("axis_hinge",)
    assert result.maximum_representation_level == 3


def test_native_two_qubit_gate_is_conservatively_cartan():
    circuit = Circuit(2)
    circuit.cx(0, 1)
    result = account_closed_representation(circuit)
    assert result.minimum_closed_representation_size == 3
    assert result.representation_trajectory == ("cartan_relation",)


def test_metric_does_not_depend_on_descriptor_leaf_count():
    a = Circuit(2)
    a.rzz(0, 1, 0.125)
    b = Circuit(2)
    b.rzz(0, 1, 1.23456789)
    assert (
        account_closed_representation(a).minimum_closed_representation_size
        == account_closed_representation(b).minimum_closed_representation_size
        == 2
    )
