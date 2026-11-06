# Evolve procedure

You are changing an existing private agent workspace so that it fits the repository's current needs. Act as a staff-level technical lead: every change has evidence, a reason, and the user's approval. Nothing is applied before approval.

The kit root (`<kit>`) is recorded as `kit_root` in `.github/agents/.kit.json`.

## Rules

- Propose first, apply second. Show each change as a unified diff or a precise description of the new text.
- Never change a model label, the handoff common fields, or the private-by-default rule without explicit approval of that specific item.
- Never edit peer-facing files except the explicitly approved portable component
  adoption below; do not change report content or scientific code.
- Run Python only through `conda run -n <env> python ...`.

## Step 1: Pre-flight

For a focused exporter/chat update, use the component route below instead of the
general workspace steps. It does not require replacing or committing private roles.

1. `.github/agents/.kit.json` exists. If not, stop and suggest `/bootstrap-agents`.
2. `git -C .github status --porcelain` is empty. If not, show the changes and ask the user to commit them (`git -C .github commit -am "manual edits"`) or discard them. Do not continue with uncommitted changes.
3. Note the latest private commit: `git -C .github log -1 --oneline`.

## Step 2: Gather evidence

Read, without editing:

- the user's stated reason for the change;
- `.github/handoffs/ledger.csv`: rejected or blocked stages, failed checks, repeated blocking items, changed package-list hashes;
- `lessons` and `unresolved` in recent handoff files;
- `.github/agents/CHANGELOG.md` and `.github/CHARTER.md`;
- repository changes since the last evolution: `git log --since=<date> --stat` in the outer repository (new folders, data types, modeling code, report types);
- `conda run -n <env> python .github/scripts/audit.py`.

## Step 3: Propose

Group proposals by type. For each, state the evidence, the change, the files, and the risk.

| Type | Examples |
| --- | --- |
| Tighten a rule | A recurring lesson becomes a constraint or a checklist item |
| Fix ownership | Two roles write the same path; a path has no owner |
| Update paths | New data folder, renamed module, new output type |
| Add a role | Modeling code appeared: add the ML Engineer; figures are produced: add the Visualizer |
| Retire or merge a role | A role has not been used across several runs |
| Change the environment | Move from `DS_002` to a dedicated environment with a lock file |
| Update the charter | Goal, scope, or audience changed |

Separately, list **kit candidates**: lessons that would help every repository (not specific to this one), phrased without project names, paths, or confidential details.

**Stop** for approval of each item.

## Step 4: Apply

1. Checkpoint: `git -C .github commit --allow-empty -m "checkpoint before evolve"`.
2. Apply approved items only.
   - Add a role with `conda run -n <env> python <kit>/tools/kit_render.py add-role --target . --role "<Role>"`, then fill its `{{FILL: ...}}` tokens, add it to the Coordinator `agents` list and to the roles tables in `copilot-instructions.md` and `AGENT_GUIDE.md`.
   - Retire a role by deleting its agent file only after approval; keep its handoffs.
3. Add one row per change to `.github/agents/CHANGELOG.md` (date, change, files, evidence, "User").
4. Run `conda run -n <env> python .github/scripts/audit.py`; resolve every failure.
5. Commit: `git -C .github add -A` and `git -C .github commit -m "evolve: <summary>"`.

## Step 5: Report

Reply with the applied changes, the audit result, the commit hash, how to undo (`git -C .github revert <hash>`), and the kit candidates for the user to consider adding to the kit.

## Focused versioned component adoption

1. Run `conda run -n <env> python <kit>/tools/kit_render.py update-components --target <repo>`.
   Default is a read-only preview. Missing kit markers are an explicit legacy refusal,
   not permission to bootstrap over custom instructions.
2. If useful, add `--stage` to write create-only proposals and a base/local/new hash
   plan under `.github/agents/_proposals/portable-docs-1.1.0/`. Review the exact four
   destinations in the kit README, including the three public exporter/guide files.
3. Obtain user approval. Apply clean managed changes with `--apply`. Conflicts block
   apply; merge them manually without discarding local content, then acknowledge exact
   merged paths with repeatable `--accept-local <path> --apply`.
4. Test the deployed exporter on selected non-sensitive Markdown and cached public
   renderer assets. Review the shared chat rule. Do not replace central instructions
   or individual role files. Component state advances only on complete adoption;
   top-level workspace kit version is deliberately unchanged.
5. Report tests, component hashes/version and unresolved custom decisions. These
   commands do not commit or tag. Obtain separate explicit approval for Git actions.
   For legacy public adapters, use the reviewed `vendor-core` route in the kit README;
   legacy private instructions require a manual approved merge.
