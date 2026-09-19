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
)->QueryResult:
    """Evaluate an observable through the validated query-aware planner.

    Specialized routes are selected only by strict validated recognizers;
    otherwise the planner falls back to the general exact evaluator.
    """
    return expectation_stable(circuit,pauli,max_terms=max_terms)

def plan_and_evaluate(
    compiled:RepresentationCompileResult,
    pauli:str|Iterable[str],
    *,
    max_terms:int=250_000,
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
    report.query_fallback_used=False
    report.query_fallback_reason=None
    result=expectation_stable(query_circuit,pauli,max_terms=max_terms)
    report.query_complexity=result.work_units
    report.query_complexity_unit="pauli_terms" if result.work_units is not None else None
    report.selected_query_route=result.method
    report.query_fallback_used=result.method in {"general_pauli_promoted","structured_exact"}
    report.query_fallback_reason=result.reason or None if report.query_fallback_used else None
    if result.method=="direct_star_relational":
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
    else:
        report.recognized_topology=None
    return result

__all__=[
    "RepresentationCompileResult","QueryResult",
    "compile_representation_aware","evaluate_observable","plan_and_evaluate",
    "boundary_transfer","apply_boundary_transfer","global_z_chain",
]
