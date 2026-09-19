import pytest
from rqm_compiler import Circuit, compile_representation_aware, evaluate_observable, evaluate_observables
from rqm_compiler.frontier import plan_frontier, evaluate_frontier


def interleaved():
    c=Circuit(5).ry(3,.41)
    for q in (0,1,2,4):c.rxx(3,q,.29).ry(3,.31).cx(q,3)
    return c


def test_frontier_rejects_before_numeric_allocation(monkeypatch):
    import rqm_compiler.frontier as f
    p=plan_frontier(interleaved(), 'XXXXX', 1)
    assert not p.accepted and p.width==2
    monkeypatch.setattr(f,'_operation_matrix',lambda *a:pytest.fail('matrix allocated'))
    with pytest.raises(ValueError,match='Rejected'):evaluate_frontier(p,'XXXXX')


def test_local_query_discards_disconnected_component():
    c=Circuit(8).ry(0,.2)
    for q in range(1,8):
        for t in range(q+1,8):c.cx(q,t)
    p=plan_frontier(c,'ZIIIIIII',1)
    assert p.accepted and p.width==1 and p.support=={0}
    import math
    assert abs(evaluate_frontier(p,'ZIIIIIII')-math.cos(.2))<1e-12


def test_batch_reuses_only_matching_support_and_digest():
    compiled=compile_representation_aware(interleaved())
    results=evaluate_observables(compiled,['XXXXX','YYYYY','ZIIII'])
    assert results[0].method=='bounded_frontier_transfer'
    assert not results[0].plan_reused and results[1].plan_reused
    assert not results[2].plan_reused
    def queries():
        yield 'XXXXX'
        compiled.circuit.rx(0,.73)
        yield 'YYYYY'
    changed=evaluate_observables(compiled,queries())
    assert not changed[1].plan_reused
    reference=evaluate_observable(compiled.circuit,'YYYYY')
    assert abs(reference.value-changed[1].value)<1e-12


@pytest.mark.parametrize('cap',[-1,True,1.5])
def test_invalid_frontier_budget(cap):
    with pytest.raises(ValueError):evaluate_observable(Circuit(2),'ZZ',max_frontier_qubits=cap)
