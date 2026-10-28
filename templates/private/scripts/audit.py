"""Read-only health check of the private agent workspace.

Usage (from the repository root):
    python .github/scripts/audit.py

Prints one line per check (pass, warn, fail) and exits with 1 if any check fails.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITHUB = ROOT / ".github"
MARKER = GITHUB / "agents" / ".kit.json"
SKIP_PARTS = {".git", "_site", "_proposals", "__pycache__"}
PLACEHOLDER = re.compile(r"\{\{(?:FILL:[^}]*|\w+)\}\}")
LEAK = re.compile(r"\bcopilot\b|\.github[/\\]|\.agent\.md|AGENT_GUIDE|\.kit\.json", re.IGNORECASE)
PEER_SUFFIXES = {".md", ".py", ".ipynb", ".yaml", ".yml", ".toml", ".json", ".txt", ".cfg", ".sql"}
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
REQUIRED_KEYS = ("name", "description", "model", "tools", "user-invocable")
MAX_SCAN_BYTES = 2_000_000


def git(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def result(name: str, status: str, detail: str = "") -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def private_files(suffixes: tuple[str, ...]) -> list[Path]:
    return [
        path for path in sorted(GITHUB.rglob("*"))
        if path.is_file() and path.suffix in suffixes
        and not SKIP_PARTS.intersection(path.relative_to(GITHUB).parts)
    ]


def load_marker() -> dict | None:
    if not MARKER.exists():
        return None
    return json.loads(MARKER.read_text(encoding="utf-8"))


def check_marker(marker: dict | None) -> dict[str, str]:
    if marker is None:
        return result("marker", "fail", "missing .github/agents/.kit.json")
    return result("marker", "pass", f"kit v{marker.get('kit_version')}, mode {marker.get('mode')}")


def check_outer_git() -> list[dict[str, str]]:
    dot_git = ROOT / ".git"
    if not dot_git.is_dir():
        return [result("outer repository", "warn",
                       "no .git folder; exclusion and hook not checked")]
    checks = []
    exclude = dot_git / "info" / "exclude"
    lines = exclude.read_text(encoding="utf-8").splitlines() if exclude.exists() else []
    patterns = {".github", ".github/", "/.github", "/.github/"}
    excluded = any(line.strip() in patterns for line in lines)
    checks.append(result("exclusion", "pass" if excluded else "fail",
                         "" if excluded else ".github/ is not in .git/info/exclude"))
    tracked = git("ls-files", "--", ".github").stdout.split()
    checks.append(result("outer tracking", "fail" if tracked else "pass",
                         f"{len(tracked)} tracked path(s) under .github" if tracked else ""))
    hook = dot_git / "hooks" / "pre-commit"
    has_hook = hook.exists() and "agent kit" in hook.read_text(encoding="utf-8", errors="ignore")
    checks.append(result("pre-commit hook", "pass" if has_hook else "warn",
                         "" if has_hook else "kit pre-commit hook not installed"))
    return checks


def check_inner_repo() -> dict[str, str]:
    if not (GITHUB / ".git").exists():
        return result("private history", "fail", ".github has no local repository")
    status = git("status", "--porcelain", cwd=GITHUB)
    if status.returncode != 0:
        return result("private history", "fail", status.stderr.strip())
    changed = [line for line in status.stdout.splitlines() if line.strip()]
    if changed:
        return result("private history", "warn", f"{len(changed)} uncommitted change(s)")
    return result("private history", "pass")


def parse_front_matter(text: str) -> dict[str, str]:
    match = FRONT_MATTER.match(text)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip('"')
    return fields


def check_agents(marker: dict | None) -> list[dict[str, str]]:
    checks = []
    expected = {role["name"]: role["model"] for role in (marker or {}).get("roles", [])}
    seen = set()
    for path in sorted((GITHUB / "agents").glob("*.agent.md")):
        fields = parse_front_matter(path.read_text(encoding="utf-8"))
        missing = [key for key in REQUIRED_KEYS if key not in fields]
        name = fields.get("name", path.name)
        seen.add(name)
        if missing:
            checks.append(result(f"front matter {path.name}", "fail", f"missing {missing}"))
        elif name in expected and fields["model"] != expected[name]:
            checks.append(result(f"front matter {path.name}", "warn",
                                 f"model {fields['model']!r}; marker records {expected[name]!r}"))
        else:
            checks.append(result(f"front matter {path.name}", "pass"))
    for name in sorted(set(expected) - seen):
        checks.append(result("roster", "fail", f"role {name!r} in marker has no agent file"))
    return checks


def check_placeholders() -> dict[str, str]:
    hits = []
    for path in private_files((".md", ".json", ".py", ".csv")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if PLACEHOLDER.search(line):
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{number}")
    if hits:
        return result("placeholders", "fail", f"{len(hits)} unfilled: " + ", ".join(hits[:10]))
    return result("placeholders", "pass")


def peer_files(module_name: str | None) -> list[Path]:
    roots = [ROOT / "README.md", ROOT / "docs", ROOT / "reports", ROOT / "notebooks",
             ROOT / "scripts", ROOT / "configs", ROOT / "src"]
    if module_name:
        roots.append(ROOT / module_name)
    files = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(p for p in sorted(root.rglob("*"))
                         if p.is_file() and p.suffix in PEER_SUFFIXES
                         and "__pycache__" not in p.parts and ".ipynb_checkpoints" not in p.parts)
    return [p for p in files if p.stat().st_size <= MAX_SCAN_BYTES]


def check_leaks(marker: dict | None) -> dict[str, str]:
    module_name = (marker or {}).get("values", {}).get("module_name")
    hits = []
    for path in peer_files(module_name):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for number, line in enumerate(text.splitlines(), start=1):
            if LEAK.search(line):
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{number}")
    if hits:
        return result("peer-file leaks", "fail", f"{len(hits)} hit(s): " + ", ".join(hits[:10]))
    return result("peer-file leaks", "pass")


def outputs_table(text: str) -> list[str]:
    section = re.search(r"^## Outputs\s*\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    if not section:
        return []
    locations = []
    for line in section.group(1).splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and not set(cells[1]) <= {"-", " "} and cells[1] != "Location":
            locations.extend(re.findall(r"`([^`]+)`", cells[1]))
    return locations


def check_ownership() -> dict[str, str]:
    owners: dict[str, list[str]] = {}
    for path in sorted((GITHUB / "agents").glob("*.agent.md")):
        for location in outputs_table(path.read_text(encoding="utf-8")):
            if location.startswith(".github/handoffs/"):
                continue
            owners.setdefault(location, []).append(path.stem.removesuffix(".agent"))
    shared = {loc: names for loc, names in owners.items() if len(names) > 1}
    if shared:
        detail = "; ".join(f"{loc}: {', '.join(names)}" for loc, names in sorted(shared.items()))
        return result("output ownership", "warn", detail)
    return result("output ownership", "pass")


def check_ledger() -> dict[str, str]:
    path = GITHUB / "scripts" / "ledger.py"
    if not path.exists():
        return result("ledger", "fail", "missing .github/scripts/ledger.py")
    spec = importlib.util.spec_from_file_location("ledger", path)
    ledger = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger)
    problems = ledger.check()
    if problems:
        return result("ledger", "warn", "; ".join(problems[:10]))
    return result("ledger", "pass")


def main() -> int:
    marker = load_marker()
    checks = [check_marker(marker), *check_outer_git(), check_inner_repo(),
              *check_agents(marker), check_placeholders(), check_leaks(marker),
              check_ownership(), check_ledger()]
    for item in checks:
        line = f"{item['status'].upper():5} {item['check']}"
        print(f"{line}: {item['detail']}" if item["detail"] else line)
    failed = sum(item["status"] == "fail" for item in checks)
    warned = sum(item["status"] == "warn" for item in checks)
    print(f"\n{len(checks)} checks: {failed} failed, {warned} warnings")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
