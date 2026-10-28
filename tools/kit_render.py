"""Render the agent kit into a repository. Creates files only; never overwrites.

Examples (run from any folder; Python 3.10 or later, standard library only):
    python tools/kit_render.py bootstrap --target C:/work/repo --mode existing \
        --project-name "Demo study" --module-name demo --conda-env DS_002 \
        --roles "Coordinator,Researcher,Data Engineer,Statistical Reviewer" --dry-run
    python tools/kit_render.py add-role --target C:/work/repo --role Visualizer

Exit codes: 0 success, 1 invalid arguments, 2 already bootstrapped, 3 outer repository
tracks .github, 4 greenfield target not empty, 5 git unavailable, 6 not bootstrapped,
7 file conflict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
KIT_META = json.loads((KIT_ROOT / "kit.json").read_text(encoding="utf-8"))
TEMPLATES = KIT_ROOT / "templates"
PRIVATE = TEMPLATES / "private"
HOOK = TEMPLATES / "hooks" / "pre-commit"
SKELETON = KIT_ROOT / "skeleton" / "ccds_v2_minimal"
ROLES = json.loads((TEMPLATES / "roles.json").read_text(encoding="utf-8"))
ROLE_BY_NAME = {role["name"]: role for role in ROLES}

MARKER = Path(".github") / "agents" / ".kit.json"
PROPOSALS = Path(".github") / "agents" / "_proposals"
TOKEN = re.compile(r"\{\{(\w+)\}\}")
FILL = re.compile(r"\{\{FILL:")
MODULE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
SAFE_TEXT = re.compile(r'^[^"\n\x5c{}]+$')
CONDA_ENV = re.compile(r"^[A-Za-z0-9_.-]+$")
PYTHON_VERSION = re.compile(r"^3\.\d{1,2}$")
GREENFIELD_ALLOWED = {".git", ".gitignore", ".gitattributes", ".vscode", "README.md", "LICENSE"}


class KitError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def substitute(text: str, values: dict[str, str], where: str) -> str:
    unknown: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            unknown.append(key)
            return match.group(0)
        return values[key]

    rendered = TOKEN.sub(replace, text)
    if unknown:
        raise KitError(1, f"{where}: unknown placeholder(s) {sorted(set(unknown))}")
    return rendered


def roles_table(names: list[str], base: dict[str, str]) -> str:
    rows = []
    for role in ROLES:
        if role["name"] not in names:
            continue
        handoffs = ", ".join(re.sub(r"(\S+\.json)", r"`\1`", h) for h in role["handoffs"])
        rows.append(f"| **{role['name']}** | `{role['model']}` | {role['stage']} | "
                    f"{handoffs} | {role['writes']} |")
    return substitute("\n".join(rows), base, "roles.json")


def parse_roles(text: str) -> list[str]:
    names = [name.strip() for name in text.split(",") if name.strip()]
    unknown = [name for name in names if name not in ROLE_BY_NAME]
    if unknown:
        raise KitError(1, f"unknown role(s) {unknown}; choose from {list(ROLE_BY_NAME)}")
    missing = [r["name"] for r in ROLES if r["required"] and r["name"] not in names]
    if missing:
        raise KitError(1, f"required role(s) missing: {missing}")
    return [r["name"] for r in ROLES if r["name"] in names]


def validate_values(args: argparse.Namespace) -> dict[str, str]:
    checks = [
        ("--module-name", args.module_name, MODULE_NAME),
        ("--project-name", args.project_name, SAFE_TEXT),
        ("--description", args.description, SAFE_TEXT),
        ("--conda-env", args.conda_env, CONDA_ENV),
        ("--python-version", args.python_version, PYTHON_VERSION),
    ]
    for flag, value, pattern in checks:
        if not pattern.match(value):
            raise KitError(1, f"{flag} {value!r} is not allowed (pattern {pattern.pattern})")
    return {
        "project_name": args.project_name,
        "module_name": args.module_name,
        "conda_env": args.conda_env,
        "python_version": args.python_version,
        "description": args.description,
        "kit_version": KIT_META["kit_version"],
        "ccds_version": KIT_META["ccds_version"],
        "bootstrap_date": utc_now()[:10],
    }


def template_items(mode: str, role_names: list[str]) -> list[tuple[Path, Path]]:
    selected = {ROLE_BY_NAME[name]["file"] for name in role_names}
    items = []
    for src in sorted(PRIVATE.rglob("*")):
        rel = src.relative_to(PRIVATE)
        if not src.is_file() or "__pycache__" in rel.parts:
            continue
        if rel.name.endswith(".agent.md") and rel.name not in selected:
            continue
        items.append((src, Path(".github") / rel))
    if mode == "greenfield":
        for src in sorted(SKELETON.rglob("*")):
            rel = src.relative_to(SKELETON)
            if src.is_file() and "__pycache__" not in rel.parts:
                items.append((src, rel))
    return items


def render(items: list[tuple[Path, Path]], values: dict[str, str]) -> list[tuple[Path, bytes]]:
    rendered = []
    for src, dest in items:
        where = src.relative_to(KIT_ROOT).as_posix()
        dest_rel = Path(substitute(dest.as_posix(), values, where))
        text = substitute(src.read_text(encoding="utf-8"), values, where)
        rendered.append((dest_rel, text.encode("utf-8")))
    return rendered


def preflight(target: Path, mode: str, no_git: bool) -> None:
    if not target.is_dir():
        raise KitError(1, f"target is not a folder: {target}")
    if (target / MARKER).exists():
        raise KitError(2, "already bootstrapped (.github/agents/.kit.json exists); "
                          "use /evolve-agents or /audit-agents")
    if mode == "greenfield":
        unexpected = sorted(p.name for p in target.iterdir() if p.name not in GREENFIELD_ALLOWED)
        if unexpected:
            raise KitError(4, f"greenfield target is not empty: {unexpected[:10]}; "
                              "use --mode existing")
    if no_git:
        return
    if git("--version").returncode != 0:
        raise KitError(5, "git is not available on PATH")
    if (target / ".git").is_dir():
        tracked = git("-C", str(target), "ls-files", "--", ".github").stdout.split()
        if tracked:
            raise KitError(3, f"the outer repository tracks {len(tracked)} path(s) under "
                              ".github; private-by-default cannot be applied")


def write_files(target: Path, rendered: list[tuple[Path, bytes]]) -> dict[str, list]:
    report: dict[str, list] = {"created": [], "proposals": [], "skipped": [], "fill": []}
    for dest_rel, data in rendered:
        dest = target / dest_rel
        if dest.exists():
            proposal = target / PROPOSALS / dest_rel
            if proposal.exists():
                report["skipped"].append(dest_rel.as_posix())
                continue
            proposal.parent.mkdir(parents=True, exist_ok=True)
            proposal.write_bytes(data)
            report["proposals"].append((PROPOSALS / dest_rel).as_posix())
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        report["created"].append({"path": dest_rel.as_posix(), "sha256": sha256_bytes(data)})
        count = len(FILL.findall(data.decode("utf-8")))
        if count:
            report["fill"].append({"path": dest_rel.as_posix(), "count": count})
    return report


def setup_outer_git(target: Path) -> dict[str, str]:
    dot_git = target / ".git"
    if not dot_git.is_dir():
        return {"outer": "no repository; exclusion and hook not installed"}
    exclude = dot_git / "info" / "exclude"
    lines = exclude.read_text(encoding="utf-8").splitlines() if exclude.exists() else []
    if any(line.strip() in {".github", ".github/", "/.github", "/.github/"} for line in lines):
        exclusion = "already present"
    else:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        prefix = "" if not lines or exclude.read_bytes().endswith(b"\n") else "\n"
        with exclude.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(f"{prefix}# agent kit: private workspace\n.github/\n")
        exclusion = "added"
    hook = dot_git / "hooks" / "pre-commit"
    if hook.exists():
        proposal = target / PROPOSALS / "hooks" / "pre-commit"
        proposal.parent.mkdir(parents=True, exist_ok=True)
        proposal.write_bytes(HOOK.read_bytes())
        hook_status = f"existing hook kept; kit hook written to {PROPOSALS.as_posix()}/hooks/"
    else:
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_bytes(HOOK.read_bytes())
        hook_status = "installed"
    return {"exclusion": exclusion, "hook": hook_status}


def commit_inner(target: Path, message: str) -> str:
    inner = target / ".github"
    if not (inner / ".git").exists():
        init = git("-C", str(inner), "init", "-b", "main")
        if init.returncode != 0:
            return f"init failed: {init.stderr.strip()}"
    git("-C", str(inner), "add", "-A")
    commit = git("-C", str(inner), "commit", "-m", message)
    if commit.returncode != 0:
        return f"commit failed: {(commit.stderr or commit.stdout).strip()}"
    return git("-C", str(inner), "rev-parse", "--short", "HEAD").stdout.strip()


def bootstrap(args: argparse.Namespace) -> dict:
    target = args.target.resolve()
    preflight(target, args.mode, args.no_git)
    values = validate_values(args)
    names = parse_roles(args.roles)
    values["agent_list"] = json.dumps([n for n in names if n != "Coordinator"])
    values["roles_table"] = roles_table(names, values)
    rendered = render(template_items(args.mode, names), values)

    if args.dry_run:
        plan = []
        for dest_rel, _ in rendered:
            exists = (target / dest_rel).exists()
            action = "proposal" if exists else "create"
            plan.append({"path": dest_rel.as_posix(), "action": action})
        return {"status": "dry-run", "mode": args.mode, "roles": names, "files": plan}

    report = write_files(target, rendered)
    git_report = {} if args.no_git else setup_outer_git(target)
    marker = {
        "kit_version": KIT_META["kit_version"],
        "kit_root": KIT_ROOT.as_posix(),
        "ccds_version": KIT_META["ccds_version"],
        "mode": args.mode,
        "bootstrapped_utc": utc_now(),
        "values": {k: values[k] for k in
                   ("project_name", "module_name", "conda_env", "python_version", "description")},
        "roles": [{"name": n, "model": ROLE_BY_NAME[n]["model"], "file": ROLE_BY_NAME[n]["file"]}
                  for n in names],
        "created": report["created"],
        "proposals": report["proposals"],
        "skipped": report["skipped"],
        "git": git_report,
        "evolutions": [],
    }
    marker_path = target / MARKER
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_bytes((json.dumps(marker, indent=2) + "\n").encode("utf-8"))
    if not args.no_git:
        git_report["inner_commit"] = commit_inner(
            target, f"bootstrap: agent kit v{KIT_META['kit_version']} ({args.mode})")
    return {
        "status": "created",
        "mode": args.mode,
        "roles": names,
        "created": len(report["created"]),
        "proposals": report["proposals"],
        "skipped": report["skipped"],
        "fill_tokens": report["fill"],
        "git": git_report,
    }


def add_role(args: argparse.Namespace) -> dict:
    target = args.target.resolve()
    marker_path = target / MARKER
    if not marker_path.exists():
        raise KitError(6, "not bootstrapped; run /bootstrap-agents first")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if args.role not in ROLE_BY_NAME:
        raise KitError(1, f"unknown role {args.role!r}; choose from {list(ROLE_BY_NAME)}")
    if any(role["name"] == args.role for role in marker["roles"]):
        raise KitError(7, f"role {args.role!r} is already in the roster")
    role = ROLE_BY_NAME[args.role]
    dest_rel = Path(".github") / "agents" / role["file"]
    if (target / dest_rel).exists():
        raise KitError(7, f"{dest_rel.as_posix()} already exists")
    values = {**marker["values"], "kit_version": marker["kit_version"],
              "ccds_version": marker["ccds_version"],
              "bootstrap_date": marker["bootstrapped_utc"][:10]}
    src = PRIVATE / "agents" / role["file"]
    data = substitute(src.read_text(encoding="utf-8"), values, role["file"]).encode("utf-8")
    if args.dry_run:
        return {"status": "dry-run", "create": dest_rel.as_posix()}
    (target / dest_rel).write_bytes(data)
    marker["roles"].append({"name": role["name"], "model": role["model"], "file": role["file"]})
    marker["evolutions"].append({"utc": utc_now(), "action": "add-role", "role": role["name"],
                                 "kit_version": KIT_META["kit_version"],
                                 "sha256": sha256_bytes(data)})
    marker_path.write_bytes((json.dumps(marker, indent=2) + "\n").encode("utf-8"))
    return {
        "status": "created",
        "file": dest_rel.as_posix(),
        "fill_tokens": len(FILL.findall(data.decode("utf-8"))),
        "follow_up": [
            "add the role to the Coordinator 'agents' list",
            "add the role to the roles tables in copilot-instructions.md and AGENT_GUIDE.md",
            "record the change in .github/agents/CHANGELOG.md",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    boot = sub.add_parser("bootstrap", help="Create the private workspace (and skeleton).")
    boot.add_argument("--target", type=Path, required=True)
    boot.add_argument("--mode", choices=("existing", "greenfield"), required=True)
    boot.add_argument("--project-name", required=True)
    boot.add_argument("--module-name", required=True)
    boot.add_argument("--description", default="Data-science project.")
    boot.add_argument("--conda-env", default=KIT_META["default_conda_env"])
    boot.add_argument("--python-version", default=KIT_META["default_python_version"])
    boot.add_argument("--roles", required=True, help="Comma-separated role names.")
    boot.add_argument("--no-git", action="store_true", help="Skip all Git steps.")
    boot.add_argument("--dry-run", action="store_true", help="Print the plan; write nothing.")
    add = sub.add_parser("add-role", help="Add one agent file to a bootstrapped repository.")
    add.add_argument("--target", type=Path, required=True)
    add.add_argument("--role", required=True)
    add.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        result = bootstrap(args) if args.command == "bootstrap" else add_role(args)
    except KitError as error:
        print(json.dumps({"status": "refused", "code": error.code, "reason": str(error)},
                         indent=2))
        return error.code
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
