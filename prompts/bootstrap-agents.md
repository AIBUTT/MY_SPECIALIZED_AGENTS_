# Bootstrap procedure

You are creating the private agent workspace in the current repository from the agent kit. Act as a staff-level technical lead: careful, explicit, and reversible. This procedure runs once per repository.

The kit root is the folder that contains this file's parent `prompts/` folder. Below it is called `<kit>`. Read `<kit>/README.md` and `<kit>/ROLE_CATALOG.md` before starting.

## Rules

- Create files only. Never overwrite, move, or delete an existing file. The render tool writes conflicting files to `.github/agents/_proposals/` instead.
- Stop at every step marked **Stop** and wait for the user.
- Run Python only through `conda run -n <env> python ...`. Do not install or upgrade packages.
- Never mention agents, Copilot, the kit, or `.github/` in peer-facing files.
- If any pre-flight check fails, report it and stop. Do not work around it.

## Step 1: Pre-flight (read-only)

Run these checks from the repository root and report each result in one line.

1. **Marker.** If `.github/agents/.kit.json` exists, stop immediately and reply: "This repository was bootstrapped on <date> with kit v<version>. Use `/evolve-agents` to change the workspace or `/audit-agents` to check it." Do not continue, even if the user asks in the same message. Re-bootstrapping requires the user to remove the marker by hand, as described in `<kit>/README.md`.
2. **Git.** `git --version` succeeds.
3. **Outer repository.** If `.git/` exists: `git status --porcelain` is empty (otherwise ask the user to commit or stash first), and `git ls-files -- .github` is empty (otherwise stop: the repository publishes `.github/` content, and private-by-default cannot be applied without a user decision). If `.git/` does not exist, ask whether to run `git init -b main`.
4. **Environments.** `conda env list`. Note any `environment.yml`, `requirements.txt`, or `pyproject.toml`.

## Step 2: Discover

Decide the mode:

- **greenfield** when the folder contains nothing beyond `.git`, `.gitignore`, `.gitattributes`, `.vscode`, `README.md`, and `LICENSE`;
- **existing** otherwise.

For an **existing** repository, inventory without editing:

- package layout (`src/<pkg>/`, top-level package, scripts), languages, notebooks and their naming;
- data folders, formats, sizes, large-file tracking (Git LFS), and any restricted sources;
- tests, linters, documentation builders, configs, run-output folders;
- existing conventions worth keeping (path rules, terminology, run IDs, manifests);
- confidentiality signals (personal data, credentials, network paths in metadata).

For a **greenfield** repository, interview the user, one short group of questions at a time:

1. Goal: what decision or product does this work support?
2. Data: sources, formats, approximate size, access restrictions.
3. Confidentiality: who may see data, outputs, and code?
4. Deliverables and audience.
5. Modeling: will models be trained (classical ML, deep learning) or is the work analytical?
6. Names: project name, Python module name (lowercase, underscores).
7. Environment: dedicated conda environment, or the shared `DS_002`?

Write a discovery summary in chat: mode, evidence, conventions to keep, risks. **Stop** for confirmation.

## Step 3: Propose

Propose, in chat:

1. **Roster.** For each role in `<kit>/ROLE_CATALOG.md`, include or exclude it with one line of evidence. The Coordinator is required. For greenfield, start small: Coordinator, Researcher, Data Engineer, Statistical Reviewer, plus a role only when the interview gives evidence for it. Models are fixed by the catalog.
2. **Settings.** Project name, module name, description (one sentence, no quotes or braces), conda environment, Python version.
3. **Environment decision.** A dedicated environment keeps its own lock file. `DS_002` is shared: every handoff records the package-list hash, and installs require approval because they affect other projects.
4. **Path mapping (existing only).** Where the repository's real locations differ from the kit defaults (`data/raw/`, `data/input_manifest.json`, `runs/<run_id>/`, `<module_name>/`, `reports/figures/`), list the mapping that will be applied in Step 5.
5. **Repository-specific rules** to carry into `copilot-instructions.md` (for example a data contract, a terminology list, a large-file policy).

**Stop** for approval. Apply every change the user requests before continuing.

## Step 4: Render

Dry run first and show the plan (counts of files to create and proposals):

```powershell
conda run -n <env> python <kit>/tools/kit_render.py bootstrap --target . --mode <mode> --project-name "<name>" --module-name <module> --description "<sentence>" --conda-env <env> --python-version <x.y> --roles "<Role 1>,<Role 2>,..." --dry-run
```

Then run the same command without `--dry-run`. The tool:

- renders the selected agent files, instructions, guide, runbook, charter, ledger, scripts, and (greenfield) the CCDS skeleton;
- writes conflicting files to `.github/agents/_proposals/`;
- adds `.github/` to `.git/info/exclude` and installs the outer pre-commit hook;
- writes the marker `.github/agents/.kit.json`;
- initialises the private repository in `.github/` and commits the raw render.

If the tool refuses (non-zero exit), report its reason and stop.

## Step 5: Fill

Replace every `{{FILL: ...}}` token in `.github/` with repository-specific content, using the discovery evidence and the approved proposal:

- `copilot-instructions.md`: scope paragraph, input location, restricted sources, sharing policy, current analysis version, domain terms, lock-file rule.
- `CHARTER.md`: from the interview (greenfield) or from the README and reports (existing). Mark paths that do not exist yet as "(planned)".
- Agent files: formats, contracts, and the analysis contract to preserve. For an existing repository, apply the path mapping from Step 3 to every Inputs and Outputs table.
- `RUNBOOK.md`: standing decisions and expected values, or "defined per run".

Follow `.github/instructions/agent-writing.instructions.md`. Remove a line rather than leave a vague placeholder. Do not change models, tools, stage numbers, or handoff fields.

For each file in `.github/agents/_proposals/`, show the user a short comparison with the existing file and ask whether to merge, keep the existing file, or discard the proposal. Never merge without approval.

## Step 6: Verify

1. `conda run -n <env> python .github/scripts/audit.py` reports no failures.
2. Greenfield: `conda run -n <env> python -m pytest` passes; run `python -m ruff check .` if Ruff is available, otherwise report that it is not.
3. `conda run -n <env> python .github/build_private_docs.py --no-open` builds, or report the missing package.
4. `git status --porcelain` in the outer repository lists no `.github` path.
5. Commit the private history: `git -C .github add -A` and `git -C .github commit -m "bootstrap: repository-specific content"`.

## Step 7: Report

Reply with:

- mode, roster with models, settings;
- files created, proposals and their resolution, refusals;
- audit, test, and docs results;
- next steps for the user: review and commit the skeleton in the outer repository (greenfield), open the private docs, and start the first run with the Coordinator.
