"""Quaternion-first, budgeted adaptive Cartan routing."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib, json, math, time
from typing import Literal

from rqm_entanglement import decompose_su4_verified
from .adaptive_closure import REPRESENTATION_LEVEL, minimal_representation
from .circuit import Circuit
from .ops import Operation
from .su4_blocks import _candidate_windows, _window_unitary
from .verification import verify_equivalence

AdaptiveMode = Literal["off", "symbolic_only", "selective"]
FailureCategory = Literal[
    "decomposition_failure", "numerical_tolerance_failure",
    "equivalence_proof_failure", "unsupported_window_structure",
    "implementation_defect",
]

@dataclass(frozen=True)
class TwoQubitCostModel:
    name: str = "cx_reference"
    gate_costs: tuple[tuple[str,int], ...] = (("cx",1),("cy",1),("cz",1),("swap",3),("iswap",2),("rxx",2),("ryy",2),("rzz",2),("su4q",6))
    generic_su4_ceiling: int = 6
    def __post_init__(self):
        if not self.name: raise ValueError("cost model name is required")
        if self.generic_su4_ceiling < 1: raise ValueError("generic_su4_ceiling must be positive")
        if any(cost < 0 for _,cost in self.gate_costs): raise ValueError("gate costs must be non-negative")
    def operation_cost(self, operation: Operation) -> int:
        return int(dict(self.gate_costs).get(operation.gate,0)) if len(set(operation.targets)|set(operation.controls)) == 2 else 0

@dataclass(frozen=True)
class CompilationWorkBudget:
    max_kak_windows:int=0; max_dense_operations:int=0
    def __post_init__(self):
        if self.max_kak_windows < 0 or self.max_dense_operations < 0: raise ValueError("work budget values must be non-negative")

@dataclass(frozen=True)
class AdaptiveCartanPolicy:
    mode:AdaptiveMode="symbolic_only"; budget:CompilationWorkBudget=field(default_factory=CompilationWorkBudget); cost_model:TwoQubitCostModel=field(default_factory=TwoQubitCostModel)
    min_source_two_qubit_cost:int=9; min_predicted_savings:int=3; min_predicted_savings_fraction:float=.30; max_window_operations:int=64; tolerance:float=1e-10
    def __post_init__(self):
        if self.mode not in {"off","symbolic_only","selective"}: raise ValueError(f"unsupported adaptive mode: {self.mode}")
        if self.min_source_two_qubit_cost < 0 or self.min_predicted_savings < 0: raise ValueError("cost thresholds must be non-negative")
        if not 0 <= self.min_predicted_savings_fraction <= 1: raise ValueError("min_predicted_savings_fraction must be in [0, 1]")
        if self.max_window_operations < 1: raise ValueError("max_window_operations must be positive")
        if not math.isfinite(self.tolerance) or self.tolerance <= 0: raise ValueError("tolerance must be positive and finite")
    @classmethod
    def safe(cls): return cls(mode="symbolic_only")
    @classmethod
    def balanced(cls,n:int):
        q=min(16,max(1,math.ceil(n/64))); return cls(mode="selective",budget=CompilationWorkBudget(q,q*64))
    @classmethod
    def aggressive(cls,n:int):
        q=min(64,max(1,math.ceil(n/16))); return cls(mode="selective",budget=CompilationWorkBudget(q,q*64))

@dataclass(frozen=True)
class CandidateWindow:
    start:int; end:int; pair:tuple[int,int]; source_two_qubit_cost:int; predicted_savings:int
    @property
    def operation_count(self): return self.end-self.start
    @property
    def window_id(self): return f"{self.pair[0]}-{self.pair[1]}:{self.start}-{self.end}"

def circuit_two_qubit_cost(circuit,model): return sum(model.operation_cost(op) for op in circuit.operations)
def _copy_operation(op): return Operation.from_descriptor(op.to_descriptor())

def _classify_stage_exception(stage:str, exc:BaseException) -> FailureCategory:
    text=str(exc).lower()
    if stage == "window_unitary":
        structural=("unsupported", "outside the candidate pair", "unresolved angle", "non-finite angle", "unresolved u1q")
        return "unsupported_window_structure" if isinstance(exc,ValueError) and any(s in text for s in structural) else "implementation_defect"
    if stage == "decompose":
        if isinstance(exc,ImportError) or isinstance(exc,TypeError): return "implementation_defect"
        numerical=("tolerance", "reconstruction", "numerical", "validation", "not unitary", "unitarity")
        if isinstance(exc,ValueError) and any(s in text for s in numerical): return "numerical_tolerance_failure"
        if isinstance(exc,ValueError): return "decomposition_failure"
        return "implementation_defect"
    if stage == "final_equivalence": return "equivalence_proof_failure"
    return "implementation_defect"

def _event(kind, *, window_id,before,after,pair,reason,details=None):
    return {"kind":kind,"window_id":window_id,"pair":list(pair),"before":before,"after":after,"before_level":REPRESENTATION_LEVEL[before],"after_level":REPRESENTATION_LEVEL[after],"reason":reason,"details":details or {}}

def _metadata(c:CandidateWindow, window:list[Operation], source_hash:str) -> dict[str,object]:
    return {"source_hash":source_hash,"window_id":c.window_id,"pair":list(c.pair),"window_length":len(window),"gate_histogram":dict(sorted(Counter(op.gate for op in window).items()))}

def _failure_event(c,window,source_hash,before,category,stage,exc,extra=None):
    details=_metadata(c,window,source_hash)
    details.update({"failure_category":category,"stage":stage,"exception_type":type(exc).__name__ if exc else None,"diagnostic":str(exc)[:500] if exc else None})
    if extra: details.update(extra)
    return _event("retained",window_id=c.window_id,before=before,after=before,pair=c.pair,reason=category,details=details)

def _discover_candidates(circuit,policy):
    candidates=[]; rejected=[]
    for start,end,pair in _candidate_windows(circuit):
        window=circuit.operations[start:end]; cost=sum(policy.cost_model.operation_cost(x) for x in window); predicted=cost-policy.cost_model.generic_su4_ceiling; fraction=predicted/cost if cost else 0; reason=None
        if len(window)>policy.max_window_operations: reason="window_too_large"
        elif cost<policy.min_source_two_qubit_cost: reason="source_cost_below_threshold"
        elif predicted<policy.min_predicted_savings: reason="predicted_savings_below_threshold"
        elif fraction<policy.min_predicted_savings_fraction: reason="predicted_fraction_below_threshold"
        if reason: rejected.append({"window_id":f"{pair[0]}-{pair[1]}:{start}-{end}","pair":list(pair),"range":[start,end],"source_two_qubit_cost":cost,"predicted_savings":predicted,"reason":reason})
        else: candidates.append(CandidateWindow(start,end,pair,cost,predicted))
    return candidates,rejected

def apply_adaptive_cartan(circuit:Circuit, policy:AdaptiveCartanPolicy):
    started=time.perf_counter_ns(); events=[]
    if policy.mode!="selective" or policy.budget.max_kak_windows==0:
        return circuit,{"mode":policy.mode,"budget_kind":"deterministic_work","kak_invocations":0,"selected_windows":[],"rejected_windows":[],"representation_events":[],"root_cause_histogram":{},"elapsed_ns":time.perf_counter_ns()-started}
    candidates,rejected=_discover_candidates(circuit,policy)
    ranked=sorted(candidates,key=lambda x:(-x.predicted_savings,-x.source_two_qubit_cost,x.operation_count,x.pair,x.start)); selected=[]; dense=0
    for c in ranked:
        if len(selected)>=policy.budget.max_kak_windows: rejected.append({"window_id":c.window_id,"reason":"kak_window_budget_exhausted"}); continue
        if dense+c.operation_count>policy.budget.max_dense_operations: rejected.append({"window_id":c.window_id,"reason":"dense_operation_budget_exhausted"}); continue
        selected.append(c); dense+=c.operation_count
    replacements={}; selected_evidence=[]; kak=0
    for c in sorted(selected,key=lambda x:x.start):
        window=circuit.operations[c.start:c.end]; payload=[op.to_descriptor() for op in window]; source_hash=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest(); before=max((minimal_representation(op) for op in window),key=lambda n:REPRESENTATION_LEVEL[n],default="identity")
        try: unitary=_window_unitary(window,c.pair)
        except Exception as exc:
            category=_classify_stage_exception("window_unitary",exc); events.append(_failure_event(c,window,source_hash,before,category,"window_unitary",exc)); rejected.append({"window_id":c.window_id,"reason":category,"detail":str(exc)}); continue
        try:
            kak+=1; evidence=decompose_su4_verified(unitary,tolerance=policy.tolerance,source_hash=source_hash)
        except Exception as exc:
            category=_classify_stage_exception("decompose",exc); events.append(_failure_event(c,window,source_hash,before,category,"decompose",exc,{"tolerance":policy.tolerance})); rejected.append({"window_id":c.window_id,"reason":category,"detail":str(exc)}); continue
        if float(evidence.reconstruction_error)>policy.tolerance:
            exc=ValueError(f"reconstruction error {evidence.reconstruction_error} exceeds tolerance {policy.tolerance}"); events.append(_failure_event(c,window,source_hash,before,"numerical_tolerance_failure","decompose_validation",exc,{"reconstruction_error":float(evidence.reconstruction_error),"tolerance":policy.tolerance})); rejected.append({"window_id":c.window_id,"reason":"numerical_tolerance_failure","detail":str(exc)}); continue
        replacement=Operation(gate="su4q",targets=list(c.pair),params={"block":evidence.block.to_dict(),"fallback_operations":payload,"routing":{"window_id":c.window_id,"source_hash":source_hash,"source_two_qubit_cost":c.source_two_qubit_cost,"predicted_savings":c.predicted_savings,"cost_model":policy.cost_model.name}}); after=minimal_representation(replacement); kind="promotion" if REPRESENTATION_LEVEL[after]>REPRESENTATION_LEVEL[before] else ("demotion" if REPRESENTATION_LEVEL[after]<REPRESENTATION_LEVEL[before] else "retained")
        details=_metadata(c,window,source_hash); details.update({"reconstruction_error":float(evidence.reconstruction_error),"tolerance":policy.tolerance,"weyl_class":evidence.classification.class_label})
        events.append(_event(kind,window_id=c.window_id,before=before,after=after,pair=c.pair,reason="verified_su4_replacement",details=details)); replacements[c.start]=(c.end,replacement); selected_evidence.append({"window_id":c.window_id,"pair":list(c.pair),"range":[c.start,c.end],"source_hash":source_hash,"source_two_qubit_cost":c.source_two_qubit_cost,"predicted_savings":c.predicted_savings,"reconstruction_error":evidence.reconstruction_error,"weyl_class":evidence.classification.class_label})
    output=Circuit(circuit.num_qubits,metadata=dict(circuit.metadata)); i=0
    while i<len(circuit.operations):
        r=replacements.get(i)
        if r is None: output.add(_copy_operation(circuit.operations[i])); i+=1
        else: end,op=r; output.add(op); i=end
    proof=verify_equivalence(circuit,output,max_dense_qubits=8)
    if not proof.verified:
        output=Circuit(circuit.num_qubits,metadata=dict(circuit.metadata)); [output.add(_copy_operation(op)) for op in circuit.operations]
        for item in selected_evidence:
            details={"failure_category":"equivalence_proof_failure","stage":"final_equivalence","source_hash":item["source_hash"],"proof_status":getattr(proof,"status",None),"proof_error":getattr(proof,"max_abs_err",None)}
            events.append(_event("demotion",window_id=item["window_id"],before="quaternion_cartan_block",after="cartan_relation",pair=tuple(item["pair"]),reason="equivalence_proof_failure",details=details)); rejected.append({"window_id":item["window_id"],"reason":"equivalence_proof_failure"})
        selected_evidence=[]
    histogram=Counter(e.get("details",{}).get("failure_category") for e in events if e.get("details",{}).get("failure_category"))
    return output,{"mode":policy.mode,"budget_kind":"deterministic_work","budget":{"max_kak_windows":policy.budget.max_kak_windows,"max_dense_operations":policy.budget.max_dense_operations},"cost_model":policy.cost_model.name,"generic_su4_ceiling":policy.cost_model.generic_su4_ceiling,"candidate_windows":len(candidates),"selected_windows":selected_evidence,"rejected_windows":rejected,"representation_events":events,"root_cause_histogram":dict(sorted(histogram.items())),"promotion_count":sum(e["kind"]=="promotion" for e in events),"demotion_count":sum(e["kind"]=="demotion" for e in events),"retained_count":sum(e["kind"]=="retained" for e in events),"kak_invocations":kak,"dense_operations":dense,"semantic_verified":bool(proof.verified),"elapsed_ns":time.perf_counter_ns()-started}
