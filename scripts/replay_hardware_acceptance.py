"""Replay retained hardware inputs offline against installed release packages.

Requires a separate rqm-api checkout plus its harness dependencies. Nothing is
submitted to a provider. Historical hardware counts remain historical evidence.
"""

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    attempts = []

    def guard(event, arguments):
        if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
            attempts.append(event)
            raise RuntimeError("Network prohibited in offline hardware replay")

    sys.addaudithook(guard)
    sys.path.insert(0, str(args.api.resolve()))
    import numpy as np
    import rqm_qiskit
    from app.core.config import Settings
    from app.models.schemas import CircuitIR, Provider
    from app.services.compiler import CompilerService
    from app.services.measurement_boundary import normalize_measurements
    from app.services.providers.braket_provider import _to_braket_circuit
    from app.services.real_qpu_canary import _qiskit_descriptor
    from braket.circuits import Circuit as BraketCircuit
    from braket.circuits.serialization import IRType
    from qiskit.quantum_info import Statevector
    from rqm_braket.translator import BraketTranslator
    from rqm_compiler import Circuit

    service = CompilerService(
        Settings(
            _env_file=None,
            provider_mode="real",
            allowed_provider_targets={
                "ibm": ["offline-sdk"],
                "braket": ["offline-sdk"],
            },
            braket_enabled=False,
            qiskit_runtime_enabled=False,
            global_provider_kill_switch_enabled=False,
            disabled_provider_targets={},
        )
    )
    fixtures = json.loads(args.fixtures.read_text())
    rows = []
    for case in fixtures["cases"]:
        row = {k: case[k] for k in ("provider", "index", "phase", "basis", "level")}
        try:
            compiled, _, _ = service.compile(
                CircuitIR.model_validate(case["input"]),
                Provider(case["provider"]),
                "offline-sdk",
                512,
                case["level"],
            )
            row["compiled_operations_match_hardware_snapshot"] = (
                compiled["operations"] == case["compiled"]["operations"]
            )
            if case["provider"] == "ibm":
                descriptor = _qiskit_descriptor(compiled)
                circuit = rqm_qiskit.to_qiskit_circuit(
                    Circuit.from_descriptors(
                        descriptor["operations"], num_qubits=descriptor["num_qubits"]
                    ),
                    optimize=False,
                )
                probabilities = Statevector.from_instruction(
                    circuit.remove_final_measurements(inplace=False)
                ).probabilities()
                row["max_probability_error"] = float(
                    np.max(np.abs(probabilities - case["expected_probabilities"]))
                )
                mapping = {
                    circuit.find_bit(g.clbits[0]).index: circuit.find_bit(
                        g.qubits[0]
                    ).index
                    for g in circuit.data
                    if g.operation.name == "measure"
                }
                row["measurement_order"] = [mapping[k] for k in sorted(mapping)]
                row["passed"] = (
                    row["compiled_operations_match_hardware_snapshot"]
                    and row["max_probability_error"] <= 1e-9
                    and row["measurement_order"] == [2, 0, 1]
                )
            else:
                # Record API-helper compatibility separately from the public
                # bridge's documented descriptor interface. Do not patch API
                # or bridge implementations during compiler acceptance.
                try:
                    _to_braket_circuit(compiled, BraketCircuit)
                    row["api_helper_compatible"] = True
                except Exception as exc:  # noqa: BLE001 - retain every diagnostic in the evidence
                    row["api_helper_compatible"] = False
                    row["api_helper_error"] = f"{type(exc).__name__}: {exc}"
                descriptor = normalize_measurements(compiled)
                circuit = BraketTranslator().translate_descriptors(
                    descriptor["operations"]
                )
                program = json.loads(circuit.to_ir(ir_type=IRType.OPENQASM).json())
                row["submitted_program_matches_hardware_snapshot"] = (
                    program == case["program"]
                )
                row["passed"] = (
                    row["compiled_operations_match_hardware_snapshot"]
                    and row["submitted_program_matches_hardware_snapshot"]
                )
        except Exception as exc:  # noqa: BLE001 - retain every diagnostic in the evidence
            row.update(passed=False, error_type=type(exc).__name__, error=str(exc))
        rows.append(row)
    result = {
        "kind": "offline_replay_of_completed_hardware_workloads",
        "new_hardware_jobs": 0,
        "network_attempts": attempts,
        "api_revision": fixtures["source_commit"],
        "fixture_sha256": hashlib.sha256(args.fixtures.read_bytes()).hexdigest(),
        "packages": {
            n: importlib.metadata.version(n)
            for n in (
                "rqm-compiler",
                "rqm-core",
                "rqm-entanglement",
                "rqm-qiskit",
                "rqm-braket",
                "qiskit",
                "amazon-braket-sdk",
            )
        },
        "rows": rows,
        "passed": sum(r["passed"] for r in rows),
        "total": len(rows),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    return int(bool(attempts) or result["passed"] != result["total"])


if __name__ == "__main__":
    raise SystemExit(main())
