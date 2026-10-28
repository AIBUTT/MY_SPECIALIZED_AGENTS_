"""Render peer documentation plus private agent files to .github/_site/ (local only).

Usage (from any folder):
    python .github/build_private_docs.py            # build and open in the browser
    python .github/build_private_docs.py --no-open  # build only
"""

from __future__ import annotations

import argparse
import importlib.util
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / ".github" / "_site"
PRIVATE_PATTERNS = (
    ".github/copilot-instructions.md",
    ".github/CHARTER.md",
    ".github/instructions/*.md",
    ".github/agents/AGENT_GUIDE.md",
    ".github/agents/RUNBOOK.md",
    ".github/agents/CHANGELOG.md",
    ".github/agents/*.agent.md",
)
PEER_PATTERNS = ("README.md", "docs/*.md", "docs/*/*.md", "reports/*.md", "reports/*/*.md")
PRIVATE_LABELS = {
    ".github": "Private: workspace",
    ".github/instructions": "Private: writing standards",
    ".github/agents": "Private: agents",
}

spec = importlib.util.spec_from_file_location(
    "docs_site", ROOT / ".github" / "scripts" / "docs_site.py"
)
docs_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs_site)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-open", action="store_true", help="Build without opening a browser.")
    args = parser.parse_args()

    sources = docs_site.collect_sources(PRIVATE_PATTERNS + PEER_PATTERNS, ROOT)
    index = docs_site.build_site(
        sources, OUT_DIR, "{{project_name}}: private workspace docs", ROOT, PRIVATE_LABELS
    )
    print(f"Rendered {len(sources)} pages: {index}")
    if not args.no_open:
        webbrowser.open(index.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
