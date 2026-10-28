# Kit changelog

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
