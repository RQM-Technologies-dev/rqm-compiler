"""Query-support frontier planning with a pre-allocation active-qubit cap.

The bound applies to one frontier tensor (4**width real coefficients for the
closed hinge/CX path; complex entries for generic gates), not
process memory. A rejected chronological schedule is not an optimal-width proof.
"""
from dataclasses import dataclass
import numpy as np
from .ops import Operation
from .su4_blocks import _operation_matrix, _single_qubit_matrix

P = {"I":np.eye(2,dtype=complex), "X":np.array([[0,1],[1,0]],complex),
     "Y":np.array([[0,-1j],[1j,0]],complex), "Z":np.diag([1.,-1.])}

@dataclass
class FrontierPlan:
    operations: list
    preparations: dict
    last_use: dict
    support: set
    width: int
    accepted: bool
    reason: str
    matrices: list | None = None
    states: dict | None = None
    structured: bool = False
    coefficient_actions: list | None = None


def plan_frontier(circuit, labels, cap):
    support={q for q,p in enumerate(labels) if p!='I'}
    kept=[]
    for op in reversed(circuit.operations):
        if op.gate=='barrier':continue
        touched=set(op.targets)|set(op.controls)
        if touched & support:
            support.update(touched);kept.append(op)
    preparations={}; coupled=set();operations=[]
    for op in reversed(kept):
        qs=tuple(sorted(set(op.targets)|set(op.controls)))
        if len(qs)==1 and qs[0] not in coupled:
            preparations.setdefault(qs[0],[]).append(op)
        else:
            coupled.update(qs);operations.append((op,qs))
    last={q:i for i,(_,qs) in enumerate(operations) for q in qs}
    active=set();width=0
    for i,(_,qs) in enumerate(operations):
        active.update(qs);width=max(width,len(active))
        active.difference_update(q for q in qs if last[q]==i)
    width=max(width,1 if support else 0)
    accepted=width<=cap and all(1<=len(qs)<=2 for _,qs in operations)
    plan=FrontierPlan(operations,preparations,last,support,width,accepted,
        "" if accepted else f"frontier width {width} exceeds cap {cap} or unsupported locality")
    plan.structured=all(len(qs)==1 or op.gate in {"rxx","ryy","rzz","cx"} for op,qs in operations)
    return plan


def _apply(tensor, matrix, axes):
    axes=list(axes);order=axes+[i for i in range(tensor.ndim) if i not in axes]
    moved=tensor.transpose(order)
    out=(matrix@moved.reshape(2**len(axes),-1)).reshape(moved.shape)
    return out.transpose(np.argsort(order))


def evaluate_frontier(plan, labels):
    if not plan.accepted:raise ValueError("Rejected frontier plan: no numeric allocation permitted")
    if plan.structured:return _evaluate_coefficients(plan,labels)
    if plan.matrices is None:
        plan.states={}
        for q in plan.support:
            v=np.array([1.,0.],complex)
            for op in plan.preparations.get(q,[]):v=_single_qubit_matrix(op)@v
            plan.states[q]=v
        plan.matrices=[]
        for op,qs in plan.operations:
            if len(qs)==1:u=_single_qubit_matrix(op)
            else:
                # Tensor axes below are MSB first; compiler matrices are LSB first.
                u=_operation_matrix(op,qs).reshape(2,2,2,2).transpose(1,0,3,2).reshape(4,4)
            plan.matrices.append(u)
    rho=np.array(1.+0j);active=[];initialized=set()
    for i,((op,qs),u) in enumerate(zip(plan.operations,plan.matrices)):
        for q in qs:
            if q not in initialized:
                v=plan.states[q];k=len(active)
                rho=np.kron(rho.reshape(2**k,2**k),np.outer(v,v.conj())).reshape((2,)*(2*k+2))
                active.append(q);initialized.add(q)
        k=len(active);axes=[active.index(q) for q in qs]
        rho=_apply(rho,u,axes)
        rho=_apply(rho,u.conj(),[x+k for x in axes])
        for q in qs:
            if plan.last_use[q]==i:
                k=len(active);axis=active.index(q)
                rho=_apply(rho,P[labels[q]],[axis])
                rho=np.trace(rho,axis1=axis,axis2=axis+k);active.remove(q)
    value=complex(rho)
    for q in plan.support-initialized:
        v=plan.states[q];value*=np.vdot(v,P[labels[q]]@v)
    return value


def _evaluate_coefficients(plan,labels):
    from .local_observable import prepared_coefficients, operation_quaternion
    from rqm_entanglement.pauli_transfer import apply_pair_coefficients
    if plan.coefficient_actions is None:
        plan.states={q:np.asarray(prepared_coefficients(plan.preparations.get(q,[]))) for q in plan.support}
        plan.coefficient_actions=[]
        for op,qs in plan.operations:
            if len(qs)==1:
                q=operation_quaternion(op)
                action=np.zeros((4,4));action[0,0]=1.
                for i,axis in enumerate(((1,0,0),(0,1,0),(0,0,1))):action[1:,i+1]=q.rotate_vector(axis)
            else:action=None
            plan.coefficient_actions.append(action)
    coefficients=np.array(1.);active=[];initialized=set()
    for i,((op,qs),action) in enumerate(zip(plan.operations,plan.coefficient_actions)):
        for q in qs:
            if q not in initialized:
                coefficients=np.multiply.outer(coefficients,plan.states[q]);active.append(q);initialized.add(q)
        if len(qs)==1:
            axis=active.index(qs[0]);coefficients=np.moveaxis(np.tensordot(action,coefficients,axes=(1,axis)),0,axis)
        else:
            wires=(op.controls[0],op.targets[0]) if op.gate=='cx' else qs
            coefficients=apply_pair_coefficients(coefficients,[active.index(q) for q in wires],op.gate,float(op.params.get('angle',0.)))
        for q in qs:
            if plan.last_use[q]==i:
                axis=active.index(q);coefficients=np.take(coefficients,'IXYZ'.index(labels[q]),axis=axis);active.remove(q)
    value=float(coefficients)
    for q in plan.support-initialized:value*=plan.states[q]['IXYZ'.index(labels[q])]
    return complex(value)
