# Kit changelog

## v1.1.0 (2026-11-05)

Engineering maintenance; no scientific defaults or role model labels changed.

- Generic offline Markdown component: one canonical vendored core, explicit repeatable
  source selection, descriptive name/version/date ZIP roots, pinned embedded MathJax,
  cited raster images, scoped excluded links, strict dependencies and rollback.
- Manifest provenance: selected input/output hashes and line counts, core/renderer
  versions, UTC build clock separate from the user date label; optional reproducible clock.
- Deliberate greenfield and existing-project installation with `update-components`:
  preview by default, create-only proposals, base/local/new hashes, managed safe
  updates, explicit custom merge acknowledgment and component-level completion marker.
- Guarded `vendor-core` for reviewed legacy adapters; no automatic private migration.
- Shared plain-ASCII chat equation rule for all roles; source LaTeX remains unchanged.
- Public CLI and guide do not depend on private runtime files. Skeleton builder delegates
  portable mode to the installed component. Full usage and upgrade instructions added.
- Commit/tag remain subject to separate explicit approval.

## v1.0.1 (2026-10-29)

Lessons from the first existing-repository run.

- Path-style test: the drive-letter pattern now requires a non-word character before the letter (`(?<!\w)[A-Za-z]:\\`), so strings such as `"failed:\n"` are no longer reported as Windows paths; new self-test.
- Visualizer: owns the plotting cells of every notebook, including figures that are displayed but not saved; ownership table updated.
- Handoffs: a stage that executes or edits notebooks records each notebook's SHA-256 in `outputs`; the Coordinator compares cell sources, outputs, and metadata when only a notebook hash differs.
- README: the kit test command targets `tests`; collecting from the kit root fails on the unrendered skeleton templates.

## v1.0.0 (2026-10-28)

First release, generalised from a working data-science repository.

- Nine roles with fixed models and fifteen-year staff-level professional standards: Coordinator, Data Steward, Researcher, Data Architect, Data Engineer, ML Engineer, Statistical Reviewer, Visualizer, Report Curator.
- Ten stages (`00_extraction` to `09_release`) with fixed JSON handoff files, a JSON schema, and a CSV ledger maintained by the Coordinator.
- Handoff common fields extended with `timestamp_utc`, `lessons`, and `environment.package_list_sha256`.
- Private-by-default workspace: `.git/info/exclude`, an outer pre-commit hook, and a local repository inside `.github/`.
- Create-only renderer with marker, dry run, proposals for conflicts, and an `add-role` command.
- Read-only audit script and ledger tools rendered into each repository.
- Minimal CCDS v2 skeleton (release `v2.3.0`) for empty repositories, with `NN_<description>.ipynb` notebook names, `tests/`, `configs/`, `runs/`, Ruff `PTH` rules, and a path-style test.
- Slash commands `/bootstrap-agents`, `/evolve-agents`, `/audit-agents`.
