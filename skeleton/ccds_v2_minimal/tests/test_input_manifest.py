from {{module_name}}.input_manifest import build_input_manifest, compare_manifests


def test_manifest_lists_files_with_hashes(tmp_path):
    (tmp_path / "a.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.csv").write_text("y\n2\n", encoding="utf-8")
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")

    manifest = build_input_manifest(tmp_path, hash_files=True)

    assert manifest["file_count"] == 2
    assert [record["path"] for record in manifest["files"]] == ["a.csv", "sub/b.csv"]
    assert all(len(record["sha256"]) == 64 for record in manifest["files"])


def test_compare_reports_added_removed_and_changed(tmp_path):
    (tmp_path / "keep.csv").write_text("1", encoding="utf-8")
    (tmp_path / "drop.csv").write_text("1", encoding="utf-8")
    old = build_input_manifest(tmp_path, hash_files=True)
    (tmp_path / "drop.csv").unlink()
    (tmp_path / "keep.csv").write_text("2", encoding="utf-8")
    (tmp_path / "new.csv").write_text("1", encoding="utf-8")
    new = build_input_manifest(tmp_path, hash_files=True)

    assert compare_manifests(old, new) == {
        "added": ["new.csv"], "removed": ["drop.csv"], "changed": ["keep.csv"]
    }
