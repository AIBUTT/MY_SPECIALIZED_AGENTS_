# CCDS source record

The skeleton in `ccds_v2_minimal/` is the kit's own copy of the minimal Cookiecutter Data Science structure. It is rendered without installing `cookiecutter-data-science`.

| Field | Value |
| --- | --- |
| Upstream | https://github.com/drivendataorg/cookiecutter-data-science |
| Release followed | `v2.3.0` (published 2025-07-24) |
| Verified | 2026-10-28, through the GitHub releases API |

## Kept from CCDS

- Top-level package `<module_name>/` with `config.py`, `dataset.py`, `features.py`, `plots.py`, and `modeling/{train,predict}.py`.
- `data/{raw,interim,processed,external}`, `docs/`, `models/`, `notebooks/`, `references/`, `reports/figures/`.
- `Makefile`, `pyproject.toml`, `requirements.txt`, `README.md`.
- `config.py` path names (`PROJ_ROOT`, `DATA_DIR`, `RAW_DATA_DIR`, and so on).
- `data/` excluded from Git by default.

## Deviations

| CCDS | Kit | Reason |
| --- | --- | --- |
| Notebook names `1.0-<initials>-<description>` | `NN_<description>.ipynb` | User decision |
| `typer` and `loguru` in module stubs | `argparse` and standard output | No dependencies in the skeleton |
| `mkdocs` documentation | `scripts/build_docs.py` (Markdown to HTML) | Same builder as the private docs |
| `flake8`/`black` options | Ruff with `I` and `PTH` rules, plus `tests/test_path_style.py` | Path convention enforced |
| No `tests/`, `configs/`, `runs/` by default | Added | Stage-gated runs need frozen configs, run folders, and tests |
| No input manifest | `<module_name>/input_manifest.py` | Intake stage |
| `models/` committed | `models/` and `runs/` ignored | Generated outputs are not committed by default |
| `LICENSE` | Omitted | Add when a licence is chosen |

## Updating to a newer CCDS release

1. Read the upstream release notes and the template tree for the new tag.
2. Apply structural changes to `ccds_v2_minimal/` by hand, keeping the deviations above unless they are revisited.
3. Update this record and `kit.json`, add an entry to the kit `CHANGELOG.md`, run the kit tests, and tag a new kit version.
