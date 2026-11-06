# Portable exporter source

Canonical core: `portable_docs.py`, component **1.1.0**, Python 3.11 or later.
`build_portable_docs.py` is a thin public CLI, and `PORTABLE_DOCS.md` is the deployed
public guide. No project data, project paths or private runtime imports belong here.

The kit's `update-components` command vendors the core byte-for-byte into public
`scripts/portable_docs.py` and records both upstream and installed SHA-256.
The `vendor-core` command provides a guarded path for reviewed legacy adapters.
Make core fixes here first, then preview/adopt them in approved targets; do not
maintain a second divergent exporter implementation. Adapter-specific eligible
figure roots remain in the target's public entry point, not in this core.

Changes to this component must update its version, the kit's component version,
changelog, and focused tests as appropriate. No automated update scans or writes
other repositories. Rebuilding documents is separate from updating source.
