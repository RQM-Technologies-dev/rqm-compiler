"""Public representation-aware compiler API for the 0.3.x integration line.

This module promotes the validated stable-prototype planner into supported
rqm-compiler API names while keeping implementation compatibility during the
0.3.x migration.
"""
from __future__ import annotations
from typing import Iterable
import numpy as np

from .adaptive import AdaptiveCartanPolicy
from .circuit import Circuit
from .stable_prototype import (
    StableCompileResult as RepresentationCompileResult,
    StableReadoutResult as QueryResult,
    apply_boundary_transfer,
    boundary_transfer,
    compile_stable,
    expectation_stable,
    global_z_chain,
    circuit_digest,
)

def compile_representation_aware(
    circuit:Circuit, *, adaptive_policy:AdaptiveCartanPolicy|None=None
)->RepresentationCompileResult:
    """Compile using the validated representation-aware pipeline."""
    return compile_stable(circuit,adaptive_policy=adaptive_policy)

def evaluate_observable(
    circuit:Circuit,
    pauli:str|Iterable[str],
    *,
    max_terms:int=250_000,
    max_frontier_qubits:int=4,
)->QueryResult:
    """Evaluate an observable through the validated query-aware planner.

    Specialized routes are selected only by strict validated recognizers;
    otherwise the planner falls back to the general exact evaluator.
    """
    return expectation_stable(circuit,pauli,max_terms=max_terms,max_frontier_qubits=max_frontier_qubits)

def plan_and_evaluate(
    compiled:RepresentationCompileResult,
    pauli:str|Iterable[str],
    *,
    max_terms:int=250_000,
    max_frontier_qubits:int=4,
    _plan_cache:dict|None=None,
)->QueryResult:
    """Evaluate a query and attach planner telemetry to CompilerReport."""
    report=compiled.report
    query_circuit=compiled.circuit
    report.query_evaluation_basis="compiled_output"
    if (compiled.query_source is not None
        and compiled.output_digest==circuit_digest(compiled.circuit)
        and compiled.source_digest==circuit_digest(compiled.query_source)):
        query_circuit=compiled.query_source
        report.query_evaluation_basis="verified_equivalent_input"
    # Reset before evaluation, including the exception path.
    report.query_complexity=None
    report.query_complexity_unit=None
    report.selected_query_route=None
    report.recognized_topology=None
    report.contraction_width=None
    report.largest_intermediate=None
    report.largest_intermediate_unit=None
    report.query_promotion_count=0
    report.query_plan_reused=False
    report.frontier_rejection=None
    report.query_fallback_used=False
    report.query_fallback_reason=None
    result=expectation_stable(query_circuit,pauli,max_terms=max_terms,max_frontier_qubits=max_frontier_qubits,_plan_cache=_plan_cache)
    report.largest_intermediate=result.largest_intermediate
    report.largest_intermediate_unit=result.intermediate_unit
    report.query_promotion_count=result.query_promotion_count
    report.query_plan_reused=result.plan_reused
    report.frontier_rejection=result.frontier_rejection
    report.query_complexity=result.work_units
    report.query_complexity_unit="pauli_terms" if result.work_units is not None else None
    report.selected_query_route=result.method
    report.query_fallback_used=result.method in {"general_pauli_promoted","structured_exact"}
    report.query_fallback_reason=result.reason or None if report.query_fallback_used else None
    if result.method in {"direct_star_relational","star_product_transfer"}:
        report.recognized_topology="star"
        report.query_complexity_unit="leaf_transfers"
    elif result.method=="chain_boundary_transfer":
        report.recognized_topology="chain"
        report.contraction_width=1
        report.query_complexity_unit="edge_transfers"
    elif result.method=="topology_hardware_1d":
        report.recognized_topology="hardware_efficient_1d"
        # No measured contraction-width certificate is returned by this route.
        report.query_complexity_unit="complex_tensor_entries"
        report.largest_intermediate=result.work_units
    elif result.method=="bounded_frontier_transfer":
        report.recognized_topology="bounded_frontier"
        report.contraction_width=result.frontier_width
        report.query_complexity_unit="frontier_operations"
    else:
        report.recognized_topology=None
    return result

__all__=[
    "RepresentationCompileResult","QueryResult",
    "compile_representation_aware","evaluate_observable","evaluate_observables","plan_and_evaluate",
    "boundary_transfer","apply_boundary_transfer","global_z_chain",
]


def evaluate_observables(compiled:RepresentationCompileResult, paulis:Iterable[str], *,
                         max_terms:int=250_000, max_frontier_qubits:int=4)->list[QueryResult]:
    """Evaluate a batch with at most 16 cached frontier plans and local matrices.

    Reuse requires identical circuit digest, query support and frontier budget.
    Values are never cached; mutations between yielded queries invalidate reuse.
    CompilerReport describes the last query; each returned result has its own
    intermediate, rejection and plan-reuse evidence.
    """
    cache={}
    return [plan_and_evaluate(compiled,p,max_terms=max_terms,
            max_frontier_qubits=max_frontier_qubits,_plan_cache=cache) for p in paulis]
