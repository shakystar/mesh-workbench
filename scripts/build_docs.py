"""Build crawlable HTML and raw Markdown without changing source documentation."""

import argparse
import html
import json
import re
import shutil
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://shakystar.github.io/mesh-workbench/"
# Public Search Console verification value; retain it to preserve ownership.
GOOGLE_SITE_VERIFICATION = "QKoJhACEHrA7Wxp-lbBRqSs65--gutjxEPhbl9uPN-A"
DESCRIPTION = "MIT-licensed Blender modeling tools for AI agents: Python and JSON CLI for mesh editing, procedural assemblies, surface patterns and local patch reconstruction."


def build(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "docs", output / "docs", dirs_exist_ok=True)
    shutil.copytree(
        ROOT / "examples",
        output / "examples",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    names = [
        "README.md",
        "CONTRIBUTING.md",
        "THIRD_PARTY_NOTICES.md",
        "LICENSE",
        "llms.txt",
        "tool-manifest.json",
    ]
    for name in names:
        shutil.copyfile(ROOT / name, output / name)
    css = """body{margin:0;background:#10151c;color:#e6edf3;font:17px/1.7 system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:32px 24px}nav{display:flex;gap:20px;flex-wrap:wrap;border-bottom:1px solid #384454;padding:16px 0}a{color:#8ccaff}h1,h2,h3{line-height:1.25;margin-top:1.6em}h1{font-size:2.4rem}pre{background:#19222d;padding:18px;overflow:auto;border:1px solid #384454;border-radius:8px}code{font-size:.9em}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;display:block;overflow:auto}th,td{border:1px solid #384454;padding:10px;vertical-align:top}blockquote{border-left:3px solid #8ccaff;padding-left:16px}footer{margin-top:40px;border-top:1px solid #384454;padding-top:16px;color:#aab8c7}@media(max-width:600px){main{padding:18px 12px}h1{font-size:1.9rem}}"""
    (output / "style.css").write_text(css, encoding="utf-8")
    pages = []
    sources = [ROOT / n for n in names if n.endswith(".md")] + sorted(
        (ROOT / "docs").rglob("*.md")
    )
    for source in sources:
        relative = source.relative_to(ROOT)
        destination = (
            Path("index.html")
            if relative.as_posix() == "README.md"
            else relative.with_suffix(".html")
        )
        content = source.read_text(encoding="utf-8")
        title = next(
            (
                line[2:].strip()
                for line in content.splitlines()
                if line.startswith("# ")
            ),
            source.stem,
        )
        body = markdown.markdown(content, extensions=["fenced_code", "tables", "toc"])

        def rewrite(match):
            href = match.group(1)
            if "://" in href or href.startswith(("#", "mailto:")):
                return match.group(0)
            path, separator, fragment = href.partition("#")
            resolved = (source.parent / path).resolve()
            if resolved.is_dir() and not (resolved / "index.html").exists():
                return (
                    'href="https://github.com/shakystar/mesh-workbench/tree/main/'
                    + resolved.relative_to(ROOT).as_posix()
                    + '"'
                )
            if path.endswith(".md"):
                target = (source.parent / path).resolve()
                if target in sources:
                    path = (
                        "index.html"
                        if relative.parent == Path(".") and path == "README.md"
                        else path[:-3] + ".html"
                    )
                    if target == ROOT / "README.md":
                        path = (
                            path[: -len("README.html")] + "index.html"
                            if path.endswith("README.html")
                            else path
                        )
            return 'href="' + path + (separator + fragment if separator else "") + '"'

        body = re.sub(r'href="([^"]+)"', rewrite, body)
        canonical = (
            BASE
            if destination.as_posix() == "index.html"
            else BASE + destination.as_posix()
        )
        verification = ""
        schema = ""
        if destination.name == "index.html":
            verification = f'<meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}">'
            data = {
                "@context": "https://schema.org",
                "@type": "SoftwareSourceCode",
                "name": "Mesh Workbench",
                "description": DESCRIPTION,
                "codeRepository": "https://github.com/shakystar/mesh-workbench",
                "url": BASE,
                "license": "https://opensource.org/license/mit",
                "programmingLanguage": "Python",
                "runtimePlatform": "Blender",
                "image": BASE + "docs/assets/drill-surface-after-hero.png",
            }
            schema = (
                '<script type="application/ld+json">' + json.dumps(data) + "</script>"
            )
        page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} | Mesh Workbench</title><meta name="description" content="{html.escape(DESCRIPTION)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(DESCRIPTION)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}docs/assets/drill-surface-after-hero.png"><link rel="stylesheet" href="{BASE}style.css">{verification}{schema}</head><body><main><nav><a href="{BASE}">Mesh Workbench</a><a href="{BASE}docs/AGENT_QUICKSTART.html">Agent quickstart</a><a href="{BASE}docs/reference/OPERATIONS.html">API</a><a href="{BASE}llms.txt">llms.txt</a><a href="https://github.com/shakystar/mesh-workbench">GitHub</a></nav>{body}<footer>Original project code: MIT. Blender is a separate dependency. <a href="{BASE}THIRD_PARTY_NOTICES.html">Licensing scope</a></footer></main></body></html>"""
        (output / destination).parent.mkdir(parents=True, exist_ok=True)
        (output / destination).write_text(page, encoding="utf-8")
        pages.append(canonical)
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join("<url><loc>" + html.escape(url) + "</loc></url>" for url in pages)
        + "</urlset>\n"
    )
    (output / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    # Verify published internal HTML links (including documents, recipes and images).
    missing = []
    for page in output.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        for link in re.findall(r'(?:href|src)="([^"]+)"', text):
            if link.startswith(BASE):
                target = output / link[len(BASE) :].split("#")[0]
            elif "://" in link or link.startswith(("#", "mailto:")):
                continue
            else:
                target = page.parent / link.split("#")[0]
            if not target.exists():
                missing.append((str(page.relative_to(output)), link))
    if missing:
        raise ValueError("Broken published links: " + str(missing))
    print(
        json.dumps(
            {
                "html_pages": len(pages),
                "output": str(output),
                "internal_links": "passed",
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runs/site")
    build(parser.parse_args().output)
