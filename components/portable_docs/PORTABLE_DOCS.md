# Offline document packages

The exporter packages existing public Markdown and figures without recalculating results.
Use the project's approved Python environment; obtain approval before installing dependencies
(`Markdown` and `pymdown-extensions`; exporter runtime Python 3.11 or later).

From the repository root, replace `<env>` with that environment's name:

```powershell
conda run -n <env> python scripts/build_portable_docs.py --include reports/presentation.md --name study-summary --version 1 --date 2026-11-05 --fetch-assets
```

Repeat `--include` to select additional exact root-relative Markdown paths. Without
`--include`, all `README.md`, `docs/**/*.md` and `reports/**/*.md` are selected for
backward compatibility. Linked pages are never added implicitly: existing excluded
documents are marked `[not included]`. Missing requested pages, missing linked pages
and missing eligible figures are errors. Review source contents for sharing approval.

Eligible Markdown roots are `docs/`, `reports/`, and the root `README.md`. Eligible raster
images (PNG, JPEG, GIF, WebP) must be in `docs/`, `reports/`, or `figures/`. Only cited images
are embedded. Cited public TXT files in docs/reports and `requirements.txt` may accompany
the report. Private/hidden paths and paths escaping the repository are rejected.
Other code/data links are visibly annotated, not copied. Remote images, dynamic TeX,
Mermaid and unsupported HTML dependencies fail explicitly.

`--name`, `--version`, and `--date` must be supplied together. Names use ASCII letters,
digits and hyphens; versions also allow dots. Dates use valid `YYYY-MM-DD`. The example
produces `build/study-summary_v1_2026-11-05.zip` containing the root folder
`study-summary_v1_2026-11-05/`; its `index.html` lists only selected pages. `--out` may
change the parent directory, but a named package must retain this exact folder name.
Unlabelled builds retain `build/portable_docs.zip` and the historical flat ZIP layout.

The first build fetches only SHA-256-pinned public MathJax 3.2.2 assets. Subsequent builds
omit `--fetch-assets` and reuse `build/cache/portable_docs`; `--cache` can point to a
previously verified asset cache. The exporter installs no dependencies.

Peers extract the whole ZIP and open `<package>/index.html` in a JavaScript-enabled
browser. No server, Python, extension or network is needed. Images and the equation
renderer are embedded. External citations are marked `[online]`. The page's status
line reports successful image and equation rendering.

`portable-manifest.json` records selection, input/output hashes and text-line counts,
renderer/package versions, core source hash and image roots. The user date is a label,
not a generation timestamp. `generated_utc` records the UTC build clock. To reproduce
bytes, preserve source files, renderer versions and pinned assets, and set the same
`SOURCE_DATE_EPOCH` (integer Unix seconds) before each build; the manifest labels that
clock explicitly. Text rows mean lines; binary rows are null. The manifest and ZIP
cannot contain their own hashes; record those in a separate delivery record.

Update source code and this guide as a reviewed set, then rebuild packages. Never patch
generated HTML as an upgrade. Exporter component version: **1.1.0**. Existing project
files must be reviewed rather than overwritten by an installation.
