#!/usr/bin/env python3
"""Turn Obsidian-style markdown into something Zola accepts.

Copies the site into OUT_DIR and rewrites every page in content/ so you can
write plain markdown with no front matter at all:

  title  <- front matter `title`, else the first `# heading` (removed from the
            body so it is not shown twice), else the file name
  date   <- front matter `date`, else the date the file was first committed
            to git, else today
  tags   <- front matter `tags: [a, b]` (or `tags: a`), Obsidian style
  link   <- front matter `link: /some/url`: lists point there, not at the page
  draft  <- `draft: true` or `publish: false` hides the page
  redirect_from <- old URLs that should redirect to this page

Also, in the body (outside code):
  $x$, $$x$$     -> rendered with KaTeX in the browser
  [[note]], [[note|text]], [[note#Heading]] -> links to other pages
  ![[image.png]] -> image found anywhere in content/ or static/

Any other front matter keys (Obsidian properties) go into `extra`.

Usage: prepare.py SITE_DIR OUT_DIR
"""

import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ZOLA_KEYS = {"title", "description", "date", "updated", "weight", "draft",
             "slug", "template", "authors"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}


def git_created(path: Path, repo: Path) -> dt.date | None:
    try:
        out = subprocess.run(
            ["git", "log", "--follow", "--diff-filter=A", "--format=%as", "--", str(path)],
            cwd=repo, capture_output=True, text=True, check=True).stdout.split()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return dt.date.fromisoformat(out[-1]) if out else None


def split_front_matter(text: str) -> tuple[dict, str]:
    m = re.match(r"\A(?:---|\+\+\+)\s*\n(.*?)\n(?:---|\+\+\+)\s*(?:\n|\Z)", text, re.S)
    if not m:
        return {}, text
    if text.startswith("+++"):
        sys.exit("TOML front matter (+++) is not supported here, use --- YAML")
    return yaml.safe_load(m.group(1)) or {}, text[m.end():]


def slugify(s: str) -> str:
    return re.sub(r"[^\w]+", "-", s.lower()).strip("-")


# --- body transforms -------------------------------------------------------

MD_PUNCT = re.compile(r"([!-/:-@\[-`{-~])")  # every ASCII punctuation char


def md_literal(s: str) -> str:
    """Backslash-escape so markdown outputs exactly `s`."""
    return MD_PUNCT.sub(r"\\\1", s)


DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.S)
INLINE_MATH = re.compile(r"(?<![\\$])\$(?=\S)((?:\\.|[^$\\\n])+?)(?<=\S)\$(?!\d)")
WIKILINK = re.compile(r"(!?)\[\[([^\]|#]*)(#[^\]|]*)?(?:\|([^\]]*))?\]\]")


def transform_text(s: str, ctx: dict) -> str:
    def display(m):
        ctx["math"] = True
        body = re.sub(r"\n\s*\n", "\n", m.group(1))  # blank lines would split it
        return md_literal(r"\[" + body + r"\]")

    def inline(m):
        ctx["math"] = True
        return md_literal(r"\(" + m.group(1) + r"\)")

    def wikilink(m):
        embed, target, anchor, label = m.groups()
        target = target.strip()
        name = Path(target).name
        if embed and Path(name).suffix.lower() in IMAGE_EXT:
            url = ctx["files"].get(name)
            return f"![{label or ''}]({url})" if url else m.group(0)
        page = ctx["pages"].get(name.removesuffix(".md").lower())
        text = label or (target + (anchor or "")).lstrip("#") or target
        if not page:
            return text  # unknown note: keep the text, don't break the build
        frag = "#" + slugify(anchor[1:]) if anchor else ""
        return f"[{text}](@/{page}{frag})"

    s = DISPLAY_MATH.sub(display, s)
    s = INLINE_MATH.sub(inline, s)
    return WIKILINK.sub(wikilink, s)


def transform_body(body: str, ctx: dict) -> str:
    # leave fenced code blocks and inline code alone
    out = []
    for i, chunk in enumerate(re.split(r"(^(?:```|~~~).*?^(?:```|~~~)[^\n]*$)", body, flags=re.S | re.M)):
        if i % 2:
            out.append(chunk)
            continue
        parts = re.split(r"(`+[^`]*?`+)", chunk)
        out.append("".join(p if j % 2 else transform_text(p, ctx) for j, p in enumerate(parts)))
    return "".join(out)


# --- main --------------------------------------------------------------------

def process_page(src: Path, dst: Path, site: Path, pages: dict, files: dict):
    fm, body = split_front_matter(src.read_text(encoding="utf-8"))
    is_section = src.name == "_index.md"

    out = {k: fm.pop(k) for k in list(fm) if k in ZOLA_KEYS}

    if "title" not in out:
        m = re.match(r"\A\s*#[ \t]+(.+?)[ \t#]*\n", body + "\n")
        if m:
            out["title"] = m.group(1).strip()
            body = body[m.end():]
        else:
            out["title"] = src.stem.replace("_", " ").replace("-", " ")

    if fm.pop("publish", True) is False:
        out["draft"] = True
    if fm.get("redirect_from"):
        out["aliases"] = fm.pop("redirect_from")

    if not is_section:
        out.setdefault("date", git_created(src, site) or dt.date.today())
        tags = fm.pop("tags", None)
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        if tags:
            out["taxonomies"] = {"tags": [str(t).lstrip("#") for t in tags]}
    else:
        # section settings (sort_by, transparent, ...) pass straight through
        out.update(fm)
        fm = {}

    ctx = {"pages": pages, "files": files, "math": False}
    body = transform_body(body, ctx)

    extra = fm.pop("extra", {}) or {}
    extra.update(fm)  # leftover Obsidian properties
    if ctx["math"]:
        extra["math"] = True
    if extra:
        out["extra"] = extra

    dst.write_text("---\n" + yaml.safe_dump(out, allow_unicode=True, sort_keys=False)
                   + "---\n" + body, encoding="utf-8")


def main():
    site, out_dir = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(site, out_dir, ignore=shutil.ignore_patterns(
        ".git", ".venv", out_dir.name, "public", ".obsidian"))

    content = site / "content"
    pages = {p.stem.lower(): p.relative_to(content).as_posix()
             for p in content.rglob("*.md") if p.name != "_index.md"}
    files = {}
    for root, prefix in ((site / "static", ""), (content, "")):
        for f in root.rglob("*"):
            if f.is_file() and f.suffix != ".md":
                files.setdefault(f.name, "/" + prefix + f.relative_to(root).as_posix())

    for src in content.rglob("*.md"):
        process_page(src, out_dir / "content" / src.relative_to(content), site, pages, files)


if __name__ == "__main__":
    main()
