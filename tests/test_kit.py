"""Tests for the agent kit: rendering, refusal rules, ledger, audit, and template consistency.

Run from the kit root:
    python -m pytest -q
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


kit = load("kit_render", KIT_ROOT / "tools" / "kit_render.py")
SKELETON_TESTS = KIT_ROOT / "skeleton" / "ccds_v2_minimal" / "tests"
style = load("path_style", SKELETON_TESTS / "test_path_style.py")
ALL_ROLES = ",".join(role["name"] for role in kit.ROLES)
LEAK = re.compile(r"\bcopilot\b|\.github[/\\]|\.agent\.md|AGENT_GUIDE|\.kit\.json", re.IGNORECASE)


def boot_args(target: Path, mode: str, roles: str = ALL_ROLES, no_git: bool = True,
              dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(target=target, mode=mode, project_name="Demo study",
                              module_name="demo", description="Demo project.",
                              conda_env="DS_002", python_version="3.11", roles=roles,
                              no_git=no_git, dry_run=dry_run)


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def test_roles_match_agent_templates():
    templates = {p.name for p in (kit.PRIVATE / "agents").glob("*.agent.md")}
    assert templates == {role["file"] for role in kit.ROLES}
    for role in kit.ROLES:
        text = (kit.PRIVATE / "agents" / role["file"]).read_text(encoding="utf-8")
        assert f'name: {role["name"]}\n' in text
        assert f'model: "{role["model"]}"' in text
        assert "tools: [" + ", ".join(role["tools"]) + "]" in text
        assert "fifteen years" in text


def test_greenfield_render(tmp_path):
    result = kit.bootstrap(boot_args(tmp_path, "greenfield"))

    assert result["status"] == "created"
    assert (tmp_path / "demo" / "config.py").exists()
    assert (tmp_path / "data" / "raw" / ".gitkeep").exists()
    assert (tmp_path / ".github" / "agents" / ".kit.json").exists()
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert not kit.TOKEN.search(path.read_text(encoding="utf-8")), path
    coordinator = (tmp_path / ".github" / "agents" / "coordinator.agent.md").read_text("utf-8")
    assert 'agents: ["Data Steward", "Researcher"' in coordinator
    for path in tmp_path.rglob("*.py"):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_rendered_skeleton_tests_pass(tmp_path):
    kit.bootstrap(boot_args(tmp_path, "greenfield"))
    completed = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_peer_files_do_not_leak(tmp_path):
    kit.bootstrap(boot_args(tmp_path, "greenfield"))
    for path in tmp_path.rglob("*"):
        if path.is_file() and ".github" not in path.relative_to(tmp_path).parts:
            assert not LEAK.search(path.read_text(encoding="utf-8")), path


def test_second_bootstrap_is_refused(tmp_path):
    kit.bootstrap(boot_args(tmp_path, "greenfield"))
    with pytest.raises(kit.KitError) as error:
        kit.bootstrap(boot_args(tmp_path, "existing"))
    assert error.value.code == 2


def test_greenfield_refuses_non_empty_folder(tmp_path):
    (tmp_path / "analysis.py").write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(kit.KitError) as error:
        kit.bootstrap(boot_args(tmp_path, "greenfield"))
    assert error.value.code == 4


def test_existing_files_become_proposals(tmp_path):
    original = tmp_path / ".github" / "copilot-instructions.md"
    original.parent.mkdir(parents=True)
    original.write_text("keep me\n", encoding="utf-8")

    result = kit.bootstrap(boot_args(tmp_path, "existing"))

    assert original.read_text(encoding="utf-8") == "keep me\n"
    assert ".github/agents/_proposals/.github/copilot-instructions.md" in result["proposals"]
    assert not (tmp_path / "demo").exists()


def test_dry_run_writes_nothing(tmp_path):
    result = kit.bootstrap(boot_args(tmp_path, "greenfield", dry_run=True))
    assert result["status"] == "dry-run"
    assert list(tmp_path.iterdir()) == []


def test_roles_are_validated(tmp_path):
    with pytest.raises(kit.KitError):
        kit.bootstrap(boot_args(tmp_path, "existing", roles="Researcher"))
    with pytest.raises(kit.KitError):
        kit.bootstrap(boot_args(tmp_path, "existing", roles="Coordinator,Wizard"))


def test_add_role(tmp_path):
    kit.bootstrap(boot_args(tmp_path, "existing", roles="Coordinator,Researcher"))
    result = kit.add_role(argparse.Namespace(target=tmp_path, role="Visualizer", dry_run=False))
    assert result["file"] == ".github/agents/visualizer.agent.md"
    marker = json.loads((tmp_path / ".github" / "agents" / ".kit.json").read_text("utf-8"))
    assert [r["name"] for r in marker["roles"]][-1] == "Visualizer"
    assert marker["evolutions"][0]["action"] == "add-role"
    with pytest.raises(kit.KitError) as error:
        kit.add_role(argparse.Namespace(target=tmp_path, role="Visualizer", dry_run=False))
    assert error.value.code == 7


def test_ledger_append_and_check(tmp_path):
    kit.bootstrap(boot_args(tmp_path, "existing"))
    ledger_py = tmp_path / ".github" / "scripts" / "ledger.py"
    handoff = tmp_path / ".github" / "handoffs" / "20260101_demo" / "01_intake.json"
    handoff.parent.mkdir(parents=True)
    handoff.write_text(json.dumps({
        "run_id": "20260101_demo", "stage": "01_intake", "agent": "Data Steward",
        "configured_model": "GPT-6 Luna", "actual_model": "unknown",
        "timestamp_utc": "2026-01-01T00:00:00Z", "status": "accepted",
        "environment": {"conda_env": "DS_002", "package_list_sha256": "x", "git_revision": "y"},
        "inputs": [], "commands": [], "outputs": [], "files_changed": [],
        "checks": [{"name": "a", "command": "b", "result": "c", "passed": False}],
        "scientific_assumptions_changed": [], "unresolved": [{"item": "z", "blocking": True}],
        "lessons": [], "ready_for_next_stage": False,
    }), encoding="utf-8")

    assert run([sys.executable, str(ledger_py), "check"], tmp_path).returncode == 1
    assert run([sys.executable, str(ledger_py), "append", str(handoff)], tmp_path).returncode == 0
    assert run([sys.executable, str(ledger_py), "check"], tmp_path).returncode == 0
    rows = (tmp_path / ".github" / "handoffs" / "ledger.csv").read_text("utf-8").splitlines()
    assert len(rows) == 2 and ",1,1,0,0,x," in rows[1]
    handoff.write_text(handoff.read_text("utf-8") + " ", encoding="utf-8")
    assert run([sys.executable, str(ledger_py), "check"], tmp_path).returncode == 1
    env = run([sys.executable, str(ledger_py), "env-hash"], tmp_path)
    assert len(json.loads(env.stdout)["package_list_sha256"]) == 64


@pytest.mark.skipif(GIT is None, reason="git not available")
def test_git_setup_and_audit(tmp_path):
    run(["git", "init", "-b", "main"], tmp_path)
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    run(["git", "add", "README.md"], tmp_path)
    run(["git", "commit", "-m", "init"], tmp_path)

    result = kit.bootstrap(boot_args(tmp_path, "existing", no_git=False))

    assert result["git"]["exclusion"] == "added"
    assert result["git"]["hook"] == "installed"
    assert re.fullmatch(r"[0-9a-f]{7,}", result["git"]["inner_commit"])
    assert run(["git", "status", "--porcelain"], tmp_path).stdout.strip() == ""
    audit = run([sys.executable, str(tmp_path / ".github" / "scripts" / "audit.py")], tmp_path)
    failed = [line for line in audit.stdout.splitlines() if line.startswith("FAIL")]
    assert len(failed) == 1 and "placeholders" in failed[0], audit.stdout

    run(["git", "add", "-f", ".github"], tmp_path)
    hook = run(["git", "commit", "-m", "leak"], tmp_path)
    assert hook.returncode != 0 and "private" in hook.stderr


def test_kit_python_follows_path_style():
    failures = []
    for folder in ("tools", "tests", "templates"):
        for path in sorted((KIT_ROOT / folder).rglob("*.py")):
            failures.extend(style.path_violations(path.read_text(encoding="utf-8"),
                                                  path.relative_to(KIT_ROOT).as_posix()))
    assert not failures, failures
