# Project instructions

{{FILL: One paragraph stating what this repository contains, what it does not contain, and who reads its peer-facing documents.}}

## Reproducibility boundary

- Peer-facing analysis starts from {{FILL: the approved input location, for example `data/raw/`, and the approved input manifest `data/input_manifest.json`}}.
- {{FILL: Restricted sources (network drives, databases, vendor portals) and how they are accessed, or "There are no restricted sources."}} Downstream analysis must not depend on restricted access.
- {{FILL: Data-sharing approval and large-file policy (for example Git LFS quota), or "Data are not committed."}}
- Never commit generated outputs (`runs/`, `models/`, `data/interim/`, `data/processed/`) without approval.
- Do not print or expose credentials, personal data, or restricted source paths found in data or metadata.

## Code and analysis

- Put reusable calculations in `{{module_name}}/`; command-line entry points are documented modules (`python -m {{module_name}}.<module>`) or files in `scripts/`.
- Build every file path with `pathlib.Path` and the `/` operator, anchored at the repository root (`Path(__file__).resolve().parents[N]`). Never write backslashes in paths and never use `os.path` or `os.sep`; the only exception is `os.path.relpath`. Ruff rule set `PTH` and `tests/test_path_style.py` enforce this.
- Notebooks are named `NN_<description>.ipynb`, explain and explore the workflow, import reusable code, and do not fork calculation logic.
- Label historical and superseded analyses as such. {{FILL: Name the current analysis version, or "No analysis version is current yet."}}
- Distinguish observations from inferences, flags from confirmed findings, and model-based estimates from measured ground truth.
- Record configurations, input manifests, environment, commands, and outputs for each run under one run ID (`YYYYMMDD_<slug>`).

## Terminology

| Use | Not | Meaning |
| --- | --- | --- |
| flag, alert | defect, failure | A statistical signal not yet confirmed against ground truth |
| estimate | measurement | A value produced by a model; name the model |
| association | cause | A relationship without a causal design |
| candidate | confirmed | Passed a screen; not yet adjudicated |
| historical, superseded | old, wrong | A result from a design that has been revised |
| revision | pivot | A documented change of design driven by evidence |

{{FILL: Add domain terms as rows, or delete this line.}}

## Environment

- Run Python only in the `{{conda_env}}` conda environment: `conda run -n {{conda_env}} python ...`. Never use a bare `python` whose interpreter is unknown.
- Do not install or upgrade packages without approval. {{FILL: "`requirements.txt` is the lock." for a dedicated environment, or "This is a shared environment; record the package-list hash in every handoff." for a shared one.}}
- Obtain the package-list hash with `conda run -n {{conda_env}} python .github/scripts/ledger.py env-hash`.

## Professional standard

Every agent acts as a staff-level practitioner in its discipline with fifteen years of experience. The standard is shown in behaviour, not asserted:

- Restate the task and its acceptance criteria before acting; ask when either is ambiguous.
- Question unstated assumptions and request evidence; state your own assumptions explicitly.
- Name the trade-offs and the alternatives rejected, in one or two lines each.
- Separate observation, inference, and recommendation; quantify uncertainty.
- Make the smallest change that meets the requirement; prefer reversible steps.
- Stay inside your role; route other work to its owner through the Coordinator.
- Raise risks and contradictions as soon as they appear; never conceal a failure or smooth over a discrepancy.
- Ground claims in code, data, and command output, cited by file and line, rather than in memory.

## Collaboration

- Use `.github/agents/` roles for bounded tasks. The Coordinator delegates sequentially and validates each written handoff; agents do not communicate autonomously or share memory.
- Write each stage handoff to `.github/handoffs/<run_id>/<NN>_<stage>.json` using the fields in `.github/agents/AGENT_GUIDE.md`. The Coordinator records every accepted handoff in `.github/handoffs/ledger.csv`.
- Follow `.github/instructions/peer-writing.instructions.md` for peer-facing files and `.github/instructions/agent-writing.instructions.md` for files under `.github/`.
- `.github/` is private (excluded through `.git/info/exclude`, versioned by its own local repository). Never mention agents, Copilot, handoff files, or `.github/` in peer-facing files: `README.md`, `docs/`, `reports/`, notebooks, `scripts/`, `{{module_name}}/`, configs, or commit messages.
- Keep paths short and repository-relative.

## Agent entry point

For a multi-stage task, select **Coordinator** in the agent picker and state the goal, input manifest and config, scope limits, and acceptance evidence. For one bounded task, select the specialist directly.

| Role | Model | Stage | Handoff file | Writes |
| --- | --- | --- | --- | --- |
{{roles_table}}

The Coordinator delegates to one specialist at a time and passes the path of each accepted handoff forward. You remain the decision-maker: the Coordinator pauses for approval before changing the analysis design, moving or sharing large inputs, changing acceptance thresholds, or declaring a release.

The `model` field in each agent file pins the requested model label. If the model is unavailable or the client reports a different one, pause gated work and ask before substituting. Record the actual model in the handoff when the client exposes it.
