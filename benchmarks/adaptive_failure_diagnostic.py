"""Focused forensic diagnostic for adaptive SU(4) representation transitions."""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse, json
from pathlib import Path

from phase_transition_cr import FAMILIES
from rqm_compiler.adaptive import AdaptiveCartanPolicy
from rqm_compiler.compile import optimize_circuit

CATEGORIES = {
    "decomposition_failure",
    "numerical_tolerance_failure",
    "equivalence_proof_failure",
    "unsupported_window_structure",
    "implementation_defect",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, required=True)
    args = ap.parse_args()
    histogram: Counter[str] = Counter()
    examples: dict[str, list[dict[str, object]]] = defaultdict(list)
    conditions = 0
    events_seen = 0
    for n in (4, 8):
        for depth in (4, 8):
            for density in (0.5, 1.0):
                for seed in (1729, 2718):
                    for family, builder in FAMILIES.items():
                        conditions += 1
                        circuit = builder(n, depth, density, seed)
                        _, report = optimize_circuit(circuit, adaptive_policy=AdaptiveCartanPolicy.aggressive(n))
                        routing = getattr(report, "adaptive_routing", {}) or {}
                        for event in routing.get("representation_events", []):
                            events_seen += 1
                            category = (event.get("details") or {}).get("failure_category")
                            if not category:
                                continue
                            if category not in CATEGORIES:
                                raise AssertionError(f"unknown failure category: {category}")
                            histogram[category] += 1
                            if len(examples[category]) < 8:
                                examples[category].append({
                                    "family": family, "n": n, "depth": depth,
                                    "density": density, "seed": seed, "event": event,
                                })
    payload = {
        "conditions": conditions,
        "events_seen": events_seen,
        "classified_failures": sum(histogram.values()),
        "root_cause_histogram": dict(sorted(histogram.items())),
        "representative_examples": dict(sorted(examples.items())),
        "scientific_note": "No failure category is evidence that a lower representation remained mathematically closed; closure retention requires an independently evaluated closure predicate.",
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    main()
