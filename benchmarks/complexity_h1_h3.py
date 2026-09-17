"""H1-H3 scaling experiment for rqm-compiler.

This benchmark separates three hypotheses:
H1 representational compression, H2 operational/computational compression,
and H3 closure compression.

Important: ``rqm_representation_size`` is a structural compiler-IR measure, not
an assertion that the compiler stores or simulates a complete n-qubit state in
that many scalars.  ``minimum_closed_representation_size`` is therefore reported
as a PROXY until an exact RQM state-evolution representation exposes its own
closed-state dimension.  This prevents the benchmark from overstating the
scientific result.

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
from typing import Callable

from rqm_compiler import Circuit
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.compile import optimize_circuit


@dataclass
class Result:
    family: str
    n: int
    statevector_dimension: int
    input_operations: int
    output_operations: int
    rqm_representation_size: int
    minimum_closed_representation_size_proxy: int
    elapsed_ns_median: int
    peak_memory_bytes_median: int
    promotion_count: int
    maximum_representation_level: int
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
        # Alternating nearest-neighbour brickwork spreads entanglement without
        # making circuit construction itself exponential.
        for parity in (0, 1):
            for q in range(parity, n - 1, 2):
                dense_layers.cx(q, q + 1)
                dense_layers.t(q + 1)

    return {
        "local_clifford": local,
        "entangled_clifford": clifford_chain,
        "entangled_nonclifford": nonclifford_chain,
        "deep_nonclifford": dense_layers,
    }


def _scalar_count(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, (bool, int, float, str)):
        return 1
    if isinstance(value, dict):
        return sum(_scalar_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_scalar_count(v) for v in value)
    return 1


def _representation_size(circuit: Circuit) -> int:
    """Count scalar leaves in canonical operation descriptors."""
    return sum(_scalar_count(op.to_descriptor()) for op in circuit.operations)


def _representation_level(circuit: Circuit) -> int:
    """Structural hierarchy: local quaternion=1, native relation=2, SU4 block=3."""
    level = 0
    for op in circuit.operations:
        touched = len(set(op.targets) | set(op.controls))
        if op.gate == "su4q":
            level = max(level, 3)
        elif touched >= 2:
            level = max(level, 2)
        else:
            level = max(level, 1)
    return level


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
    # CompilerReport is intentionally treated defensively so this benchmark
    # remains useful across report-schema revisions.
    raw = getattr(report, "__dict__", {})
    for key in ("adaptive", "adaptive_cartan", "adaptive_evidence"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    metadata = raw.get("metadata")
    if isinstance(metadata, dict):
        for key in ("adaptive", "adaptive_cartan", "adaptive_evidence"):
            value = metadata.get(key)
            if isinstance(value, dict):
                return value
    return {}


def _verified_and_error(report: object) -> tuple[bool, float | None]:
    raw = getattr(report, "__dict__", {})
    text = json.dumps(raw, default=str).lower()
    verified = "verified" in text and "counterexample" not in text and "failedproof" not in text
    # Exact numerical error is only emitted when the current report exposes it.
    for key in ("error", "max_error", "reconstruction_error", "verification_error"):
        value = raw.get(key)
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
            size = _representation_size(final_output)
            rows.append(
                Result(
                    family=family,
                    n=n,
                    statevector_dimension=1 << n,
                    input_operations=len(circuit.operations),
                    output_operations=len(final_output.operations),
                    rqm_representation_size=size,
                    minimum_closed_representation_size_proxy=size,
                    elapsed_ns_median=int(statistics.median(timings)),
                    peak_memory_bytes_median=int(statistics.median(peaks)),
                    promotion_count=promotions,
                    maximum_representation_level=_representation_level(final_output),
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
