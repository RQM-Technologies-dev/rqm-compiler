"""Run frozen API corpora against certified wheel source hashes, offline.

The API unitary harness must accept main(qualification_path=...). This is a
provenance input only; workloads, tolerances, comparisons and network guards
remain unchanged. Use the API harness's recorded two-line compatibility patch.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import zipfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--api', type=Path, required=True)
    p.add_argument('--certification', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    api, cert, out = args.api.resolve(), args.certification.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((cert / 'manifest.json').read_text())
    assert manifest['status'] == 'passed'
    expected = {}
    for name in ('rqm-compiler', 'rqm-entanglement', 'rqm-qiskit'):
        module = name.replace('-', '_')
        wheel = next((cert / 'wheels').glob(module + '-*.whl'))
        assert hashlib.sha256(wheel.read_bytes()).hexdigest() == manifest['wheels'][wheel.name]
        with zipfile.ZipFile(wheel) as z:
            expected[name] = {n[len(module)+1:]: hashlib.sha256(z.read(n)).hexdigest()
                              for n in z.namelist() if n.startswith(module + '/') and n.endswith('.py')}
        loaded = Path(importlib.import_module(module).__file__).parent
        assert loaded.is_relative_to(cert / 'venv'), str(loaded)
        actual = {str(f.relative_to(loaded)): hashlib.sha256(f.read_bytes()).hexdigest()
                  for f in loaded.rglob('*.py')}
        assert actual == expected[name], name
    qualification = out / 'wheel-source-qualification.json'
    qualification.write_text(json.dumps({'sources': expected, 'wheels': manifest['wheels']}, indent=2)+'\n')
    sys.path.insert(0, str(api))
    unitary = importlib.import_module('scripts.compiler_cross_provider_preflight_0_3_7')
    unitary.OUT = out / 'unitary'
    unitary_exit = unitary.main(qualification_path=qualification)
    measurement = importlib.import_module('scripts.compiler_measurement_contract_0_4_0')
    measurement.OUT = out / 'measurement'
    measurement_exit = measurement.main()
    summary = {'unitary_exit': unitary_exit, 'measurement_exit': measurement_exit,
               'unitary': json.loads((unitary.OUT/'results.json').read_text())['summary'],
               'measurement': json.loads((measurement.OUT/'results.json').read_text())['summary'],
               'qualified_source_parity': json.loads((unitary.OUT/'results.json').read_text())['qualified_source_parity']}
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    return int(bool(unitary_exit or measurement_exit))


if __name__ == '__main__':
    raise SystemExit(main())
