# Specialized agent kit

A versioned kit for creating, evolving, and auditing a private team of VS Code agents in data-science repositories. It was generalised from a working repository in which the roles, handoff files, gates, and writing standards were refined over several runs.

Scope: data science, machine learning, deep learning, data engineering, data architecture, Python and SQL, and visualisation.

## Contents

| Path | Purpose |
| --- | --- |
| `kit.json` | Kit version, CCDS release followed, default environment |
| `ROLE_CATALOG.md` | The nine roles, fixed models, ownership, and when to include each |
| `CHANGELOG.md` | Kit versions and the lessons each one adopted |
| `prompts/` | Full procedures: `bootstrap-agents.md`, `evolve-agents.md`, `audit-agents.md` |
| `user-prompts/` | Thin VS Code slash commands that point to `prompts/` |
| `templates/roles.json` | Machine-readable role definitions |
| `templates/private/` | Everything rendered into a repository's `.github/` |
| `templates/hooks/pre-commit` | Outer-repository hook that rejects staged `.github` paths |
| `skeleton/ccds_v2_minimal/` | Minimal Cookiecutter Data Science v2 structure for empty repositories |
| `skeleton/CCDS_SOURCE.md` | CCDS release followed and the documented deviations |
| `tools/kit_render.py` | Create-only bootstrap plus preview-first versioned component adoption |
| `components/portable_docs/` | Canonical generic offline exporter, standalone CLI and public guide |
| `tests/test_kit.py` | Kit tests |

## Installation

The slash commands are VS Code user prompt files. Copy them once to the user prompts folder:

```powershell
Copy-Item C:/Users/10550/REDLEN_DS/MY_SPECIALIZED_AGENTS_/user-prompts/*.prompt.md "$env:APPDATA/Code/User/prompts/"
```

They then appear in Chat in every workspace as `/bootstrap-agents`, `/evolve-agents`, and `/audit-agents`. A prompt file runs only when typed; it never runs automatically. Each one contains a single instruction to read and follow the matching procedure in `prompts/`, so the procedures stay in one versioned place.

Requirements: Git on `PATH`, conda, and an environment with Python 3.10 or later. The private documentation builder also needs `markdown` (and `pymdown-extensions` for equations); the kit never installs them.

## Lifecycle

```mermaid
flowchart LR
  B["/bootstrap-agents<br/>once"] --> W[Runs with the Coordinator]
  W --> A["/audit-agents<br/>read-only"]
  A --> E["/evolve-agents<br/>approved changes"]
  E --> W
  E -. generic lessons .-> K[Kit update<br/>new version]
  K -. adopted through .-> E
```

1. **Bootstrap** (once per repository). Pre-flight checks, discovery or interview, proposed roster and settings, your approval, deterministic render, repository-specific filling, audit, commit to the private history.
2. **Work.** Multi-stage runs through the Coordinator, with handoff files and the ledger as the record.
3. **Audit.** Read-only checks at any time.
4. **Evolve.** Evidence from the ledger, `lessons`, and repository changes becomes proposed edits; nothing is applied without approval; every change is logged and committed.
5. **Kit update.** Lessons that apply to every repository are added to the kit as a new version.

## Empty and existing repositories

| | Greenfield (empty folder) | Existing repository |
| --- | --- | --- |
| Discovery | Interview: goal, data, confidentiality, deliverables, modeling, names, environment | Inventory of layout, data, tests, docs, conventions |
| Skeleton | CCDS v2 minimal structure rendered | Not rendered; existing layout kept |
| Roster | Small: Coordinator, Researcher, Data Engineer, Statistical Reviewer | Chosen from evidence |
| Paths in agent files | Kit defaults; missing paths marked "(planned)" | Mapped to the repository's real paths |
| Conflicts | None expected | Written to `.github/agents/_proposals/` for review |

## Safety layers

| Layer | Protects against |
| --- | --- |
| Marker `.github/agents/.kit.json` | A second bootstrap: the procedure and the renderer both refuse |
| Create-only renderer | Overwriting files: conflicts become proposals |
| Dry run before render | Unexpected file lists |
| Pre-flight: clean outer tree, no tracked `.github` | Mixing kit files with uncommitted work; repositories that publish `.github/` |
| `.git/info/exclude` and the pre-commit hook | Private files entering the outer repository |
| Private repository in `.github/` | Losing or being unable to undo agent changes; `git clean -fdx` in the outer repository |
| Separate commands | Accidental changes: only `/evolve-agents` edits an existing workspace, and only after approval |

## Undo

```powershell
git -C .github log --oneline           # private history
git -C .github revert <commit>         # undo one change
```

The private history covers `.github/` only. Code is restored through the outer repository; generated outputs are regenerated from their run record.

## Deliberate re-bootstrap

Re-bootstrapping is rarely needed; prefer `/evolve-agents`. If it is needed:

1. Commit the private history and copy `.github/` to a backup folder outside the repository.
2. Delete `.github/agents/.kit.json` by hand.
3. Run `/bootstrap-agents`. Existing files become proposals; nothing is overwritten.

## The shared environment

`DS_002` is the default environment for repositories without their own. Because it is shared, every handoff records a package-list hash (`ledger.py env-hash`), and installs require approval. A repository with a dedicated environment sets it once at bootstrap (`--conda-env`); the agent files never name an environment directly. `/evolve-agents` can move a repository from `DS_002` to a dedicated environment.

## Portable reports and shared chat equations (1.1.0)

This is engineering maintenance, not a scientific release. The canonical exporter is
`components/portable_docs/portable_docs.py`. Deployment copies its bytes unchanged to
`scripts/portable_docs.py`; there are no separate scientific/project-specific forks.
Public runtime code imports no private `.github` modules. The existing private
`scripts/docs_site.py` renderer and `build_site` callers remain unchanged.
The exporter runtime requires Python 3.11 or later; the bootstrap tool itself remains
standard-library-only and Python 3.10 compatible.

After bootstrap in **either greenfield or existing mode**, deliberately install the
optional component using the same update command. Bootstrap alone does not install
public exporter files. From this kit root, use the repository's approved environment:

```powershell
conda run -n lhl_discovery python tools/kit_render.py update-components --target C:/work/study
conda run -n lhl_discovery python tools/kit_render.py update-components --target C:/work/study --stage
# Review the plan/proposals; run the next command only after explicit approval.
conda run -n lhl_discovery python tools/kit_render.py update-components --target C:/work/study --apply
```

These maintenance examples use `lhl_discovery`, not the kit's default `DS_002`.
If conda is not on PATH, prefix the arguments with
`& C:/Users/10550/AppData/Local/anaconda3/Scripts/conda.exe run -n lhl_discovery python`.
For a different project, select its approved environment explicitly; do not install
or upgrade packages automatically.

The default command is read-only. `--stage` creates only review proposals under
`.github/agents/_proposals/portable-docs-1.1.0/`, including `plan.json` with
base/local/new SHA-256. It refuses to overwrite differing prior proposals.
`--apply` creates missing files and updates only unchanged managed files.
Unknown/customized conflicts block the entire apply before target writes.
For a conflict, manually merge the proposal while preserving local content, then
explicitly acknowledge each reviewed result:

```powershell
conda run -n lhl_discovery python tools/kit_render.py update-components --target C:/work/study --apply --accept-local docs/PORTABLE_DOCS.md
```

`--accept-local` is an approval, not an automatic merge or content validation; inspect
the resulting file before using it. Custom files remain custom on subsequent upgrades.
Reapplying an unchanged component is a no-op. The four managed paths are:

- `scripts/portable_docs.py` and `scripts/build_portable_docs.py`;
- `docs/PORTABLE_DOCS.md`;
- `.github/instructions/chat-equations.instructions.md`.

The chat rule applies to every role: use readable plain ASCII formulas and define
terms; no raw LaTeX delimiters/commands in chat unless requested. Preserve LaTeX in
source reports. Newly bootstrapped central instructions reference that shared rule.
Existing custom `copilot-instructions.md` and role files are never replaced.

Only `components.portable_docs.version` and its managed hashes in the target marker
advance after every component file succeeds or is explicitly acknowledged. The
top-level `kit_version` remains the workspace's bootstrap version: this command does
not pretend to migrate all private roles/templates. Interrupted writes do not advance
the marker; preview and reapply safely. No commits, tags or external-repository changes
are performed by these component commands.

### Build and share after deployment

From the **target repository root**, create `reports/presentation.md` and its approved
figures, then run:

```powershell
conda run -n lhl_discovery python scripts/build_portable_docs.py --include reports/presentation.md --name study-summary --version 1 --date 2026-11-05 --fetch-assets
```

Omit `--fetch-assets` on subsequent builds. Repeat `--include` for each additional
document. No flag means all public docs for compatibility, not implicit link traversal.
Greenfield `scripts/build_docs.py --portable` delegates to the same installed CLI;
existing builders need not be overwritten and can use `build_portable_docs.py` directly.
Use `--cache` to reuse a verified public MathJax cache. The public guide documents
eligible paths, failures, metadata and the optional reproducible `SOURCE_DATE_EPOCH`.
Only existing selected Markdown/figures are consumed; no data analysis runs.

Output: `build/study-summary_v1_2026-11-05.zip`, containing the identically named root
folder. Peers extract it and open that folder's `index.html` in a JavaScript-enabled
browser, with no server, Python or network. Unselected links are visibly scoped out,
not added to navigation. Source updates require rebuilding; never patch generated HTML.
The manifest records exporter/core hashes, versions, selection, UTC build time and
separate date label, input/output hashes and text-line counts.

### Legacy projects without a kit marker

`update-components` explicitly refuses pre-kit workspaces. Do not bootstrap over a
custom private team merely to obtain the exporter. A reviewed public adapter can
instead vendor just the canonical core, with no marker/private-file mutation:

```powershell
conda run -n lhl_discovery python tools/kit_render.py vendor-core --target C:/work/legacy --path src/example/portable_docs.py
# After review, supply the current file hash printed by preview:
conda run -n lhl_discovery python tools/kit_render.py vendor-core --target C:/work/legacy --path src/example/portable_docs.py --expected-sha256 <local-sha256> --apply
```

Missing destinations are create-only; existing differing files require their exact
reviewed SHA-256. Preserve the project's adapter, eligible figure roots and CLI tests;
verify the vendored bytes against the canonical core and rebuild. For an entirely
new public entry point, review the standalone CLI and guide as create-only additions.
Legacy chat instructions require a manual approved merge of the shared rule; no tool
claims to migrate arbitrary custom instructions safely.

## Maintaining the kit

The kit is a local Git repository, tagged by version.

1. Change templates, prompts, or the skeleton.
2. Run the tests: `conda run -n <env> python -m pytest -q -p no:cacheprovider tests` from the kit root.
3. Update `kit.json` (`kit_version`) and `CHANGELOG.md`.
4. Obtain explicit approval before committing or tagging (`git tag v<version>`).
   Updating version metadata/changelog alone does not authorize a Git release.

Before adding a lesson from a repository, remove project names, paths, data descriptions, and anything confidential.

## Known limitations

- The kit assumes a repository publishes nothing under `.github/`. A repository that needs public `.github/` content (for example CI workflows) is refused at pre-flight and needs a separate decision.
- Model labels request a model; they do not guarantee a model snapshot. Record the actual model when the client reports it.
- Agents cannot run notebook cells with the default tools; long notebooks are run by the user.
- The skeleton follows CCDS `v2.3.0` by hand; later CCDS releases are not adopted automatically (see `skeleton/CCDS_SOURCE.md`).
