"""H1-H3 scaling experiment for rqm-compiler.

The central measurement is C_R(n): minimum closed RQM representation size.
C_R is now supplied by representation-owned accounting rather than serialized
IR scalar-leaf size. Its scope is deliberately the compiler working
representation; it is not an n-qubit state dimension claim.

Run:
    python benchmarks/complexity_h1_h3.py --max-qubits 32 --repeats 7

Optional CSV:
    python benchmarks/complexity_h1_h3.py --max-qubits 32 --csv results/h1_h3.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path

from rqm_compiler import Circuit
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.adaptive_closure import account_closed_representation
from rqm_compiler.compile import optimize_circuit


@dataclass
class Result:
    family: str
    n: int
    statevector_dimension: int
    statevector_complex_amplitudes: int
    statevector_bytes_complex128_theoretical: int
    input_operations: int
    output_operations: int
    minimum_closed_representation_size: int
    closure_metric_scope: str
    closure_metric_exact_within_scope: bool
    quantum_state_dimension_claim: bool
    maximum_representation_level: int
    representation_histogram: str
    promotion_count: int
    elapsed_ns_median: int
    peak_memory_bytes_median: int
    semantic_verified: bool
    output_error: float | None


def _families(n: int) -> dict[str, Circuit]:
    """Deterministic ladder from local/Clifford to entangled non-Clifford."""
    local = Circuit(n)
    for q in range(n):
        local.h(q).s(q).h(q)

    clifford_chain = Circuit(n)
    for q in range(n):
        clifford_chain.h(q)
    for q in range(n - 1):
        clifford_chain.cx(q, q + 1)

    nonclifford_chain = Circuit(n)
    for q in range(n):
        nonclifford_chain.h(q).t(q)
    for q in range(n - 1):
        nonclifford_chain.cx(q, q + 1)
        nonclifford_chain.t(q + 1)

    dense_layers = Circuit(n)
    for layer in range(3):
        for q in range(n):
            dense_layers.h(q).t(q).rz(q, math.pi / (8 + layer))
        for parity in (0, 1):
            for q in range(parity, n - 1, 2):
                dense_layers.cx(q, q + 1)
                dense_layers.t(q + 1)

    axis_hinge = Circuit(n)
    for q in range(n):
        axis_hinge.h(q)
    for q in range(0, n - 1, 2):
        axis_hinge.rxx(q, q + 1, math.pi / 8)
    for q in range(1, n - 1, 2):
        axis_hinge.rzz(q, q + 1, math.pi / 16)

    return {
        "local_clifford": local,
        "entangled_clifford": clifford_chain,
        "entangled_nonclifford": nonclifford_chain,
        "deep_nonclifford": dense_layers,
        "axis_hinge_structured": axis_hinge,
    }


def _compile_once(circuit: Circuit) -> tuple[Circuit, object, int, int]:
    policy = AdaptiveCartanPolicy.aggressive(circuit.num_qubits)
    tracemalloc.start()
    started = time.perf_counter_ns()
    output, report = optimize_circuit(circuit, adaptive_policy=policy)
    elapsed = time.perf_counter_ns() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return output, report, elapsed, peak


def _adaptive_evidence(report: object) -> dict[str, object]:
    raw = getattr(report, "__dict__", {})
    for key in ("adaptive_routing", "adaptive", "adaptive_cartan", "adaptive_evidence"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    metadata = raw.get("metadata")
    if isinstance(metadata, dict):
        for key in ("adaptive_routing", "adaptive", "adaptive_cartan", "adaptive_evidence"):
            value = metadata.get(key)
            if isinstance(value, dict):
                return value
    return {}


def _verified_and_error(report: object) -> tuple[bool, float | None]:
    raw = getattr(report, "__dict__", {})
    status = str(raw.get("equivalence_status", "")).upper()
    verified = bool(raw.get("equivalence_verified", False)) or status == "VERIFIED"
    equivalence = raw.get("equivalence_report")
    if isinstance(equivalence, dict):
        value = equivalence.get("max_abs_err")
        if isinstance(value, (int, float)):
            return verified, float(value)
    return verified, None


def run(ns: list[int], repeats: int) -> list[Result]:
    rows: list[Result] = []
    for n in ns:
        for family, circuit in _families(n).items():
            timings: list[int] = []
            peaks: list[int] = []
            final_output = None
            final_report = None
            for _ in range(repeats):
                output, report, elapsed, peak = _compile_once(circuit)
                timings.append(elapsed)
                peaks.append(peak)
                final_output, final_report = output, report
            assert final_output is not None and final_report is not None

            adaptive = _adaptive_evidence(final_report)
            selected = adaptive.get("selected_windows", [])
            promotions = len(selected) if isinstance(selected, list) else 0
            verified, error = _verified_and_error(final_report)
            closure = account_closed_representation(final_output)
            dimension = 1 << n

            rows.append(
                Result(
                    family=family,
                    n=n,
                    statevector_dimension=dimension,
                    statevector_complex_amplitudes=dimension,
                    statevector_bytes_complex128_theoretical=dimension * 16,
                    input_operations=len(circuit.operations),
                    output_operations=len(final_output.operations),
                    minimum_closed_representation_size=closure.minimum_closed_representation_size,
                    closure_metric_scope=closure.scope,
                    closure_metric_exact_within_scope=closure.exact_within_scope,
                    quantum_state_dimension_claim=closure.quantum_state_dimension_claim,
                    maximum_representation_level=closure.maximum_representation_level,
                    representation_histogram=json.dumps(closure.representation_histogram, sort_keys=True),
                    promotion_count=promotions,
                    elapsed_ns_median=int(statistics.median(timings)),
                    peak_memory_bytes_median=int(statistics.median(peaks)),
                    semantic_verified=verified,
                    output_error=error,
                )
            )
    return rows


def _write_csv(path: Path, rows: list[Result]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-qubits", type=int, default=32)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    ns = [n for n in (2, 4, 8, 16, 32, 64, 128) if n <= args.max_qubits]
    rows = run(ns, max(1, args.repeats))
    if args.csv:
        _write_csv(args.csv, rows)
    print(json.dumps([asdict(row) for row in rows], indent=2))


if __name__ == "__main__":
    main()
