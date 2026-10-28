"""Maintain the handoff ledger and report the environment package-list hash.

Usage (from the repository root):
    python .github/scripts/ledger.py append .github/handoffs/<run_id>/<NN>_<stage>.json
    python .github/scripts/ledger.py check
    python .github/scripts/ledger.py env-hash

The JSON handoff files are the source of truth; the ledger is an index of validated
handoffs. Only the Coordinator appends rows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFFS = ROOT / ".github" / "handoffs"
LEDGER = HANDOFFS / "ledger.csv"
COLUMNS = [
    "timestamp_utc", "run_id", "stage", "agent", "configured_model", "actual_model", "status",
    "ready_for_next_stage", "n_inputs", "n_outputs", "n_checks_failed", "n_unresolved_blocking",
    "n_assumptions_changed", "n_lessons", "package_list_sha256", "handoff_path", "handoff_sha256",
]
REQUIRED = [
    "run_id", "stage", "agent", "configured_model", "actual_model", "timestamp_utc", "status",
    "environment", "inputs", "commands", "outputs", "files_changed", "checks",
    "scientific_assumptions_changed", "unresolved", "lessons", "ready_for_next_stage",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows() -> list[dict[str, str]]:
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def row_for(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [field for field in REQUIRED if field not in data]
    if missing:
        raise ValueError(f"{path.name} is missing fields: {missing}")
    expected_folder = data["run_id"]
    if path.parent.name != expected_folder:
        raise ValueError(f"{path.name}: run_id {expected_folder!r} differs from its folder")
    if not path.stem.startswith(data["stage"]):
        raise ValueError(f"{path.name}: stage {data['stage']!r} differs from its file name")
    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_id": data["run_id"],
        "stage": data["stage"],
        "agent": data["agent"],
        "configured_model": data["configured_model"],
        "actual_model": data["actual_model"],
        "status": data["status"],
        "ready_for_next_stage": str(bool(data["ready_for_next_stage"])).lower(),
        "n_inputs": str(len(data["inputs"])),
        "n_outputs": str(len(data["outputs"])),
        "n_checks_failed": str(sum(1 for check in data["checks"] if not check.get("passed"))),
        "n_unresolved_blocking": str(sum(
            1 for item in data["unresolved"] if isinstance(item, dict) and item.get("blocking")
        )),
        "n_assumptions_changed": str(len(data["scientific_assumptions_changed"])),
        "n_lessons": str(len(data["lessons"])),
        "package_list_sha256": data["environment"].get("package_list_sha256", ""),
        "handoff_path": path.relative_to(ROOT).as_posix(),
        "handoff_sha256": sha256(path),
    }


def append(handoff: Path) -> int:
    path = handoff if handoff.is_absolute() else ROOT / handoff
    path = path.resolve()
    row = row_for(path)
    rows = read_rows()
    last = [r for r in rows if r["handoff_path"] == row["handoff_path"]]
    if last and last[-1]["handoff_sha256"] == row["handoff_sha256"]:
        print(json.dumps({"status": "unchanged", "handoff": row["handoff_path"]}))
        return 0
    new_file = not LEDGER.exists()
    with LEDGER.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    print(json.dumps({"status": "appended", "handoff": row["handoff_path"],
                      "ready_for_next_stage": row["ready_for_next_stage"]}))
    return 0


def check() -> list[str]:
    """Return problems: unrecorded handoffs, changed handoffs, rows without a file."""
    rows = read_rows()
    last: dict[str, dict[str, str]] = {}
    for row in rows:
        last[row["handoff_path"]] = row
    problems = []
    files = sorted(p for p in HANDOFFS.glob("*/*.json"))
    for path in files:
        key = path.relative_to(ROOT).as_posix()
        if key not in last:
            problems.append(f"not in ledger: {key}")
        elif last[key]["handoff_sha256"] != sha256(path):
            problems.append(f"changed after its last ledger row: {key}")
    present = {path.relative_to(ROOT).as_posix() for path in files}
    problems.extend(f"ledger row without file: {key}" for key in sorted(set(last) - present))
    return problems


def env_hash() -> dict[str, object]:
    packages = sorted(
        f"{dist.metadata['Name'].lower()}=={dist.version}"
        for dist in importlib.metadata.distributions()
        if dist.metadata["Name"]
    )
    text = "\n".join([f"python=={sys.version.split()[0]}", *packages])
    return {
        "python": sys.version.split()[0],
        "n_packages": len(packages),
        "package_list_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("append", help="Append a validated handoff to the ledger.")
    add.add_argument("handoff", type=Path)
    sub.add_parser("check", help="Compare the ledger with the handoff files.")
    sub.add_parser("env-hash", help="Print the package-list hash of the running environment.")
    args = parser.parse_args()

    if args.command == "append":
        try:
            return append(args.handoff)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(json.dumps({"status": "failed", "error": str(error)}))
            return 1
    if args.command == "check":
        problems = check()
        print(json.dumps({"status": "failed" if problems else "passed", "problems": problems},
                         indent=2))
        return 1 if problems else 0
    print(json.dumps(env_hash(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
