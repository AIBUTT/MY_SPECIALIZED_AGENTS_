"""Focused public exporter adoption, conflict and offline rendering tests."""

import argparse
import base64
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest
from test_kit import boot_args, kit

CONDA = Path("C:/Users/10550/AppData/Local/anaconda3/Scripts/conda.exe")


def args(target, **kwargs):
    return argparse.Namespace(target=target, stage=False, apply=False, accept_local=[], **kwargs)


def snapshot(target):
    return {p.relative_to(target).as_posix(): p.read_bytes()
            for p in target.rglob("*") if p.is_file()}


def update(target, *, apply=False, stage=False, accept=()):
    values = args(target)
    values.apply, values.stage, values.accept_local = apply, stage, list(accept)
    return kit.update_components(values)


def test_preview_then_apply_existing_and_reapply(tmp_path):
    original = tmp_path / ".github" / "copilot-instructions.md"
    original.parent.mkdir()
    original.write_text("# Customized instructions\nKeep every local rule.\n", encoding="utf-8")
    kit.bootstrap(boot_args(tmp_path, "existing"))
    marker_path = tmp_path / kit.MARKER
    marker = json.loads(marker_path.read_text("utf-8"))
    marker["kit_version"] = "1.0.1"
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    before = snapshot(tmp_path)
    assert update(tmp_path)["status"] == "preview"
    assert snapshot(tmp_path) == before
    update(tmp_path, apply=True)
    assert original.read_bytes() == before[".github/copilot-instructions.md"]
    marker = json.loads(marker_path.read_text("utf-8"))
    assert marker["kit_version"] == "1.0.1"  # not a wholesale workspace migration
    assert marker["components"]["portable_docs"]["version"] == "1.1.0"
    installed = snapshot(tmp_path)
    update(tmp_path, apply=True)
    assert snapshot(tmp_path) == installed
    assert (tmp_path / "scripts" / "portable_docs.py").read_bytes() == (
        kit.COMPONENT / "portable_docs.py"
    ).read_bytes()


def test_conflicts_proposals_and_explicit_merged_acceptance(tmp_path):
    kit.bootstrap(boot_args(tmp_path, "existing"))
    custom = tmp_path / "docs" / "PORTABLE_DOCS.md"
    custom.parent.mkdir()
    custom.write_text("# Local guide\nKeep this content.\n", encoding="utf-8")
    before = snapshot(tmp_path)
    plan = update(tmp_path)
    row = next(r for r in plan["files"] if r["path"] == "docs/PORTABLE_DOCS.md")
    assert row["action"] == "conflict" and row["base_sha256"] is None
    assert row["local_sha256"] and row["new_sha256"]
    with pytest.raises(kit.KitError, match="conflicts"):
        update(tmp_path, apply=True)
    assert snapshot(tmp_path) == before
    update(tmp_path, stage=True)
    assert custom.read_bytes() == before["docs/PORTABLE_DOCS.md"]
    proposal = tmp_path / kit.PROPOSALS / "portable-docs-1.1.0" / "docs" / "PORTABLE_DOCS.md"
    assert proposal.is_file()
    custom.write_bytes(custom.read_bytes() + proposal.read_bytes())
    update(tmp_path, apply=True, accept=["docs/PORTABLE_DOCS.md"])
    assert "Keep this content." in custom.read_text("utf-8")
    after = snapshot(tmp_path)
    update(tmp_path, apply=True)
    assert snapshot(tmp_path) == after


def test_future_component_upgrade_does_not_clobber_customized_files(tmp_path, monkeypatch):
    kit.bootstrap(boot_args(tmp_path, "existing"))
    update(tmp_path, apply=True)
    custom = tmp_path / "scripts" / "portable_docs.py"
    custom.write_bytes(custom.read_bytes() + b"\n# Local policy\n")
    update(tmp_path, apply=True)
    before = snapshot(tmp_path)
    files = kit.component_files()
    files["scripts/portable_docs.py"] += b"\n# New upstream\n"
    monkeypatch.setattr(kit, "component_files", lambda: files)
    plan = update(tmp_path)
    assert next(r for r in plan["files"] if r["path"] == "scripts/portable_docs.py")[
        "action"
    ] == "conflict"
    with pytest.raises(kit.KitError):
        update(tmp_path, apply=True)
    assert snapshot(tmp_path) == before


def test_legacy_refusal_and_guarded_core_vendoring(tmp_path):
    with pytest.raises(kit.KitError, match="legacy"):
        update(tmp_path)
    assert not list(tmp_path.iterdir())
    values = argparse.Namespace(target=tmp_path, path="scripts/portable_docs.py",
                                apply=False, expected_sha256=None)
    assert kit.vendor_core(values)["status"] == "preview"
    assert not list(tmp_path.iterdir())
    values.apply = True
    kit.vendor_core(values)
    dest = tmp_path / values.path
    dest.write_bytes(b"# customized\n")
    with pytest.raises(kit.KitError):
        kit.vendor_core(values)
    values.expected_sha256 = kit.sha256_bytes(dest.read_bytes())
    kit.vendor_core(values)
    assert dest.read_bytes() == (kit.COMPONENT / "portable_docs.py").read_bytes()


def test_shared_chat_rule_and_no_private_runtime_dependency(tmp_path):
    kit.bootstrap(boot_args(tmp_path, "greenfield"))
    update(tmp_path, apply=True)
    rule = tmp_path / ".github" / "instructions" / "chat-equations.instructions.md"
    text = rule.read_text("utf-8")
    assert 'applyTo: "**"' in text and "All roles" in text and "plain ASCII" in text
    assert "Preserve LaTeX" in text
    for relative in ("scripts/portable_docs.py", "scripts/build_portable_docs.py"):
        source = (tmp_path / relative).read_text("utf-8")
        assert ".github" not in source
        assert "neusoft" not in source.lower()


def test_component_paths_reject_symlink_escape(tmp_path):
    kit.bootstrap(boot_args(tmp_path, "existing"))
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    try:
        (tmp_path / "scripts").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation unavailable")
    with pytest.raises(kit.KitError, match="symlink"):
        update(tmp_path, apply=True)
    assert not list(outside.iterdir())


def test_generic_deployed_export_with_pinned_cached_assets(tmp_path):
    """Optional real-asset fixture; no network and no project documents are consumed."""
    cache = os.environ.get("PORTABLE_DOCS_TEST_CACHE")
    if not cache:
        pytest.skip("Set PORTABLE_DOCS_TEST_CACHE to verified public MathJax asset cache")
    kit.bootstrap(boot_args(tmp_path, "greenfield"))
    conda = os.environ.get("CONDA_EXE") or str(CONDA)
    cli = [conda, "run", "-n", "lhl_discovery", "python",
           str(kit.KIT_ROOT / "tools" / "kit_render.py"),
           "update-components", "--target", str(tmp_path)]
    before = snapshot(tmp_path)
    preview = subprocess.run(cli, capture_output=True, text=True, check=False)
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert snapshot(tmp_path) == before
    installed = subprocess.run([*cli, "--apply"], capture_output=True, text=True, check=False)
    assert installed.returncode == 0, installed.stdout + installed.stderr
    reports = tmp_path / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "summary.md").write_text(
        "# Generic study\n\n$x = 1$\n\n![One pixel](pixel.png)\n\n"
        "[Outside selection](other.md)\n", encoding="utf-8",
    )
    (reports / "other.md").write_text("# Not selected\n", encoding="utf-8")
    (reports / "pixel.png").write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII="
    ))
    result = subprocess.run(
        [conda, "run", "-n", "lhl_discovery", "python", str(tmp_path / "scripts" / "build_docs.py"),
         "--portable", "--include", "reports/summary.md", "--name", "generic-study",
         "--version", "1", "--date", "2026-11-05", "--cache", cache],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    folder = tmp_path / "build" / "generic-study_v1_2026-11-05"
    manifest = json.loads((folder / "portable-manifest.json").read_text("utf-8"))
    assert manifest["selection"] == ["reports/summary.md"]
    assert manifest["figures"] == {"reports/summary.md": 1}
    assert not (folder / "reports" / "other.html").exists()
    checker = os.environ.get("PORTABLE_DOCS_TEST_CHECKER")
    browser = os.environ.get("PORTABLE_DOCS_TEST_BROWSER")
    if checker and browser:
        spec = importlib.util.spec_from_file_location("offline_checker", checker)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        evidence = module.verify(folder.with_suffix(".zip"), Path(browser))
        assert sum(r["images"] for r in evidence["pages"]) == 1
        assert sum(r["svg_equations"] for r in evidence["pages"]) == 1


@pytest.mark.parametrize("source", [
    ".private/note.md", "data/note.md", "../note.md", "reports/missing.md",
])
def test_generic_selection_rejects_invalid_sources(tmp_path, source):
    spec = importlib.util.spec_from_file_location("generic_core", kit.COMPONENT / "portable_docs.py")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    with pytest.raises(ValueError):
        core.select_sources(tmp_path, [source])


@pytest.mark.parametrize("labels", [
    ("bad/name", "1", "2026-11-05"), ("study", "../1", "2026-11-05"),
    ("study", "1", "2026-02-30"), ("study", None, None),
])
def test_generic_version_labels(labels):
    spec = importlib.util.spec_from_file_location("generic_core", kit.COMPONENT / "portable_docs.py")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    with pytest.raises(ValueError):
        core.package_stem(*labels)
