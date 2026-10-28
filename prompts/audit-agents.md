# Audit procedure

You are checking the health of the private agent workspace. This procedure is read-only: do not edit, create, or delete any file, and do not commit.

## Step 1: Automated checks

Read the conda environment from `.github/agents/.kit.json` (`values.conda_env`) and run:

```powershell
conda run -n <env> python .github/scripts/audit.py
conda run -n <env> python .github/scripts/ledger.py check
conda run -n <env> python .github/scripts/ledger.py env-hash
```

If the marker is missing, report that the repository has not been bootstrapped and stop.

## Step 2: Manual checks

1. **Environment drift.** Compare the `env-hash` result with `environment.package_list_sha256` in the most recent handoff. Report a difference as a finding.
2. **Models.** List the model label in each agent file and compare it with `<kit_root>/templates/roles.json`. Report differences; they may be deliberate evolutions recorded in `CHANGELOG.md`.
3. **Kit version.** Compare `kit_version` in the marker with `<kit_root>/kit.json`. If the kit is newer, list the kit `CHANGELOG.md` entries since the marker's version.
4. **Ownership.** Confirm that every output path in the agent files has exactly one owner and that no role writes outside its Outputs table, based on `files_changed` in recent handoffs.
5. **Stale items.** Unresolved blocking items older than the latest release; roles never used in any handoff.
6. **Private history.** `git -C .github log --oneline -10`; uncommitted changes.

## Step 3: Report

Reply with a table of checks (pass, warn, fail) with one line of detail each, followed by recommended actions. Point to `/evolve-agents` for any change.
