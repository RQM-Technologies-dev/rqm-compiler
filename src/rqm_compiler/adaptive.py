"""Quaternion-first, budgeted adaptive Cartan routing."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import time
from typing import Literal

from rqm_entanglement import decompose_su4_verified

from .adaptive_closure import REPRESENTATION_LEVEL, minimal_representation
from .circuit import Circuit
from .ops import Operation
from .su4_blocks import _candidate_windows, _window_unitary
from .verification import verify_equivalence

AdaptiveMode = Literal["off", "symbolic_only", "selective"]


@dataclass(frozen=True)
class TwoQubitCostModel:
    name: str = "cx_reference"
    gate_costs: tuple[tuple[str, int], ...] = (
        ("cx", 1), ("cy", 1), ("cz", 1), ("swap", 3), ("iswap", 2),
        ("rxx", 2), ("ryy", 2), ("rzz", 2), ("su4q", 6),
    )
    generic_su4_ceiling: int = 6
    def __post_init__(self) -> None:
        if not self.name: raise ValueError("cost model name is required")
        if self.generic_su4_ceiling < 1: raise ValueError("generic_su4_ceiling must be positive")
        if any(cost < 0 for _, cost in self.gate_costs): raise ValueError("gate costs must be non-negative")
    def operation_cost(self, operation: Operation) -> int:
        costs=dict(self.gate_costs); touched=set(operation.targets)|set(operation.controls)
        return int(costs.get(operation.gate,0)) if len(touched)==2 else 0

@dataclass(frozen=True)
class CompilationWorkBudget:
    max_kak_windows: int = 0
    max_dense_operations: int = 0
    def __post_init__(self) -> None:
        if self.max_kak_windows < 0 or self.max_dense_operations < 0: raise ValueError("work budget values must be non-negative")

@dataclass(frozen=True)
class AdaptiveCartanPolicy:
    mode: AdaptiveMode = "symbolic_only"
    budget: CompilationWorkBudget = field(default_factory=CompilationWorkBudget)
    cost_model: TwoQubitCostModel = field(default_factory=TwoQubitCostModel)
    min_source_two_qubit_cost: int = 9
    min_predicted_savings: int = 3
    min_predicted_savings_fraction: float = 0.30
    max_window_operations: int = 64
    tolerance: float = 1e-10
    def __post_init__(self) -> None:
        if self.mode not in {"off","symbolic_only","selective"}: raise ValueError(f"unsupported adaptive mode: {self.mode}")
        if self.min_source_two_qubit_cost < 0 or self.min_predicted_savings < 0: raise ValueError("cost thresholds must be non-negative")
        if not 0.0 <= self.min_predicted_savings_fraction <= 1.0: raise ValueError("min_predicted_savings_fraction must be in [0, 1]")
        if self.max_window_operations < 1: raise ValueError("max_window_operations must be positive")
        if not math.isfinite(self.tolerance) or self.tolerance <= 0.0: raise ValueError("tolerance must be positive and finite")
    @classmethod
    def safe(cls): return cls(mode="symbolic_only")
    @classmethod
    def balanced(cls,num_qubits:int):
        quota=min(16,max(1,math.ceil(num_qubits/64))); return cls(mode="selective",budget=CompilationWorkBudget(quota,quota*64))
    @classmethod
    def aggressive(cls,num_qubits:int):
        quota=min(64,max(1,math.ceil(num_qubits/16))); return cls(mode="selective",budget=CompilationWorkBudget(quota,quota*64))

@dataclass(frozen=True)
class CandidateWindow:
    start:int; end:int; pair:tuple[int,int]; source_two_qubit_cost:int; predicted_savings:int
    @property
    def operation_count(self): return self.end-self.start
    @property
    def window_id(self): return f"{self.pair[0]}-{self.pair[1]}:{self.start}-{self.end}"

def circuit_two_qubit_cost(circuit,model): return sum(model.operation_cost(op) for op in circuit.operations)
def _copy_operation(operation): return Operation.from_descriptor(operation.to_descriptor())

def _event(kind:str, *, window_id:str, before:str, after:str, pair:tuple[int,int], reason:str, details:dict[str,object]|None=None) -> dict[str,object]:
    return {"kind":kind,"window_id":window_id,"pair":list(pair),"before":before,"after":after,
            "before_level":REPRESENTATION_LEVEL[before],"after_level":REPRESENTATION_LEVEL[after],"reason":reason,
            "details":details or {}}

def _discover_candidates(circuit,policy):
    candidates=[]; rejected=[]
    for start,end,pair in _candidate_windows(circuit):
        window=circuit.operations[start:end]; source_cost=sum(policy.cost_model.operation_cost(x) for x in window)
        predicted=source_cost-policy.cost_model.generic_su4_ceiling; fraction=predicted/source_cost if source_cost else 0.0; reason=None
        if len(window)>policy.max_window_operations: reason="window_too_large"
        elif source_cost<policy.min_source_two_qubit_cost: reason="source_cost_below_threshold"
        elif predicted<policy.min_predicted_savings: reason="predicted_savings_below_threshold"
        elif fraction<policy.min_predicted_savings_fraction: reason="predicted_fraction_below_threshold"
        if reason:
            rejected.append({"window_id":f"{pair[0]}-{pair[1]}:{start}-{end}","pair":list(pair),"range":[start,end],"source_two_qubit_cost":source_cost,"predicted_savings":predicted,"reason":reason}); continue
        candidates.append(CandidateWindow(start,end,pair,source_cost,predicted))
    return candidates,rejected

def apply_adaptive_cartan(circuit: Circuit, policy: AdaptiveCartanPolicy):
    started=time.perf_counter_ns(); events=[]
    if policy.mode != "selective" or policy.budget.max_kak_windows == 0:
        return circuit,{"mode":policy.mode,"budget_kind":"deterministic_work","kak_invocations":0,"selected_windows":[],"rejected_windows":[],"representation_events":events,"elapsed_ns":time.perf_counter_ns()-started}
    candidates,rejected=_discover_candidates(circuit,policy)
    ranked=sorted(candidates,key=lambda x:(-x.predicted_savings,-x.source_two_qubit_cost,x.operation_count,x.pair,x.start))
    selected=[]; dense_operations=0
    for c in ranked:
        if len(selected)>=policy.budget.max_kak_windows:
            rejected.append({"window_id":c.window_id,"reason":"kak_window_budget_exhausted"}); continue
        if dense_operations+c.operation_count>policy.budget.max_dense_operations:
            rejected.append({"window_id":c.window_id,"reason":"dense_operation_budget_exhausted"}); continue
        selected.append(c); dense_operations+=c.operation_count
    replacements={}; selected_evidence=[]; kak_invocations=0
    for c in sorted(selected,key=lambda x:x.start):
        window=circuit.operations[c.start:c.end]; payload=[op.to_descriptor() for op in window]
        source_hash=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
        before=max((minimal_representation(op) for op in window), key=lambda name: REPRESENTATION_LEVEL[name], default="identity")
        try:
            kak_invocations+=1
            evidence=decompose_su4_verified(_window_unitary(window,c.pair),tolerance=policy.tolerance,source_hash=source_hash)
        except (ImportError,TypeError,ValueError) as exc:
            rejected.append({"window_id":c.window_id,"reason":"decomposition_or_proof_failed","detail":str(exc)})
            events.append(_event("retained",window_id=c.window_id,before=before,after=before,pair=c.pair,reason="decomposition_or_proof_failed")); continue
        replacement=Operation(gate="su4q",targets=list(c.pair),params={"block":evidence.block.to_dict(),"fallback_operations":payload,"routing":{"window_id":c.window_id,"source_hash":source_hash,"source_two_qubit_cost":c.source_two_qubit_cost,"predicted_savings":c.predicted_savings,"cost_model":policy.cost_model.name}})
        after=minimal_representation(replacement)
        kind="promotion" if REPRESENTATION_LEVEL[after]>REPRESENTATION_LEVEL[before] else ("demotion" if REPRESENTATION_LEVEL[after]<REPRESENTATION_LEVEL[before] else "retained")
        events.append(_event(kind,window_id=c.window_id,before=before,after=after,pair=c.pair,reason="verified_su4_replacement",details={"reconstruction_error":evidence.reconstruction_error,"weyl_class":evidence.classification.class_label}))
        replacements[c.start]=(c.end,replacement)
        selected_evidence.append({"window_id":c.window_id,"pair":list(c.pair),"range":[c.start,c.end],"source_hash":source_hash,"source_two_qubit_cost":c.source_two_qubit_cost,"predicted_savings":c.predicted_savings,"reconstruction_error":evidence.reconstruction_error,"weyl_class":evidence.classification.class_label})
    output=Circuit(circuit.num_qubits,metadata=dict(circuit.metadata)); index=0
    while index<len(circuit.operations):
        replacement=replacements.get(index)
        if replacement is None: output.add(_copy_operation(circuit.operations[index])); index+=1; continue
        end,op=replacement; output.add(op); index=end
    proof=verify_equivalence(circuit,output,max_dense_qubits=8)
    if not proof.verified:
        output=Circuit(circuit.num_qubits,metadata=dict(circuit.metadata))
        for op in circuit.operations: output.add(_copy_operation(op))
        rejected.extend({"window_id":item["window_id"],"reason":"final_circuit_proof_failed"} for item in selected_evidence)
        # Record semantic rollback as a demotion from proposed generalized block back to original proven form.
        for item in selected_evidence:
            wid=item["window_id"]; pair=tuple(item["pair"]); events.append(_event("demotion",window_id=wid,before="quaternion_cartan_block",after="cartan_relation",pair=pair,reason="final_circuit_proof_failed_rollback"))
        selected_evidence=[]
    return output,{"mode":policy.mode,"budget_kind":"deterministic_work","budget":{"max_kak_windows":policy.budget.max_kak_windows,"max_dense_operations":policy.budget.max_dense_operations},"cost_model":policy.cost_model.name,"generic_su4_ceiling":policy.cost_model.generic_su4_ceiling,"candidate_windows":len(candidates),"selected_windows":selected_evidence,"rejected_windows":rejected,"representation_events":events,"promotion_count":sum(e["kind"]=="promotion" for e in events),"demotion_count":sum(e["kind"]=="demotion" for e in events),"retained_count":sum(e["kind"]=="retained" for e in events),"kak_invocations":kak_invocations,"dense_operations":dense_operations,"semantic_verified":bool(proof.verified),"elapsed_ns":time.perf_counter_ns()-started}
