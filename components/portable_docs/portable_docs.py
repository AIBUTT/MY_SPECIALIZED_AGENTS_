"""Offline documentation packaging, version 1.1.0; no scientific transformations.

Only peer Markdown, cited peer .txt files, requirements.txt, and curated raster
figures are eligible. Other repository links are annotated, not copied or read.
All runtime assets are pinned and embedded. A strict HTML dependency check and CSP
prevent silently relying on a server, repository checkout, CDN, fonts, or plugins.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import shutil
import tempfile
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from datetime import date as calendar_date
from html.parser import HTMLParser
from importlib.metadata import version as package_version
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from urllib.request import urlopen

ASSETS = {
    "mathjax-3.2.2-tex-svg-full.js": (
        "https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg-full.js",
        "a4354ff94fd868aea0cc6eaaa79a57fda0588646fc46ee3700a349ee0a11cbe6",
    ),
    "mathjax-3.2.2-LICENSE": (
        "https://cdn.jsdelivr.net/npm/mathjax@3.2.2/LICENSE",
        "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
    ),
}
MANIFEST = "portable-manifest.json"
EXPORTER_VERSION = "1.1.0"
IMAGE_ROOTS = (Path("docs"), Path("reports"), Path("figures"))
MIMES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".gif": "image/gif", ".webp": "image/webp"}
TAGS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "code", "col", "colgroup",
    "dd", "del", "details", "div", "dl", "dt", "em", "figcaption", "figure",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "input", "kbd",
    "li", "main", "mark", "ol", "p", "pre", "s", "samp", "small", "span",
    "strong", "sub", "summary", "sup", "table", "tbody", "td", "th", "thead",
    "tfoot", "tr", "ul", "var",
}
CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "img-src data:; font-src 'none'; connect-src 'none'; base-uri 'none'; "
    "object-src 'none'; form-action 'none'"
)
RUNTIME = r"""
window.portableReport = {state: "pending"};
function portableFail(error) {
  window.portableReport.state = "error";
  document.documentElement.dataset.portableState = "error";
  const note = document.getElementById("portable-status");
  note.textContent = "Rendering failed: " + String(error);
  note.setAttribute("role", "alert");
}
window.addEventListener("error", event => portableFail(event.message));
window.MathJax = {
  loader: {load: [], require: name => Promise.reject(new Error("Offline dependency: " + name))},
  tex: {packages: {"[-]": ["autoload", "require", "noundefined"]}},
  svg: {fontCache: "local"},
  options: {ignoreHtmlClass: ".*|", processHtmlClass: "arithmatex"},
  startup: {
    pageReady: () => MathJax.startup.defaultPageReady().then(async () => {
      const images = Array.from(document.images);
      await Promise.all(images.map(image => new Promise((resolve, reject) => {
        const check = () => image.naturalWidth > 0 && image.naturalHeight > 0
          ? resolve() : reject(new Error("Figure failed to load: " + image.alt));
        if (image.complete) check();
        else {
          image.addEventListener("load", check, {once: true});
          image.addEventListener("error", () => reject(new Error("Figure failed to load")),
                                 {once: true});
        }
      })));
      const errors = document.querySelectorAll("mjx-merror, [data-mjx-error]");
      const math = document.querySelectorAll("mjx-container[jax='SVG']");
      const expected = document.querySelectorAll(".arithmatex").length;
      if (errors.length || math.length !== expected) {
        throw new Error("Math verification failed (" + errors.length + " errors; " +
                        math.length + "/" + expected + " expressions)");
      }
      if (window.portableReport.state === "error") return;
      window.portableReport = {state: "ready", images: images.length, math: math.length,
                              mathErrors: errors.length};
      document.documentElement.dataset.portableState = "ready";
      const note = document.getElementById("portable-status");
      note.textContent = "Offline rendering verified: " + images.length + " figures, " +
                         math.length + " equations.";
      note.dataset.images = images.length;
      note.dataset.math = math.length;
      note.dataset.mathErrors = errors.length;
    }).catch(portableFail)
  }
};
"""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_record(path: Path, relative: str) -> dict:
    """Rows are text lines for text files; null means not a tabular/text artifact."""
    data = path.read_bytes()
    is_license = path.name.endswith("LICENSE")
    text = path.suffix in {".html", ".json", ".txt", ".js", ".py", ".md"} or is_license
    return {"path": relative, "format": "txt" if is_license else path.suffix.lstrip(".") or "text",
            "rows": len(data.splitlines()) if text else None,
            "bytes": len(data), "sha256": digest(data)}


def load_assets(cache_dir: Path, *, fetch: bool = False) -> dict[str, bytes]:
    """Fetch only these pinned public URLs, never document-provided URLs."""
    result = {}
    for name, (url, expected) in ASSETS.items():
        path = cache_dir / name
        if path.exists():
            data = path.read_bytes()
        elif fetch:
            with urlopen(url, timeout=60) as response:
                data = response.read()
            if digest(data) != expected:
                raise ValueError(f"Asset integrity mismatch: {name}")
            cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        else:
            raise ValueError(f"Missing offline asset: {path}; run once with --fetch-assets")
        if digest(data) != expected:
            raise ValueError(f"Asset integrity mismatch: {path}; remove it before fetching again")
        result[name] = data
    return result


def relative_url(target: Path, start: Path) -> str:
    return quote(Path(os.path.relpath(target, start)).as_posix())


def peer_document(relative: Path) -> bool:
    return (
        relative == Path("README.md")
        or (relative.parts[0] in {"docs", "reports"} and relative.suffix == ".md")
    )


def peer_text(relative: Path) -> bool:
    return relative == Path("requirements.txt") or (
        relative.parts[0] in {"docs", "reports"} and relative.suffix == ".txt"
    )


def peer_image(relative: Path, image_roots: tuple[Path, ...] = IMAGE_ROOTS) -> bool:
    return relative.suffix.lower() in MIMES and (
        any(relative.is_relative_to(folder) for folder in image_roots)
    )


def package_stem(name: str | None, version: str | None, date: str | None) -> str | None:
    """Validate labels, not filesystem paths. All three labels form one package identity."""
    if name is version is date is None:
        return None
    if not all((name, version, date)):
        raise ValueError("--name, --version and --date must be supplied together")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,79}", name):
        raise ValueError("Invalid name: use 1–80 ASCII letters, digits or hyphens")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,39}", version) or version.endswith("."):
        raise ValueError("Invalid version: use ASCII letters, digits, dots or hyphens")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("Invalid date: expected YYYY-MM-DD")
    calendar_date.fromisoformat(date)
    return f"{name}_v{version}_{date}"


def select_sources(root: Path, include: list[str] | None = None) -> list[Path]:
    """Select exact public Markdown paths; never follow linked documents recursively."""
    root = root.resolve()
    if include is None:
        candidates = [p for pattern in ("README.md", "docs/**/*.md", "reports/**/*.md")
                      for p in sorted(root.glob(pattern)) if p.is_file()]
    else:
        candidates = []
        for value in include:
            relative = Path(value)
            if relative.is_absolute() or relative.drive or ".." in relative.parts:
                raise ValueError(f"Requested source must be root-relative: {value}")
            candidates.append(root / relative)
    selected = {}
    for source in candidates:
        relative = safe_relative(source, root)
        if not peer_document(relative):
            raise ValueError(f"Not a peer document: {relative.as_posix()}")
        if not source.is_file():
            raise ValueError(f"Missing requested source: {relative.as_posix()}")
        selected[source.resolve()] = None
    return list(selected)


def safe_relative(target: Path, root: Path) -> Path:
    """Resolve before checking the allowlist, so symlinks cannot bypass it."""
    try:
        relative = target.resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError("Document dependency escapes repository root") from exc
    if not relative.parts or any(part.startswith(".") for part in relative.parts):
        raise ValueError("Hidden or root directory dependency is not eligible for export")
    return relative


class PortableBody(HTMLParser):
    """Rewrite HTML attributes with a dependency allowlist, preserving visible content."""

    def __init__(self, source: Path, root: Path, pages: dict[Path, Path],
                 image_roots: tuple[Path, ...] = IMAGE_ROOTS):
        super().__init__(convert_charrefs=False)
        self.source, self.root, self.pages = source, root, pages
        self.image_roots = image_roots
        self.parts: list[str] = []
        self.ids: set[str] = {"portable-exclusions"}
        self.links: list[tuple[Path, str]] = []
        self.exclusions: set[str] = set()
        self.inputs: set[Path] = set()
        self.attachments: set[Path] = set()
        self.image_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in TAGS:
            raise ValueError(f"Unsupported HTML dependency <{tag}> in {self.source.name}")
        if "mermaid" in attrs.get("class", "").split():
            raise ValueError(f"Unsupported dependency Mermaid in {self.source.name}")
        for key in attrs:
            if key.startswith("on") or key in {"srcset", "background", "formaction"}:
                raise ValueError(f"Unsupported HTML dependency attribute: {key}")
            if key == "style" and not re.fullmatch(
                r"text-align[:]\s*(left|right|center);?", attrs[key]
            ):
                raise ValueError("Unsupported inline style dependency")
            if key in {"src", "href"} and (tag, key) not in {("img", "src"), ("a", "href")}:
                raise ValueError(f"Unsupported URL attribute: {tag}.{key}")
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "img":
            if not attrs.get("src"):
                raise ValueError("Missing image src")
            attrs["src"] = self.rewrite(attrs["src"], image=True)
            if not attrs["src"]:
                self.parts.append(
                    '<span class="portable-excluded">Figure excluded from portable edition: '
                    f'{html.escape(attrs.get("alt", ""))} (reproduction/data dependency).</span>'
                )
                return
            # Load every figure now, not only those initially in the viewport.
            attrs.pop("loading", None)
        if tag == "a" and attrs.get("href"):
            original = attrs["href"]
            attrs["href"] = self.rewrite(original)
            if attrs["href"] == "#portable-exclusions":
                attrs["title"] = "Not included in this edition (selection/data scope): " + original
                attrs["class"] = attrs.get("class", "") + " portable-excluded"
            elif urlsplit(original).scheme:
                attrs["title"] = "External reference — requires internet"
                attrs["class"] = attrs.get("class", "") + " portable-external"
        self.parts.append("<" + tag + "".join(
            f' {key}="{html.escape(value, quote=True)}"' if value is not None else f" {key}"
            for key, value in attrs.items()
        ) + ">")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def handle_comment(self, data):
        self.parts.append(f"<!--{data}-->")

    def rewrite(self, url: str, *, image: bool = False) -> str:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc:
            if not image and parsed.scheme in {"https", "http", "mailto"}:
                return url
            raise ValueError(f"Unsupported remote/embedded dependency in {self.source.name}")
        if parsed.query:
            raise ValueError(f"Unsupported query in local dependency: {url}")
        target = (self.source.parent / unquote(parsed.path)).resolve() if parsed.path else self.source
        relative = safe_relative(target, self.root)
        if image:
            if not peer_image(relative, self.image_roots):
                if relative.parts[0] != "runs" and not relative.is_relative_to(Path("data")):
                    raise ValueError(f"Unsupported image dependency: {url}")
                if any(relative.is_relative_to(folder) for folder in self.image_roots):
                    raise ValueError(f"Unsupported image format: {url}")
                # Generated outputs are deliberately not consumed, even as figures.
                self.exclusions.add(url)
                return ""
            if not target.is_file():
                raise ValueError(f"Missing image: {relative.as_posix()}")
            data = target.read_bytes()
            signatures = {".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8",
                          ".jpeg": b"\xff\xd8", ".gif": b"GIF", ".webp": b"RIFF"}
            if not data.startswith(signatures[target.suffix.lower()]):
                raise ValueError(f"Invalid image (or unresolved LFS pointer): {relative.as_posix()}")
            self.inputs.add(target)
            self.image_count += 1
            return f"data:{MIMES[target.suffix.lower()]};base64," + base64.b64encode(data).decode()
        if peer_document(relative):
            if not target.is_file():
                raise ValueError(f"Missing linked document: {relative.as_posix()}")
            if target not in self.pages:
                self.exclusions.add(url)
                return "#portable-exclusions"
            destination = self.pages[target]
            self.links.append((target, unquote(parsed.fragment)))
        elif peer_text(relative):
            if not target.is_file():
                raise ValueError(f"Missing linked text: {relative.as_posix()}")
            if parsed.fragment:
                raise ValueError(f"Unsupported text-file fragment: {url}")
            self.attachments.add(target)
            self.inputs.add(target)
            destination = relative
        else:
            self.exclusions.add(url)
            return "#portable-exclusions"
        result = relative_url(destination, self.pages[self.source].parent)
        return result + ("#" + parsed.fragment if parsed.fragment else "")


def _check_output(out_dir: Path, root: Path, cache_dir: Path) -> None:
    if out_dir.is_relative_to(root) and not out_dir.is_relative_to(root / "build"):
        raise ValueError("Portable output inside the repository must be under build/")
    if out_dir == root / "build" or cache_dir.is_relative_to(out_dir):
        raise ValueError("Output must not contain the build cache")
    if out_dir.exists() and any(out_dir.iterdir()):
        marker = out_dir / MANIFEST
        if not marker.is_file():
            raise ValueError("Refusing to overwrite a non-export directory")
        manifest = json.loads(marker.read_text(encoding="utf-8"))
        expected = {item["path"] for item in manifest["outputs"]} | {MANIFEST}
        actual = {p.relative_to(out_dir).as_posix() for p in out_dir.rglob("*") if p.is_file()}
        if manifest.get("kind") != "portable-docs-v1" or actual != expected:
            raise ValueError("Refusing to overwrite an export with unmanaged files")


def export_portable(
    sources: list[Path], out_dir: Path, *, root: Path, cache_dir: Path,
    fetch_assets: bool, render_markdown: Callable[[str], str], css: str,
    name: str | None = None, version: str | None = None, date: str | None = None,
    image_roots: tuple[Path, ...] = IMAGE_ROOTS,
) -> Path:
    """Validate everything before publishing; each HTML has all its runtime assets."""
    root, out_dir, cache_dir = root.resolve(), out_dir.resolve(), cache_dir.resolve()
    stem = package_stem(name, version, date)
    if stem and out_dir.name != stem:
        raise ValueError(f"Named output directory must be called {stem}")
    for folder in image_roots:
        safe_relative(root / folder, root)
    # SOURCE_DATE_EPOCH is an optional reproducible-build clock, never a report date label.
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    generated = (datetime.fromtimestamp(int(epoch), UTC) if epoch is not None
                 else datetime.now(UTC)).isoformat(timespec="seconds")
    _check_output(out_dir, root, cache_dir)
    if not sources:
        raise ValueError("No peer documents found")
    sources = [source.resolve() for source in sources]
    pages = {}
    for source in sources:
        relative = safe_relative(source, root)
        if not peer_document(relative):
            raise ValueError(f"Not a peer document: {relative.as_posix()}")
        if not source.is_file():
            raise ValueError(f"Missing requested source: {relative.as_posix()}")
        pages[source] = relative.with_suffix(".html")
    assets = load_assets(cache_dir, fetch=fetch_assets)
    texts = {source: source.read_text(encoding="utf-8") for source in sources}
    titles, bodies = {}, {}
    for source in sources:
        title = re.search(r"^#\s+(.+)$", texts[source], re.MULTILINE)
        titles[source] = title.group(1) if title else source.stem
        body = PortableBody(source, root, pages, image_roots)
        rendered = render_markdown(texts[source])
        if re.search(r'class="[^"]*language-mermaid', rendered):
            raise ValueError(f"Unsupported dependency Mermaid in {source.name}")
        if re.search(r"\\(?:require|includegraphics)\b", rendered):
            raise ValueError(f"Unsupported dynamic TeX dependency in {source.name}")
        body.feed(rendered)
        body.close()
        bodies[source] = body
    for source, body in bodies.items():
        for target, fragment in body.links:
            if fragment and fragment not in bodies[target].ids:
                raise ValueError(f"Missing linked section: {source.name} -> {target.name}#{fragment}")

    script = assets["mathjax-3.2.2-tex-svg-full.js"].decode("utf-8")
    # HTML ends script elements even inside JS strings.
    script = re.sub("</script", r"<\\/script", script, flags=re.IGNORECASE)
    license_text = assets["mathjax-3.2.2-LICENSE"].decode("utf-8")
    extra_css = (
        ".portable-excluded:after{content:' [not included]';font-size:.85em}"
        ".portable-external:after{content:' [online]';font-size:.85em}"
        "#portable-status{border:1px solid #d0d7de;padding:.5rem}"
        "@media(max-width:800px){body{display:block}nav{position:static;width:auto;height:auto}"
        "main{padding:1rem}}@media print{nav,#portable-status{display:none}}"
    )

    def page(title: str, body: str, current: Path) -> str:
        nav = f'<a href="{relative_url(Path("index.html"), current.parent)}">Contents</a>'
        nav += "".join(
            f'<a href="{relative_url(pages[src], current.parent)}">{html.escape(titles[src])}</a>'
            for src in sources
        )
        return (
            '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta http-equiv="Content-Security-Policy" content="{html.escape(CSP, quote=True)}">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{css}{extra_css}</style></head>"
            f"<body><nav>{nav}</nav><main>"
            '<p id="portable-status">Rendering offline figures and equations…</p>'
            '<noscript>JavaScript must be enabled to format equations. Figures and text '
            "remain available.</noscript>"
            f"{body}<details><summary>MathJax 3.2.2 — license and integrity</summary>"
            f"<p>SVG output; renderer SHA-256: {ASSETS['mathjax-3.2.2-tex-svg-full.js'][1]}</p>"
            f"<pre>{html.escape(license_text)}</pre></details></main>"
            f"<script>{RUNTIME}</script><script>{script}</script></body></html>\n"
        )

    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="portable-", dir=out_dir.parent) as temporary:
        staging = Path(temporary)
        inputs = set(sources)
        attachments = set()
        exclusions = {}
        for source, body in bodies.items():
            inputs.update(body.inputs)
            attachments.update(body.attachments)
            exclusions[source.relative_to(root).as_posix()] = sorted(body.exclusions)
            content = "".join(body.parts)
            note = (
                '<aside id="portable-exclusions"><h2>Portable edition — scope</h2>'
                '<p>Original report text, numbers and equations are unchanged. Only selected '
                'documents appear in Contents; linked documents outside the selection are '
                'marked [not included], not recursively added. Cited eligible text files '
                'travel with this package. Reproduction code, data, caches '
                'and generated analysis outputs are not included. Curated report figures are '
                'embedded. Links marked [online] require internet; none is needed for rendering.'
                '</p><ul>' + "".join(
                    f"<li>Not included: <code>{html.escape(url)}</code></li>"
                    for url in sorted(body.exclusions)
                ) + "</ul></aside>"
            )
            destination = staging / pages[source]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(page(titles[source], content + note, pages[source]),
                                   encoding="utf-8", newline="\n")
        for source in sorted(attachments):
            destination = staging / source.relative_to(root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        (staging / "MathJax-LICENSE.txt").write_bytes(assets["mathjax-3.2.2-LICENSE"])
        index_body = (
            f"<h1>{html.escape(stem or 'Portable documentation')}</h1>"
            "<p>Open this file in a standard browser after extracting the entire ZIP. "
            "No server, Python, extensions or internet connection is required. Each report "
            "HTML embeds its own figures and equation renderer; linked documents require "
            "the rest of this package. Exclusions are listed on each page.</p>"
        )
        (staging / "index.html").write_text(
            page("Portable documentation", index_body, Path("index.html")),
            encoding="utf-8", newline="\n",
        )
        outputs = [file_record(p, p.relative_to(staging).as_posix())
                   for p in sorted(staging.rglob("*")) if p.is_file()]
        manifest = {
            "kind": "portable-docs-v1", "renderer": "MathJax 3.2.2 tex-svg-full",
            "exporter_version": EXPORTER_VERSION,
            "exporter_sha256": digest(Path(__file__).read_bytes()),
            "package": {"name": name, "version": version, "date_label": date,
                        "root_folder": stem},
            "generated_utc": generated,
            "clock": "SOURCE_DATE_EPOCH" if epoch is not None else "system UTC",
            "selection": [src.relative_to(root).as_posix() for src in sources],
            "image_roots": [p.as_posix() for p in image_roots],
            "versions": {p: package_version(p) for p in ("Markdown", "pymdown-extensions")},
            "assets": [{"name": name, "url": url, "sha256": sha}
                       for name, (url, sha) in ASSETS.items()],
            "inputs": [file_record(p, p.relative_to(root).as_posix()) for p in sorted(inputs)],
            "outputs": outputs, "exclusions": exclusions,
            "figures": {src.relative_to(root).as_posix(): body.image_count
                        for src, body in bodies.items()},
            "row_convention": "Text lines for text artifacts; null for non-text artifacts.",
            "integrity_note": "Manifest and ZIP hashes are recorded by the delivery record, "
                              "not recursively inside this manifest.",
        }
        (staging / MANIFEST).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
        )
        # Finish the archive before touching a previous delivery; roll back both on failure.
        archive_path = staging / "_delivery.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file() and path != archive_path:
                    relative = path.relative_to(staging)
                    member = Path(stem) / relative if stem else relative
                    info = zipfile.ZipInfo(member.as_posix(), (2020, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    archive.writestr(info, path.read_bytes())
        with tempfile.TemporaryDirectory(prefix="portable-backup-", dir=out_dir.parent) as backup:
            previous = Path(backup)
            zip_path = out_dir.with_suffix(".zip")
            old_dir, old_zip = previous / "directory", previous / "archive.zip"
            if out_dir.exists():
                out_dir.rename(old_dir)
            try:
                if zip_path.exists():
                    zip_path.rename(old_zip)
                archive_path.replace(zip_path)
                shutil.copytree(staging, out_dir)
            except BaseException:
                if out_dir.exists():
                    shutil.rmtree(out_dir)
                if zip_path.exists() and not archive_path.exists():
                    zip_path.unlink()
                if old_dir.exists():
                    old_dir.rename(out_dir)
                if old_zip.exists():
                    old_zip.rename(zip_path)
                raise
    return out_dir / "index.html"
