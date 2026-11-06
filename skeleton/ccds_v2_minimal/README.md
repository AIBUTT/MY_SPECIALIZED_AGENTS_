# {{project_name}}

{{description}}

## Project organisation

The layout follows Cookiecutter Data Science v2, with `tests/`, `configs/`, and `runs/` added.

```
├── Makefile           Convenience commands (`make test`, `make lint`, `make docs`)
├── README.md          This file
├── configs/           Analysis settings; frozen and copied into each run folder
├── data
│   ├── external       Data from third-party sources
│   ├── interim        Intermediate data that has been transformed
│   ├── processed      Final, canonical datasets for analysis and modeling
│   └── raw            Original, immutable data
├── docs/              Methods, workflow, and reproduction guides
├── models/            Trained and serialised models, predictions, and summaries
├── notebooks/         Notebooks named NN_<description>.ipynb, for example 00_data_overview.ipynb
├── pyproject.toml     Package metadata and tool configuration (pytest, Ruff)
├── references/        Data dictionaries, manuals, and other explanatory material
├── reports            Generated analyses and figures
│   └── figures
├── requirements.txt   Tested package versions
├── runs/              One folder per run ID (YYYYMMDD_<slug>) with config, manifests, and outputs
├── scripts/           Command-line utilities (documentation build)
├── tests/             Unit and style tests
└── {{module_name}}/   Source code
    ├── config.py          Project paths and shared settings
    ├── dataset.py         Build datasets from raw inputs
    ├── features.py        Compute features
    ├── input_manifest.py  Inventory and validate inputs
    ├── modeling
    │   ├── predict.py     Run inference with trained models
    │   └── train.py       Train models
    └── plots.py           Produce figures
```

## Environment

The analysis runs in the `{{conda_env}}` conda environment with Python {{python_version}}.

```powershell
conda run -n {{conda_env}} python -m pytest
```

Run module entry points from the repository root, for example `conda run -n {{conda_env}} python -m {{module_name}}.input_manifest --help`.

## Data

Raw inputs are placed in `data/raw/` and are never modified. Data and generated outputs (`data/`, `models/`, `runs/`) are not committed by default. Every run records an input manifest with file sizes and SHA-256 hashes; see [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Documentation

```powershell
conda run -n {{conda_env}} python scripts/build_docs.py --open
```

The command above produces a local browsing site, not a portable delivery.
After deliberate installation of the optional public exporter component
(`scripts/build_portable_docs.py`, `scripts/portable_docs.py` and
`docs/PORTABLE_DOCS.md`), build a selected offline package:

```powershell
conda run -n {{conda_env}} python scripts/build_docs.py --portable --include reports/presentation.md --name study-summary --version 1 --date 2026-11-05 --fetch-assets
```

Create the selected report and approved figures first. The standalone equivalent is
`conda run -n {{conda_env}} python scripts/build_portable_docs.py` with the same
selection/label flags. Omit `--fetch-assets` after the public renderer is cached.
The exporter requires Markdown and pymdown-extensions; obtain approval before
installing anything. Repeat `--include` for more documents; omission selects all
public Markdown. Existing unselected page links are annotated, not recursively added.

Share `build/study-summary_v1_2026-11-05.zip`. Peers extract it and open
`study-summary_v1_2026-11-05/index.html` with JavaScript enabled; rendering needs no
server, Python or network. Update reviewed source files, then regenerate packages;
never edit generated HTML. Component version 1.1.0 records selection, source/output
hashes, renderer versions and separate package-date/UTC-generation metadata.
