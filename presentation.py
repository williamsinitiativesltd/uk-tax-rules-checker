"""Formatting shared by the offline reports."""

from datetime import date
from decimal import Decimal
from html import escape, unescape
import re


SPECIALIST_QUESTIONS = "Questions for a tax specialist"


def money(amount: Decimal | int) -> str:
    amount = Decimal(amount)
    if amount == amount.to_integral_value():
        return f"£{amount:,.0f}"
    if amount == amount.quantize(Decimal("0.01")):
        return f"£{amount:,.2f}"
    return f"£{amount.normalize():,f}"  # exact, never rounded for display


def percent(rate: Decimal) -> str:
    return f"{(rate * 100).normalize():f}%"


def link(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def items(lines):
    return "<ul>" + "".join(f"<li>{line}</li>" for line in lines) + "</ul>"


# Markdown tables already contain the writer's formatted amounts and links.
COLUMN_TYPES = {
    "money": {"Income or price", "Adjusted net income", "Price", "Full allowance", "Personal allowance", "Agreed result",
              "Allowance reaches zero at", "Allowance £1 at", "Allowance £0 at", "Tax", "Expected result"},
    "number": {"Count"}, "year": {"Tax year", "Date or tax year"}, "date": {"From", "Last day", "Effective date", "Date run"},
    "hash": {"SHA-256"}, "identifier": {"Identifier"}
}


def source_links(url):
    raw = url.endswith("/data.xml")
    readable = url.removesuffix("/data.xml").replace("/api/content/", "/")
    return link(readable, "Read") + " · " + link(url, "Source XML" if raw else "Download source data")


COLLAPSE_AFTER = 20


def table(headers, rows, raw=False, summary=None, group_column=None):
    rows = list(rows)
    columns = []
    for index, header in enumerate(headers):
        if not any(str(row[index]).strip() for row in rows):
            continue
        if isinstance(header, tuple):
            name, kind = header
        else:
            name = header
            kind = next((t for t, names in COLUMN_TYPES.items() if name in names), "text")
        columns.append((index, name, kind))

    def attributes(kind):
        if kind in ("number", "money", "pounds"):
            return ' class="numeric"'
        if kind in ("date", "year", "identifier", "hash"):
            return f' class="{kind}"'
        return ""

    hashes = []
    head = "".join(f'<th scope="col"{attributes(kind)}>{escape(name)}</th>' for _, name, kind in columns)
    lines = []
    span_end = 0
    for row_index, row in enumerate(rows):
        cells = []
        for index, _, kind in columns:
            span = ""
            if index == group_column:
                if row_index < span_end:
                    continue
                span_end = row_index + 1
                while span_end < len(rows) and rows[span_end][index] == row[index]:
                    span_end += 1
                if span_end > row_index + 1:
                    span = f' rowspan="{span_end - row_index}"'
            val = str(row[index])
            if kind == "pounds":
                val = money(Decimal(val))
            elif kind == "year" and val.isdigit():
                val = f"{val}-{(int(val) + 1) % 100:02}"
            elif kind == "date" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", val):
                val = long_date(val)
            html = val if raw else escape(val)
            if kind == "hash":
                hashes.append(f"{row[0]}: <code>{escape(val)}</code>" if raw else
                              f"{escape(str(row[0]))}: <code>{escape(val)}</code>")
                html = f'<code title="{escape(val)}">{escape(val[:12])}…</code>'
            elif kind == "identifier":
                html = ", ".join("<code>" + escape(v) + "</code>" for v in val.split(", "))
            plain = re.sub("<[^>]+>", "", html)
            style = "number" if re.fullmatch(r"£?[\d,]+(?:\.\d+)?%?", plain) else kind
            if kind == "number" and not re.fullmatch(r"[\d,.]+", plain):
                style = "text"
            cells.append(f"<td{attributes(style)}{span}>{html}</td>")
        lines.append("<tr>" + "".join(cells) + "</tr>")
    body = '<div class="timeline"><table><thead><tr>' + head + '</tr></thead><tbody>' + "".join(lines) + "</tbody></table></div>"
    if len(rows) > COLLAPSE_AFTER:
        body = "<details><summary>" + escape(summary or f"Show all {len(rows)} rows") + "</summary>" + body + "</details>"
    if hashes:
        body += "<details><summary>Full SHA-256 values</summary>" + items(hashes) + "</details>"
    return body


def download_dates(index):
    days = sorted({entry["fetched"][:10] for name, entry in index.items() if name.startswith("legislation/")})
    return ", ".join(date.fromisoformat(day).strftime("%d %B %Y") for day in days)


def long_date(day):
    if isinstance(day, str):
        day = date.fromisoformat(day)
    return f"{day.day} {day:%B %Y}"


STYLE = """
* { box-sizing:border-box }
html { font: 1rem/1.55 system-ui,sans-serif; color:#1a231b; background:white }
body { max-width:76rem; margin:auto; padding:2rem clamp(1rem,4vw,4rem) }
nav { display:flex; flex-wrap:wrap; gap:.5rem 1.5rem; padding-bottom:1rem; border-bottom:2px solid #355636 }
a { color:#355636; text-underline-offset:.18em }
:focus-visible { outline:3px solid currentColor; outline-offset:3px }
h1,h2,h3 { line-height:1.2; text-wrap:balance }
h1 { font-size:clamp(2rem,4vw,3rem); max-width:34ch }
h2 { font-size:1.65rem; margin-top:2rem }
p,li { max-width:80ch }
li { margin-block:.35rem }
#in-short,.summary { border-left:4px solid #355636; background:#f2f5f2; padding:1rem 1.4rem; margin:1rem 0 }
#in-short h2,.summary h2 { margin-top:0 }
#three-findings { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem }
#three-findings h2 { grid-column:1/-1; margin-bottom:0 }
#three-findings section { padding:0 1rem; border:1px solid #c3cec4; border-top:3px solid #355636 }
@media (max-width:48rem) { #three-findings { grid-template-columns:1fr } }
details { padding:.6rem 0; border-bottom:1px solid #d5ddd5 }
summary { color:#355636; cursor:pointer; font-weight:650 }
.timeline,.drawing { overflow-x:auto }
table { border-collapse:collapse; width:100%; font-size:.94rem; margin:.8rem 0 }
th,td { text-align:left; vertical-align:top; padding:.5rem; border-bottom:1px solid #d5ddd5 }
th { background:#f2f5f2 }
.numeric,.year,.date,.timestamp,.hash { white-space:nowrap }
.numeric:has(a + a) { white-space:normal }
.numeric { text-align:right; font-variant-numeric:tabular-nums }
.hash,.identifier { width:1%; font-size:.82em }
.identifier code { white-space:nowrap }
code,pre { overflow-wrap:anywhere }
/* In a table, "anywhere" lets the column shrink below a field name and split it on a phone; break-word keeps names whole. */
td code { overflow-wrap:break-word }
#how-it-works table { min-width:34rem }
thead { display:table-header-group }
pre { white-space:pre-wrap }
figure { margin:1rem 0; max-width:50rem }
.drawing .arrow { fill:none; stroke:#1a231b; stroke-width:2 }
.map-node { fill:#f2f5f2; stroke:#d5ddd5 }
figure figcaption { margin:.3rem 0 }
figure .drawing { position:relative }
.chart-pair { max-width:50rem; display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem }
@media screen and (max-width:44rem) { .chart-pair { grid-template-columns:1fr } }
#checker .drawing { container-type:inline-size }
.shape { position:absolute; left:21%; max-width:78%; white-space:pre-wrap; font:2cqw/1.2 monospace }
.shape.input { top:18% }
.shape.output { top:49% }
svg { display:block; width:100%; height:auto; max-width:50rem }
footer { margin-top:2rem; padding-top:1rem; border-top:1px solid #c3cec4 }
#calculator label,#calculator output { display:block; margin:.5rem 0 }
@page { size:A4; margin:10mm 12mm }
@media print {
  html { font-size:10pt; line-height:1.35 }
  body { max-width:none; padding:0 }
  nav,.back,#search { display:none }
  details::details-content { display:block; content-visibility:visible; height:auto }
  details > * { display:block }
  summary { list-style:none }
  .timeline,.drawing { overflow:visible }
  table { font-size:9pt }
  .identifier code { white-space:normal }
  tr,figure,blockquote { break-inside:avoid }
  h1,h2,h3,summary { break-after:avoid }
  main > section:has(> h2) { break-before:page }
  body:not(.guide) #in-short { break-before:auto }
  .guide pre { break-inside:avoid }
  .brief { font-size:9pt; line-height:1.17 }
  .brief main > section,.about main > section { break-before:auto }
  figure details { display:none }
  .brief #three-findings { display:block }
  .brief #three-findings section { margin:.3rem 0; break-inside:avoid }
  .brief #in-short { padding:.45rem 1rem; margin:.45rem 0 }
  .brief p,.brief li,.brief h3 { margin:.2em 0; max-width:none }
  .brief h1 { margin:.25em 0; font-size:20pt; max-width:none }
  .brief h2 { margin:.35em 0 .15em; font-size:12.5pt }
  .brief ul { margin:.4em 0 }
  .brief table { font-size:inherit }
  .brief figure { max-width:45rem; margin:.2rem auto }
  /* On paper the diagrams cover the steps and the links in Read more cannot be followed, so both give way
     to keep the summary to two sides. */
  .brief #how-it-works table,.brief #read-more { display:none }
  .brief #what-this-is-not ul { columns:2; column-gap:1.5rem }
  .brief #what-this-is-not li { break-inside:avoid }
  .brief footer { margin-top:.4rem; padding-top:.3rem }
}
"""


def document(title, body, footer, nav, body_class="pack", description=None):
    navigation = " ".join(link(path + ".html", label) for label, path in nav.items())
    if description is None:
        first = re.search(r"<p(?: [^>]*)?>(.*?)</p>", body, re.S)
        plain = unescape(re.sub("<[^>]+>", "", first[1] if first else title))
        description = re.split(r"(?<=\.)\s+", " ".join(plain.split()), maxsplit=1)[0]
    page = (f'<!doctype html>\n<html lang="en-GB"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)}</title>'
            f'<meta name="description" content="{escape(description)}"><meta name="robots" content="noindex, nofollow">'
            f'<style>{STYLE}</style></head><body class="{body_class}"><nav>{navigation}</nav>'
            f'<main><h1>{escape(title, quote=False)}</h1>{body}</main>'
            f'<footer>{footer}</footer></body></html>\n')
    if "{{" in page or "&gt; DEV:" in page:
        raise ValueError("Unresolved content marker in " + title)
    return page.replace("\u2013", "-").replace("\u2014", "-")
