"""Inventory and validate input files, and compare two input manifests.

Usage:
    python -m {{module_name}}.input_manifest
    python -m {{module_name}}.input_manifest --sha256 --write-manifest runs/<run_id>/input_manifest.json
    python -m {{module_name}}.input_manifest --compare OLD.json NEW.json

The SHA-256 pass reads every file and can take time for large inputs. Paths in the
manifest are relative to the data root, so no machine-specific path is recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from {{module_name}}.config import PROJ_ROOT, RAW_DATA_DIR

IGNORED_NAMES = {".gitkeep", ".DS_Store", "Thumbs.db"}


def sha256(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parquet_details(path: Path) -> dict[str, Any]:
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return {}
    parquet = pq.ParquetFile(path)
    return {
        "rows": parquet.metadata.num_rows,
        "schema_sha256": hashlib.sha256(str(parquet.schema_arrow).encode("utf-8")).hexdigest(),
    }


def build_input_manifest(
    data_root: Path, pattern: str = "**/*", hash_files: bool = False
) -> dict[str, Any]:
    """Return an inventory of the files under data_root that match pattern."""
    data_root = data_root.resolve()
    if not data_root.is_dir():
        raise FileNotFoundError(f"Data root does not exist: {data_root.name}")
    files = []
    for path in sorted(data_root.glob(pattern)):
        if not path.is_file() or path.name in IGNORED_NAMES:
            continue
        record: dict[str, Any] = {
            "path": path.relative_to(data_root).as_posix(),
            "size_bytes": path.stat().st_size,
        }
        if path.suffix == ".parquet":
            record.update(_parquet_details(path))
        if hash_files:
            record["sha256"] = sha256(path)
        files.append(record)
    return {
        "manifest_version": 1,
        "input_root_label": data_root.name,
        "pattern": pattern,
        "file_count": len(files),
        "total_bytes": sum(record["size_bytes"] for record in files),
        "hashes_included": hash_files,
        "files": files,
    }


def compare_manifests(old: dict[str, Any], new: dict[str, Any]) -> dict[str, list[str]]:
    """Return paths added, removed, and changed (size, schema, or hash) between manifests."""
    before = {record["path"]: record for record in old["files"]}
    after = {record["path"]: record for record in new["files"]}
    fields = ("size_bytes", "schema_sha256", "sha256")
    changed = sorted(
        path for path in before.keys() & after.keys()
        if any(before[path].get(field) != after[path].get(field) for field in fields)
    )
    return {
        "added": sorted(after.keys() - before.keys()),
        "removed": sorted(before.keys() - after.keys()),
        "changed": changed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--pattern", default="**/*", help="Glob pattern under the data root.")
    parser.add_argument("--sha256", action="store_true", help="Hash every file.")
    parser.add_argument("--write-manifest", type=Path, help="JSON output path.")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("OLD", "NEW"))
    args = parser.parse_args(argv)

    if args.compare:
        old, new = (json.loads(path.read_text(encoding="utf-8")) for path in args.compare)
        print(json.dumps(compare_manifests(old, new), indent=2))
        return 0

    try:
        manifest = build_input_manifest(args.data_root, args.pattern, args.sha256)
    except OSError as error:
        print(json.dumps({"status": "failed", "error": str(error)}, indent=2))
        return 1
    print(json.dumps({"status": "passed", "files": manifest["file_count"],
                      "total_bytes": manifest["total_bytes"],
                      "hashes_included": manifest["hashes_included"]}, indent=2))
    if args.write_manifest:
        output = args.write_manifest
        if not output.is_absolute():
            output = PROJ_ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Manifest written: {output.relative_to(PROJ_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
