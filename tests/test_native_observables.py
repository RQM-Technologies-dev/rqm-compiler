import numpy as np
import pytest
from rqm_compiler import Circuit
from rqm_compiler.frontier import plan_frontier,evaluate_frontier
from rqm_compiler.local_observable import local_pauli_expansions
from rqm_compiler.su4_blocks import _single_qubit_matrix

P={'I':np.eye(2),'X':np.array([[0,1],[1,0]]),'Y':np.array([[0,-1j],[1j,0]]),'Z':np.diag([1,-1])}

@pytest.mark.parametrize('angle',[0.,1e-12,.43,-2.7,np.pi])
def test_quaternion_updates_against_dense_gate_oracle(angle):
    c=Circuit(1).h(0).s(0).t(0).x(0).y(0).z(0).rx(0,angle).ry(0,angle).rz(0,angle)
    for op in c.operations:
        u=_single_qubit_matrix(op)
        for label,terms in local_pauli_expansions(op).items():
            np.testing.assert_allclose(sum(v*P[p] for p,v in terms),u.conj().T@P[label]@u,atol=2e-13)

@pytest.mark.parametrize('seed',range(12))
def test_real_frontier_matches_dense_with_revisited_wires(seed):
    rng=np.random.default_rng(seed)
    c=Circuit(5)
    for q in range(5):c.ry(q,float(rng.normal()))
    for _ in range(15):
        a,b=map(int,rng.choice(5,2,replace=False))
        c.rx(a,float(rng.normal()))
        if rng.random()<.5:c.cx(a,b)
        else:getattr(c,rng.choice(['rxx','ryy','rzz']))(a,b,float(rng.normal()))
    labels=''.join(rng.choice(list('IXYZ'),5))
    p=plan_frontier(c,labels,5);dense=plan_frontier(c,labels,5);dense.structured=False
    assert p.structured
    np.testing.assert_allclose(evaluate_frontier(p,labels),evaluate_frontier(dense,labels),atol=2e-12)


def test_structured_frontier_does_not_materialize_gate_matrices(monkeypatch):
    import rqm_compiler.frontier as f
    c=Circuit(3).ry(0,.4).rxx(0,1,.3).ry(0,.2).cx(2,0).rzz(0,1,-.7)
    def forbidden(*args):pytest.fail('dense gate materialized')
    monkeypatch.setattr(f,'_single_qubit_matrix',forbidden)
    monkeypatch.setattr(f,'_operation_matrix',forbidden)
    assert np.isfinite(evaluate_frontier(plan_frontier(c,'XYZ',3),'XYZ'))
