import json
import pytest
from rqm_compiler import Circuit, compile_representation_aware, evaluate_observable, plan_and_evaluate
from rqm_compiler.verification import _apply_gate_to_state, verify_equivalence


def dense_expectation(circuit, labels):
    state = [1+0j] + [0j] * ((1 << circuit.num_qubits)-1)
    for op in circuit.operations:
        state = _apply_gate_to_state(state, op, circuit.num_qubits)
    return sum(abs(a)**2 * (-1)**sum((i >> q)&1 for q,p in enumerate(labels) if p=='Z')
               for i,a in enumerate(state))


@pytest.mark.parametrize('n',[4,12,250])
def test_public_regional_cancellation(n):
    c=Circuit(n).cx(0,1).cx(0,1)
    r=compile_representation_aware(c)
    assert len(r.circuit)==0
    assert r.report.optimization_applied
    assert r.report.equivalence_report['method']=='REGIONAL_COMPOSITION'
    assert len(c)==2
    json.dumps(r.report.to_dict(),allow_nan=False)


def test_regional_composition_matches_dense_and_preserves_boundaries():
    c=Circuit(4).ry(0,.37).cx(0,1).cx(0,1).rx(3,.2).rz(2,.7)
    r=compile_representation_aware(c)
    assert verify_equivalence(c,r.circuit,max_dense_qubits=4).verified
    c.barrier(0,1,2,3).measure(0,key='a')
    r=compile_representation_aware(c)
    assert r.circuit.to_descriptors()[-2:]==c.to_descriptors()[-2:]


@pytest.mark.parametrize('seed',range(12))
def test_interleaved_star_is_not_fast_path(seed):
    import numpy as np
    rng=np.random.default_rng(1000+seed)
    c=Circuit(3)
    for q in range(3):c.ry(q,float(rng.uniform(-1,1)))
    c.rxx(0,1,.67).cx(0,1).rz(0,.83).ryy(0,2,.91).cx(0,2)
    r=evaluate_observable(c,'ZZZ')
    assert r.method!='direct_star_relational'
    assert abs(r.value-dense_expectation(c,'ZZZ'))<1e-9


@pytest.mark.parametrize('label',['AB','Z','ZZZ','zI'])
def test_invalid_query_rejected_before_routing(label):
    with pytest.raises(ValueError):evaluate_observable(Circuit(2).rxx(0,1,.3),label)


def hardware():
    c=Circuit(4)
    for layer in range(2):
        for q in range(4):c.rz(q,.1).rx(q,.2)
        for q in range(3):c.cx(q,q+1)
    return c


def test_query_reset_source_equivalence_and_mutation():
    c=hardware();r=compile_representation_aware(c)
    assert r.report.optimization_applied
    q=plan_and_evaluate(r,'ZZZZ')
    assert q.method=='topology_hardware_1d'
    assert abs(q.value-dense_expectation(r.circuit,'ZZZZ'))<1e-9
    assert r.report.query_evaluation_basis=='verified_equivalent_input'
    plan_and_evaluate(r,'ZIII')
    assert r.report.largest_intermediate is None
    assert r.report.contraction_width is None
    assert r.report.query_complexity_unit=='pauli_terms'
    r.circuit.x(0)
    q=plan_and_evaluate(r,'ZIII')
    assert r.report.query_evaluation_basis=='compiled_output'
    assert abs(q.value-dense_expectation(r.circuit,'ZIII'))<1e-9


def test_sequence_levels_are_not_promotion_events():
    r=compile_representation_aware(Circuit(4).h(0).cx(0,1))
    assert r.report.promotion_count==0


def test_failed_regional_proof_does_not_commit(monkeypatch):
    from rqm_compiler.verification import EquivalenceReport,EquivalenceStatus
    monkeypatch.setattr('rqm_compiler.regional.verify_equivalence',
      lambda *a,**k:EquivalenceReport(status=EquivalenceStatus.UNVERIFIED))
    c=Circuit(4).cx(0,1).cx(0,1)
    r=compile_representation_aware(c)
    assert r.circuit.to_descriptors()==c.to_descriptors()
    assert not r.report.optimization_applied
    assert r.report.fallback_reason=='regional_verification_not_established'


def test_adaptive_budget_not_reset_per_region():
    # Optional decomposition loads Qiskit at execution time; isolate it from
    # the suite's import-only SDK leakage assertions.
    import subprocess,sys
    subprocess.run([sys.executable,"-c", """
from rqm_compiler import Circuit,compile_representation_aware,AdaptiveCartanPolicy,CompilationWorkBudget
c=Circuit(6)
for pair in [(0,1),(3,4)]:
    for i in range(12):c.cx(*pair).ry(pair[0],.13+i*.01)
policy=AdaptiveCartanPolicy(mode='selective',budget=CompilationWorkBudget(1,64))
r=compile_representation_aware(c,adaptive_policy=policy)
assert r.report.adaptive_routing['kak_invocations']<=1
"""],check=True)
