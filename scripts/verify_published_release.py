"""Compare public release payloads with the retained certified wheels.

Run using Python 3.11+; no third-party imports are needed. Downloads use the
public PyPI JSON API and verify the advertised SHA-256 before inspecting bytes.
Archive hashes identify artifacts; runtime parity ignores archive timestamps
and distribution metadata, which are compared separately.
"""

import argparse
import hashlib
import json
import tarfile
import urllib.request
import zipfile
from email.parser import BytesParser
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def payload(path, namespace):
    with zipfile.ZipFile(path) as archive:
        return {
            name: digest(archive.read(name))
            for name in archive.namelist()
            if name.startswith(namespace + "/") and not name.endswith("/")
        }


def requirements(path):
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        metadata = BytesParser().parsebytes(archive.read(name))
        return sorted(metadata.get_all("Requires-Dist", []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certified-wheels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for name, version in [
        ("rqm-compiler", "0.3.7"),
        ("rqm-core", "0.2.2"),
        ("rqm-entanglement", "0.2.2"),
    ]:
        namespace = name.replace("-", "_")
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        with urllib.request.urlopen(url, timeout=60) as response:
            release = json.load(response)
        (args.output / f"{name}-pypi.json").write_text(
            json.dumps(release, indent=2) + "\n"
        )
        files = []
        for item in release["urls"]:
            with urllib.request.urlopen(item["url"], timeout=60) as response:
                data = response.read()
            assert digest(data) == item["digests"]["sha256"], item["filename"]
            path = args.output / item["filename"]
            path.write_bytes(data)
            files.append(
                {"filename": path.name, "sha256": digest(data), "url": item["url"]}
            )
        wheel = next(args.output.glob(f"{namespace}-{version}-*.whl"))
        certified = next(args.certified_wheels.glob(f"{namespace}-{version}-*.whl"))
        public_payload = payload(wheel, namespace)
        certified_payload = payload(certified, namespace)
        sdist = args.output / f"{namespace}-{version}.tar.gz"
        with tarfile.open(sdist) as archive:
            sdist_payload = {}
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                parts = member.name.split("/")
                if namespace in parts:
                    relative = "/".join(parts[parts.index(namespace) :])
                    sdist_payload[relative] = digest(archive.extractfile(member).read())
        row = {
            "package": name,
            "version": version,
            "files": files,
            "certified_wheel_sha256": digest(certified.read_bytes()),
            "runtime_file_count": len(public_payload),
            "runtime_payload_matches_certified": public_payload == certified_payload,
            "sdist_runtime_matches_wheel": sdist_payload == public_payload,
            "requires_dist": requirements(wheel),
            "requirements_match_certified": requirements(wheel)
            == requirements(certified),
            "runtime_sha256": public_payload,
        }
        results.append(row)
    result = {
        "packages": results,
        "passed": all(
            r["runtime_payload_matches_certified"]
            and r["sdist_runtime_matches_wheel"]
            and r["requirements_match_certified"]
            for r in results
        ),
    }
    (args.output / "artifact-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "packages": [
                    {
                        k: v
                        for k, v in r.items()
                        if k not in {"runtime_sha256", "requires_dist", "files"}
                    }
                    for r in results
                ],
            },
            indent=2,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
