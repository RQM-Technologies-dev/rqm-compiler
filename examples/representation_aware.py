"""RQM Compiler 0.4 representation-aware public API examples.

Run with: python examples/representation_aware.py
"""
from rqm_compiler import (
    Circuit,
    compile_representation_aware,
    get_backend_capability_model,
    plan_and_evaluate,
    plan_backend_materialization,
)

def chain():
    c=Circuit(4);c.h(0)
    for i in range(3):
        c.rxx(i,i+1,.11);c.rzz(i,i+1,-.067);c.cx(i,i+1)
    return c

def general_fallback():
    c=Circuit(3);c.h(0);c.cx(0,2);c.ry(1,.31);c.cz(2,1)
    return c

def show(label,circuit,observable):
    compiled=compile_representation_aware(circuit)
    result=plan_and_evaluate(compiled,observable)
    r=compiled.report
    print(label,{
        "C_R":r.representation_complexity,
        "C_Q":r.query_complexity,
        "topology":r.recognized_topology,
        "route":r.selected_query_route,
        "fallback":r.query_fallback_used,
        "value":result.value,
    })

if __name__=="__main__":
    show("chain",chain(),"ZZZZ")
    show("general",general_fallback(),"ZZZ")
    model=get_backend_capability_model("braket_gate_model")
    planned=compile_representation_aware(chain())
    materialization=plan_backend_materialization(planned.circuit,model.name)
    print("backend",model.framework,materialization)
