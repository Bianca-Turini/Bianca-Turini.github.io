#!/usr/bin/env python3
"""Build assets/cv-Bianca-Turini.pdf from the content of index.html.

The website is the single source of truth: edit index.html, then run

    python3 tools/build_cv.py

It writes an intermediate tools/cv.html (not linked from the site) and prints it
to assets/cv-Bianca-Turini.pdf with headless Google Chrome. Requires: beautifulsoup4.
"""
import copy
import datetime
import pathlib
import subprocess
import sys

from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
OUT_HTML = ROOT / "tools" / "cv.html"
OUT_PDF = ROOT / "assets" / "cv-Bianca-Turini.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Contact address as printed on the CV.
EMAIL = "bianca.turini at icfo.eu"  # written out without "@" to keep spam bots away
WEBSITE = "bianca-turini.github.io"

site = BeautifulSoup(SRC.read_text(encoding="utf-8"), "html.parser")


def clean(node):
    """Copy a node, dropping site-only bits (figures, buttons, tags)."""
    node = copy.copy(node)
    for k in node.select(".kind"):  # drop the tag and the line break after it
        nxt = k.find_next_sibling()
        if nxt is not None and nxt.name == "br":
            nxt.decompose()
    for sel in ["figure", ".pub-links", ".kind", "video", ".cites"]:
        for el in node.select(sel):
            el.decompose()
    for a in node.find_all("a"):
        for attr in ("target", "rel", "class", "title"):
            a.attrs.pop(attr, None)
        if a.get("href", "").startswith("#") or not a.get("href"):
            a.unwrap()
    return node


def inner(node):
    return "".join(str(c) for c in node.contents).strip()


def rows_from(ul):
    """Turn a website <ul class="rows"> into (date, body_html, tags) tuples."""
    out = []
    for li in ul.find_all("li", recursive=False):
        meta = li.find(class_="meta")
        date = meta.get_text(" ", strip=True) if meta else ""
        tags = [k.get_text(strip=True) for k in li.select(".kind")]
        body = clean(li)
        m = body.find(class_="meta")
        if m:
            m.decompose()
        html = inner(body)
        # collapse leading <br> left behind by removed tags
        while html.startswith("<br/>") or html.startswith("<br>"):
            html = html.split(">", 1)[1].strip()
        html = html.replace("<span>\n            <br/>", "<span>")
        out.append((date, html, tags))
    return out


def row_html(date, body, tags=()):
    badge = "".join(f'<span class="tag">{t}</span>' for t in tags)
    return f'<li><span class="date">{date}</span><div>{badge}{body}</div></li>'


def section(title, items):
    if not items:
        return ""
    return f'<section><h2>{title}</h2><ul class="rows">{"".join(items)}</ul></section>'


# ── Header ──────────────────────────────────────────────────────────────
name = site.h1.get_text(strip=True).rstrip(".")
role = site.select_one(".lede-label").get_text(strip=True)
links = {a.get_text(strip=True).replace(" ↗", ""): a["href"] for a in site.select(".links a")}

contact = [f'<a>{EMAIL}</a>', f'<a href="https://{WEBSITE}">{WEBSITE}</a>']
for label in ("ORCID", "Google Scholar", "LinkedIn"):
    if label in links:
        contact.append(f'<a href="{links[label]}">{label}</a>')

# ── Profile: the About paragraphs ───────────────────────────────────────
about = site.select_one("#about .prose")
profile = "".join(str(clean(p)) for p in about.find_all("p", recursive=False))

# ── Expertise ──────────────────────────────────────────────────────────
exp = site.select_one("#expertise .rows")
expertise = [row_html(d, b) for d, b, _ in rows_from(exp)] if exp else []

# ── Education / research stays ──────────────────────────────────────────
edu_rows = rows_from(site.select_one("#education .rows"))
education = [row_html(d, b) for d, b, _ in edu_rows if "Research stay" not in b]
stays = [row_html(d, b.replace("<strong>Research stay</strong><br/>", ""))
         for d, b, _ in edu_rows if "Research stay" in b]
for li in site.select(".rows li"):  # research visits announced in News
    txt = li.get_text(" ", strip=True)
    if "research visit" in txt:
        d = li.find(class_="meta").get_text(strip=True)
        body = clean(li)
        body.find(class_="meta").decompose()
        stays.insert(0, row_html(d, inner(body)))

# ── Awards & fellowships ────────────────────────────────────────────────
awards = []
for li in site.select("#talks li"):
    for k in li.select(".kind.award"):
        label = k.get_text(strip=True).lstrip("★ ").strip()
        if "invited" in label.lower():
            continue
        title = li.find("strong").get_text(" ", strip=True)
        where = li.find(class_="where").get_text(" ", strip=True)
        d = li.find(class_="meta").get_text(strip=True)
        awards.append(row_html(d, f"<strong>{label}</strong>, poster prize<br/>"
                                  f'<span class="where">{where} — <em>{title}</em></span>'))
for d, b, _ in edu_rows:
    if "la Caixa" in b:
        awards.append(row_html(d, "<strong>“la Caixa” Foundation INPhINIT doctoral fellowship</strong><br/>"
                                  '<span class="where">Competitive Europe-wide PhD fellowship</span>'))

# ── Publications ────────────────────────────────────────────────────────
pubs = []
for li in site.select(".pubs > li"):
    n = li.find(class_="meta").get_text(strip=True).split("·")[0].strip()
    title = li.select_one(".title").get_text(strip=True)
    authors = inner(li.select_one(".authors"))
    venue = inner(li.select_one(".venue"))
    doi = li.get("data-doi")
    cites = li.select_one(".cites b")
    extra = f' · cited by {cites.get_text(strip=True)}' if cites else ""
    link = f' · <a href="https://doi.org/{doi}">doi:{doi}</a>' if doi else ""
    pubs.append(f'<li><span class="date">{n}</span><div>{authors}. '
                f'<strong>{title}</strong>. {venue}{link}<span class="muted">{extra}</span></div></li>')

# ── Talks / posters / schools ───────────────────────────────────────────
talk_lists = {}
for h3 in site.select("#talks h3.sub"):
    talk_lists[h3.get_text(strip=True)] = rows_from(h3.find_next_sibling("ul"))

invited = [row_html(d, b) for d, b, t in talk_lists.get("Talks", []) if any("Invited" in x for x in t)]
talks = [row_html(d, b) for d, b, t in talk_lists.get("Talks", []) if not any("Invited" in x for x in t)]
posters = [row_html(d, b, [x.lstrip("★ ").strip() for x in t]) for d, b, t in talk_lists.get("Posters", [])]
schools = [row_html(d, b) for d, b, _ in talk_lists.get("Schools", [])]

# ── Service ─────────────────────────────────────────────────────────────
service = [row_html(d, b) for d, b, _ in rows_from(site.select_one("#service .rows"))]
_out = site.select_one("#outreach .rows")
outreach = [row_html(d, b) for d, b, _ in rows_from(_out)] if _out else []

today = datetime.date.today().strftime("%B %Y")

html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{name} — CV</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  @page {{ size: A4; margin: 14mm 15mm 14mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font: 9pt/1.30 "IBM Plex Sans", sans-serif; color: #111316; }}
  a {{ color: inherit; text-decoration: none; }}
  p {{ margin: 0 0 .5em; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  header {{ border-bottom: 1.5px solid #111316; padding-bottom: 9pt; margin-bottom: 4pt; }}
  .role {{ font: 500 7.5pt "IBM Plex Mono", monospace; letter-spacing: .1em; text-transform: uppercase; color: #5f646b; }}
  h1 {{ font-size: 21pt; font-weight: 700; text-transform: uppercase; letter-spacing: .01em; margin: 3pt 0 6pt; line-height: 1; }}
  .contact {{ font: 7.8pt "IBM Plex Mono", monospace; letter-spacing: .04em; }}
  .contact a + a::before {{ content: "·"; margin: 0 .6em; color: #1f3cff; }}
  section {{ position: relative; padding: 6pt 0 6pt 34mm; border-bottom: .5px solid #d5d8dc; }}
  section:last-of-type {{ border-bottom: 0; }}
  h2 {{ position: absolute; left: 0; width: 30mm; margin: 1pt 0 0; font: 700 8pt "IBM Plex Sans", sans-serif; letter-spacing: .1em; text-transform: uppercase; }}
  .rows li {{ display: grid; grid-template-columns: 22mm 1fr; gap: 3mm; padding: 1.8pt 0; break-inside: avoid; }}
  .date {{ font: 7.5pt "IBM Plex Mono", monospace; letter-spacing: .04em; text-transform: uppercase; color: #5f646b; padding-top: 1pt; }}
  .rows strong {{ font-weight: 600; }}
  .where, .muted {{ color: #5f646b; }}
  .profile p {{ max-width: 150mm; }}
  .profile strong {{ font-weight: 600; }}
  .tag {{ display: inline-block; font: 500 6.5pt "IBM Plex Mono", monospace; letter-spacing: .06em; text-transform: uppercase;
          background: #1f3cff; color: #fff; padding: 0 3pt; margin-right: 4pt; vertical-align: 1pt; }}
  .pubs li strong {{ font-weight: 600; }}
  .rows a, .profile a {{ border-bottom: .5px solid #1f3cff; }}
  footer {{ margin-top: 6pt; font: 7pt "IBM Plex Mono", monospace; letter-spacing: .06em; text-transform: uppercase; color: #5f646b; }}
</style></head>
<body>
<header>
  <div class="role">{role}</div>
  <h1>{name}</h1>
  <div class="contact">{"".join(contact)}</div>
</header>
<section><h2>Profile</h2><div class="profile">{profile}</div></section>
{section("Expertise", expertise)}
{section("Education", education)}
{section("Research stays", stays)}
{section("Fellowships &amp; awards", awards)}
<section><h2>Publications</h2><ul class="rows pubs">{"".join(pubs)}</ul></section>
{section("Invited talks", invited)}
{section("Contributed talks", talks)}
{section("Posters", posters)}
{section("Schools", schools)}
{section("Service", service)}
{section("Outreach", outreach)}
<footer>Updated {today} · Full version with links: {WEBSITE}</footer>
</body></html>
"""

OUT_HTML.write_text(html, encoding="utf-8")
print(f"wrote {OUT_HTML.relative_to(ROOT)}")

if "--html-only" in sys.argv:
    sys.exit(0)

subprocess.run([
    CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
    "--virtual-time-budget=8000", f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri(),
], check=True, capture_output=True)
print(f"wrote {OUT_PDF.relative_to(ROOT)}")
