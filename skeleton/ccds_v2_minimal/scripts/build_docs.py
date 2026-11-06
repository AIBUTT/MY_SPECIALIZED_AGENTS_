"""Render the project's Markdown documentation as a browsable HTML site.

Examples:
    python scripts/build_docs.py --open
    python scripts/build_docs.py --out build/docs

Pages are README.md, docs/, and reports/. Links between pages point to the generated HTML;
links to notebooks, code, and figures point to the repository files. Equations (MathJax)
and diagrams (Mermaid) are rendered when a network connection is available; offline, they
remain readable as source text.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote, unquote

import markdown

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT_ROOT / "build" / "docs"
PEER_PATTERNS = ("README.md", "docs/*.md", "docs/*/*.md", "reports/*.md", "reports/*/*.md")
GROUP_LABELS = {".": "Overview", "docs": "Guides", "reports": "Reports"}

EXTENSIONS = ["extra", "toc", "sane_lists"]
EXTENSION_CONFIGS: dict[str, dict] = {}
try:
    import pymdownx  # noqa: F401
except ImportError:
    print("Note: 'pymdown-extensions' is not installed; equations render as source text.")
else:
    EXTENSIONS.append("pymdownx.arithmatex")
    EXTENSION_CONFIGS["pymdownx.arithmatex"] = {"generic": True}

MATHJAX = '<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-chtml.js"></script>'
MERMAID = (
    '<script type="module">import mermaid from '
    '"https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";'
    "mermaid.initialize({startOnLoad:true});</script>"
)
MERMAID_BLOCK = re.compile(r'<pre><code class="language-mermaid">(.*?)</code></pre>', re.DOTALL)
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
URL_ATTR = re.compile(r'(\s(?:href|src)=")([^"]+)(")')
EXTERNAL = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|#|//)")

CSS = """
body{margin:0;display:flex;font:15px/1.6 system-ui,Segoe UI,Arial,sans-serif;color:#1f2328}
nav{width:17rem;flex:none;height:100vh;position:sticky;top:0;overflow:auto;
    background:#f6f8fa;border-right:1px solid #d0d7de;padding:1rem;box-sizing:border-box}
nav h2{font-size:.8rem;text-transform:uppercase;color:#59636e;margin:1.2rem 0 .3rem}
nav a{display:block;padding:.15rem .4rem;border-radius:4px;color:#1f2328;text-decoration:none}
nav a:hover{background:#eaeef2}nav a.current{background:#dbe9ff;font-weight:600}
main{flex:1;max-width:62rem;padding:1.5rem 2.5rem 4rem;min-width:0}
h1,h2,h3{line-height:1.25}h1{border-bottom:1px solid #d0d7de;padding-bottom:.3rem}
table{border-collapse:collapse;margin:1rem 0;display:block;overflow:auto}
th,td{border:1px solid #d0d7de;padding:.35rem .7rem;vertical-align:top}th{background:#f6f8fa}
code{background:#eff1f3;padding:.1rem .3rem;border-radius:4px;font-size:90%}
pre{background:#f6f8fa;padding:.8rem;overflow:auto;border-radius:6px}
pre code{background:none;padding:0}
blockquote{margin:1rem 0;padding:.2rem 1rem;border-left:4px solid #d0d7de;color:#3d444d}
img{max-width:100%}details.front-matter{margin-bottom:1rem}
"""


def collect_sources(patterns: tuple[str, ...], root: Path = PROJECT_ROOT) -> list[Path]:
    """Return existing Markdown files matching the patterns, in pattern order."""
    seen: dict[Path, None] = {}
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                seen.setdefault(path.resolve(), None)
    return list(seen)


def _title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _relative_url(target: Path, start_dir: Path) -> str:
    try:
        return quote(Path(os.path.relpath(target, start_dir)).as_posix())
    except ValueError:
        return target.as_uri()


def _rewrite_urls(body: str, source: Path, out_file: Path, page_for: dict[Path, Path]) -> str:
    def fix(match: re.Match[str]) -> str:
        url = html.unescape(match.group(2))
        if EXTERNAL.match(url):
            return match.group(0)
        path_part, sep, fragment = url.partition("#")
        target = (source.parent / unquote(path_part)).resolve()
        new_url = _relative_url(page_for.get(target, target), out_file.parent) + sep + fragment
        return f"{match.group(1)}{html.escape(new_url, quote=True)}{match.group(3)}"

    return URL_ATTR.sub(fix, body)


def _nav(pages: list[tuple[str, str, Path]], current: Path, out_dir: Path) -> str:
    index_href = _relative_url(out_dir / "index.html", current.parent)
    parts = [f'<a href="{index_href}"><strong>Contents</strong></a>']
    group = None
    for label, title, out_file in pages:
        if label != group:
            parts.append(f"<h2>{html.escape(label)}</h2>")
            group = label
        href = _relative_url(out_file, current.parent)
        css = ' class="current"' if out_file == current else ""
        parts.append(f'<a{css} href="{href}">{html.escape(title)}</a>')
    return "\n".join(parts)


def _page(title: str, nav: str, body: str) -> str:
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{CSS}</style>{MATHJAX}{MERMAID}</head>"
        f"<body><nav>{nav}</nav><main>{body}</main></body></html>\n"
    )


def build_site(sources: list[Path], out_dir: Path, site_title: str,
               root: Path = PROJECT_ROOT) -> Path:
    """Render sources to out_dir, mirroring their repository paths; return index.html."""
    out_dir = out_dir.resolve()
    page_for = {src: out_dir / src.relative_to(root).with_suffix(".html") for src in sources}

    texts = {src: src.read_text(encoding="utf-8") for src in sources}
    pages = []
    for src in sources:
        folder = src.parent.relative_to(root).as_posix()
        pages.append((GROUP_LABELS.get(folder, folder), _title(texts[src], src.stem),
                      page_for[src]))

    for src, (_, title, out_file) in zip(sources, pages):
        front_matter_match = FRONT_MATTER.match(texts[src])
        text = texts[src][front_matter_match.end():] if front_matter_match else texts[src]
        body = markdown.markdown(text, extensions=EXTENSIONS, extension_configs=EXTENSION_CONFIGS)
        body = MERMAID_BLOCK.sub(r'<pre class="mermaid">\1</pre>', body)
        source_note = f'<p><code>{html.escape(src.relative_to(root).as_posix())}</code></p>'
        body = source_note + _rewrite_urls(body, src, out_file, page_for)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(_page(title, _nav(pages, out_file, out_dir), body), encoding="utf-8")

    index = out_dir / "index.html"
    index_body = f"<h1>{html.escape(site_title)}</h1>\n" + _nav(pages, index, out_dir)
    index.write_text(_page(site_title, _nav(pages, index, out_dir), index_body), encoding="utf-8")
    return index


def main() -> int:
    if "--portable" in sys.argv[1:]:
        try:
            from build_portable_docs import main as portable_main
        except ImportError as error:
            raise SystemExit(
                "Portable component is not installed. Install the reviewed public exporter "
                "files first; see the source project's installation instructions."
            ) from error
        return portable_main([arg for arg in sys.argv[1:] if arg != "--portable"])
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory.")
    parser.add_argument("--open", action="store_true", help="Open the site in a web browser.")
    args = parser.parse_args()

    out_dir = args.out if args.out.is_absolute() else PROJECT_ROOT / args.out
    sources = collect_sources(PEER_PATTERNS)
    index = build_site(sources, out_dir, "{{project_name}}: documentation")
    print(f"Rendered {len(sources)} pages: {index}")
    if args.open:
        webbrowser.open(index.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
