# Agent guide (private)

This guide and everything under `.github/` are local-only: `.github/` is listed in `.git/info/exclude` and is versioned by its own local repository (`.github/.git`), which is never pushed. Peer-facing documentation is under `docs/` and must not mention agents.

The workspace was created from agent kit v{{kit_version}} on {{bootstrap_date}}; `.github/agents/.kit.json` records the kit version, settings, and the files created. Do not delete or edit the marker.

## Reading the documentation

Build and open one site containing the private files and the peer documentation:

```powershell
conda run -n {{conda_env}} python .github/build_private_docs.py
```

Add `--no-open` to build only. The site is written to `.github/_site/` (ignored by the private repository). It needs the `markdown` and `pymdown-extensions` packages; the script reports which one is missing.

## Environment

- Agents run Python only as `conda run -n {{conda_env}} python ...`.
- Do not install or upgrade packages without approval.
- Record the package-list hash (`conda run -n {{conda_env}} python .github/scripts/ledger.py env-hash`) in every handoff. A changed hash between two stages of one run is a finding.

## Writing standards

| Standard | Applies to |
| --- | --- |
| `.github/instructions/peer-writing.instructions.md` | `README.md`, `docs/`, `reports/`, notebooks |
| `.github/instructions/agent-writing.instructions.md` | All Markdown under `.github/`, including agent files |

VS Code attaches the matching standard automatically when any agent edits these files.

## Starting a task

- For a multi-stage task, choose **Coordinator** and state the goal, allowed scope, input manifest and config, and acceptance checks.
- For one bounded task, choose the specialist directly.
- Review the Coordinator's proposed stage plan. Approve changes to the analysis design, large-data movement or sharing, acceptance thresholds, and release decisions explicitly.

## Roles

| Role | Model | Stage | Handoff file | Writes |
| --- | --- | --- | --- | --- |
{{roles_table}}

Each agent file lists its exact inputs and outputs. Agents do not share a live conversation; the Coordinator passes accepted handoff files between them. Stages without a role in this table are skipped and recorded as skipped in the release record.

## Stages

| Stage | Owner | Purpose |
| --- | --- | --- |
| `00_extraction` | Data Steward | Optional: produce raw inputs from restricted sources |
| `01_intake` | Data Steward | Validate inputs; write the input manifest |
| `02_research` | Researcher | Hypotheses, discriminating tests, proposed decision |
| `03_design` | Data Architect | Schemas, data contracts, storage layout, design records |
| `04_pipeline` | Data Engineer | Deterministic transformations, features, run outputs |
| `05_modeling` | ML Engineer | Training, evaluation, model artifacts |
| `06_review` | Statistical Reviewer | Independent read-only review |
| `07_figures` | Visualizer | Publication figures from accepted outputs |
| `08_report` | Report Curator | Peer documents with number and link checks |
| `09_release` | Coordinator | Release record |

Peer-facing stage gates are in `docs/WORKFLOW.md`.

## Fixed handoff files

A chat reply is not evidence: it can be summarised, misremembered, or lost when the session ends. Each specialist writes its handoff as a file at a fixed location with fixed fields, and the Coordinator validates the file rather than the chat text.

**Location:** `.github/handoffs/<run_id>/<NN>_<stage>.json`, for example `.github/handoffs/20260101_baseline/04_pipeline.json`. Handoffs reference outputs by path and never copy data. A stage that executes or edits notebooks lists each notebook in `outputs` with its SHA-256, so later edits are detectable. The schema is `.github/handoffs/handoff.schema.json`.

**Common fields:**

```json
{
  "run_id": "20260101_baseline",
  "stage": "04_pipeline",
  "agent": "Data Engineer",
  "configured_model": "GPT-6 Astra",
  "actual_model": "unknown | reported value",
  "timestamp_utc": "2026-01-01T12:00:00Z",
  "status": "accepted | rejected | blocked",
  "environment": {"conda_env": "{{conda_env}}", "lock_file": "requirements.txt | none", "package_list_sha256": "...", "git_revision": "<hash or uncommitted>"},
  "inputs": [{"path": "data/input_manifest.json", "sha256": "..."}],
  "config": {"path": "configs/default.yaml", "sha256": "..."},
  "commands": ["conda run -n {{conda_env}} python -m {{module_name}}.dataset"],
  "outputs": [{"path": "runs/20260101_baseline/pipeline/table.parquet", "format": "parquet", "rows": 0, "sha256": "..."}],
  "files_changed": ["{{module_name}}/features.py"],
  "checks": [{"name": "pytest", "command": "conda run -n {{conda_env}} python -m pytest", "result": "12 passed", "passed": true}],
  "scientific_assumptions_changed": [],
  "unresolved": [{"item": "...", "blocking": false}],
  "lessons": ["A rule or ownership gap that slowed this stage, or an empty list"],
  "ready_for_next_stage": true
}
```

**How the Coordinator uses it:**

1. Before invoking a specialist, the Coordinator names the handoff file it must write. The Statistical Reviewer is read-only, so the Coordinator writes `06_review.json` from its chat findings.
2. After the specialist returns, the Coordinator opens the file, confirms that every `outputs[].path` exists, recomputes hashes, checks `inputs` against the expected manifest, and reruns any cheap check marked as passed. When only a notebook hash differs, it compares cell sources, outputs, and metadata before treating the change as substantive; editors can re-save line endings.
3. A stage does not advance if a check fails, `scientific_assumptions_changed` is non-empty, or `unresolved` contains a blocking item. Design changes go to the user.
4. The next specialist receives the path of the accepted handoff file, not a paraphrase.
5. The Coordinator appends each validated handoff to the ledger.

## Handoff ledger

`.github/handoffs/ledger.csv` holds one row per validated handoff file. The JSON files are the source of truth; the ledger is an index for review across runs.

```powershell
conda run -n {{conda_env}} python .github/scripts/ledger.py append .github/handoffs/<run_id>/<NN>_<stage>.json
conda run -n {{conda_env}} python .github/scripts/ledger.py check
```

- Only the Coordinator appends rows.
- A rewritten handoff appends a new row; the last row for a path is authoritative.
- `check` fails if a handoff has no row or if its current SHA-256 differs from the last recorded one (the file changed after acceptance).

## Private history and undo

`.github/` has its own local Git repository. The kit commits before and after each bootstrap or evolution; commit manual edits yourself.

```powershell
git -C .github log --oneline          # history of agents, rules, and handoffs
git -C .github diff HEAD~1            # what the last change did
git -C .github revert <commit>        # undo one change, keeping history
```

- The private history covers `.github/` only. Code changes are undone through the outer repository; generated outputs are regenerated from their run record.
- The outer repository's `git clean -fdx` does not remove `.github/` because Git skips nested repositories unless `-ff` is given.
- The outer pre-commit hook rejects any staged `.github` path.

## Maintaining the workspace

| Command | Use |
| --- | --- |
| `/evolve-agents` | Propose changes to roles and rules from ledger evidence, lessons, or a change of project direction. Nothing is applied without approval. |
| `/audit-agents` | Read-only check of the marker, exclusion, hook, private history, front matter, placeholders, peer-file leaks, output ownership, and ledger. |
| `/bootstrap-agents` | Not used again in this repository; it stops when the marker exists. |

The audit can also be run directly: `conda run -n {{conda_env}} python .github/scripts/audit.py`.

## Model pinning

Each agent file sets a `model` label so the requested model is visible and consistent by role. Check the model picker before a gated task; if a pinned model is unavailable, stop and ask rather than substitute. Record the actual model in the handoff when the client exposes it. A pinned label is not an immutable model snapshot.
