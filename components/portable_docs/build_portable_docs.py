"""Build a selected, self-contained public Markdown package. Exporter component 1.1.0.

Requires Markdown and pymdown-extensions in the approved environment. This command
does not install packages. Use --fetch-assets once for pinned public MathJax files.
No server, repository checkout or private workspace is needed by the delivered HTML.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from portable_docs import export_portable, package_stem, select_sources

ROOT = Path(__file__).resolve().parents[1]
CSS = """
body{margin:0;display:flex;font:16px/1.6 system-ui,sans-serif;color:#1f2328}
nav{width:17rem;flex:none;padding:1rem;background:#f6f8fa}
nav a{display:block;margin:.5rem 0}main{max-width:65rem;padding:2rem;min-width:0}
img{max-width:100%}pre{overflow:auto}table{border-collapse:collapse}
th,td{border:1px solid #d0d7de;padding:.4rem}
"""


def render_markdown(text: str) -> str:
    import markdown

    front = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if front:
        text = text[front.end():]
    body = markdown.markdown(
        text, extensions=["extra", "toc", "sane_lists", "pymdownx.arithmatex"],
        extension_configs={"pymdownx.arithmatex": {"generic": True}},
    )
    if front:
        body = ("<details><summary>Front matter</summary><pre>"
                + html.escape(front.group(1)) + "</pre></details>" + body)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include", action="append", help="Exact public Markdown path; repeatable.")
    parser.add_argument("--name")
    parser.add_argument("--version")
    parser.add_argument("--date", help="Package label YYYY-MM-DD, not the generation timestamp.")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--cache", type=Path, default=ROOT / "build" / "cache" / "portable_docs")
    parser.add_argument("--fetch-assets", action="store_true")
    args = parser.parse_args(argv)
    try:
        stem = package_stem(args.name, args.version, args.date)
        out = args.out or ROOT / "build" / (stem or "portable_docs")
        if not out.is_absolute():
            out = ROOT / out
        cache = args.cache if args.cache.is_absolute() else ROOT / args.cache
        index = export_portable(
            select_sources(ROOT, args.include), out, root=ROOT, cache_dir=cache,
            fetch_assets=args.fetch_assets, render_markdown=render_markdown, css=CSS,
            name=args.name, version=args.version, date=args.date,
        )
    except (OSError, ValueError, ImportError) as error:
        parser.exit(1, f"Portable export failed: {error}\n")
    print(f"Contents: {index}\nShare ZIP: {out.with_suffix('.zip')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
