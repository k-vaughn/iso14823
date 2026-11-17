"""Render register Markdown from ``data/registry.json``."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlencode

from annex import (
    COUNTRIES,
    STATUS_LABELS,
    country_by_code,
    five_digit,
    nature_label,
    service_by_code,
)
from graphics import master_files, relative_graphic, web_files
from project import GITHUB_URL

COUNTS_START = "<!-- registry-counts:start -->"
COUNTS_END = "<!-- registry-counts:end -->"
CODE_RE = re.compile(r"\b\d{2}-\d{3}(?:-\d{3})?\b")
CATEGORY_MENTION = re.compile(r"\b(?:category\s+|moved to )(\d{2})\b", re.IGNORECASE)

REQUEST_LABELS = {"nl": "Netherlands", "at": "Austria", "de": "Germany"}


def title_name(sign: dict) -> str:
    return sign.get("name") or sign.get("definition") or sign["id"]


def heading(sign: dict) -> str:
    return f"{sign['id']} · {title_name(sign).replace('#', '')}"


def paragraph(text: str) -> str:
    return f"<p>{html.escape(text)}</p>"


def md_cell(text: str) -> str:
    cleaned = html.escape(text or "", quote=False).replace("|", "\\|")
    return cleaned.replace("\n", " ")


def shorten(text: str, limit: int = 160) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return f"{cut}…"


def feedback_link(title: str, page_path: str) -> str:
    query = urlencode(
        {
            "template": "page-feedback.yml",
            "title": f"[Page feedback] {title}",
            "page-title": title,
            "page-path": page_path,
        }
    )
    return f"{GITHUB_URL}/issues/new?{query}"


def chips(sign: dict, *, draft: bool = False, home_href: str = "../#draft-watermark") -> str:
    parts: list[str] = []
    kind = sign.get("kind")
    status = sign.get("status", "")
    if kind == "reserved":
        parts.append('<span class="chip chip-reserved">Reserved</span>')
    elif kind == "range":
        parts.append('<span class="chip chip-range">Code range</span>')
    if status == "C" and kind != "reserved":
        parts.append('<span class="chip chip-current">Current</span>')
    elif status == "D":
        parts.append('<span class="chip chip-deprecated">Deprecated</span>')
    if draft:
        parts.append(f'<a class="chip chip-draft" href="{home_href}">Draft</a>')
    return " ".join(parts)


def _linkify_html(text: str, known_ids: set[str], service_codes: set[str]) -> str:
    """Escape workbook text, then link pictogram codes and category mentions."""

    def code_link(match: re.Match[str]) -> str:
        code = match.group(0)
        if code in known_ids:
            return f'<a href="../signs/{code}/">{code}</a>'
        return code

    def category_link(match: re.Match[str]) -> str:
        code = match.group(1)
        prefix = match.group(0)[: -len(code)]
        if code in service_codes:
            return f'{html.escape(prefix)}<a href="../categories/{code}/">{code}</a>'
        return match.group(0)

    linked = CODE_RE.sub(code_link, html.escape(text))
    return CATEGORY_MENTION.sub(category_link, linked)


def draft_banner(mode: str, baseline_version: str | None) -> str:
    if mode == "diff" and baseline_version:
        message = (
            f"This entry has changed since full release {html.escape(baseline_version)}. "
            '<a href="../#draft-watermark">What the DRAFT watermark means</a>'
        )
    else:
        message = (
            "This entry is not yet part of a full release. "
            '<a href="../#draft-watermark">What the DRAFT watermark means</a>'
        )
    return (
        '<div class="draft4-watermark" aria-hidden="true"></div>\n\n'
        f'<p class="draft-note">{message}</p>\n'
    )


def _country_cards(
    sign: dict,
    files_by_country: dict[str, list[Path]],
    root: Path,
) -> str:
    countries = country_by_code()
    notes = sign.get("country_notes") or {}
    codes = [code for code, _name, _column in COUNTRIES]
    blocks: list[str] = []
    for code in codes:
        paths = files_by_country.get(code, [])
        note = notes.get(code, "")
        if not paths and not note:
            continue
        name = countries[code][1]
        images = []
        for path in web_files(paths):
            src = relative_graphic(root, path)
            alt = html.escape(f"{name} graphic for {title_name(sign)} ({sign['id']})", quote=True)
            images.append(f'<img src="{html.escape(src, quote=True)}" alt="{alt}" loading="lazy">')
        downloads = []
        for path in master_files(paths):
            src = relative_graphic(root, path)
            label = path.suffix.lower().lstrip(".").upper()
            downloads.append(
                f'<a href="{html.escape(src, quote=True)}">{label}</a>'
            )
        caption = f"{html.escape(name)} ({code.upper()})"
        if downloads:
            caption += " · " + " ".join(downloads)
        note_html = f"<p>{html.escape(note)}</p>" if note else ""
        image_html = "\n".join(images)
        blocks.append(
            "<figure class=\"sign-card\">\n"
            f"{image_html}\n{note_html}\n"
            f"<figcaption>{caption}</figcaption>\n"
            "</figure>"
        )
    if not blocks:
        if sign.get("kind") != "sign":
            return "<p>Reserved codes and code ranges do not have country graphics.</p>"
        return (
            "<p>No country graphic has been filed for this code. "
            "Add <code>graphics/&lt;country&gt;/"
            f"{html.escape(sign['id'])}.png</code> "
            "(the German stop sign is <code>graphics/de/12-112.png</code>).</p>"
        )
    return '<div class="sign-grid">\n' + "\n".join(blocks) + "\n</div>"


def render_sign(
    sign: dict,
    *,
    draft: bool,
    draft_mode: str,
    baseline_version: str | None,
    files_by_country: dict[str, list[Path]],
    root: Path,
    known_ids: set[str],
) -> str:
    services = service_by_code()
    service = services[sign["service_category"]]
    lines: list[str] = []
    if draft:
        lines.append(draft_banner(draft_mode, baseline_version))
    lines.append(f"# {heading(sign)}\n")
    code5 = five_digit(sign["service_category"], sign.get("pictogram_category", ""))
    kicker = (
        f'<p class="sign-kicker"><a href="../categories/{service["code"]}/">'
        f"{html.escape(service['name'])}</a>"
        f" · pictogram code {html.escape(sign['id'])}"
    )
    if code5:
        kicker += f" · five-digit code {code5}"
    kicker += "</p>"
    lines.append(kicker)
    chip_html = chips(sign, draft=draft)
    if chip_html:
        lines.append(f'<p class="sign-chips">{chip_html}</p>')
    definition = sign.get("definition", "")
    if definition and definition != title_name(sign):
        lines.append(paragraph(definition))
    elif definition and not sign.get("name"):
        pass

    rows: list[tuple[str, str]] = [
        (
            "Service category",
            f'<a href="../categories/{service["code"]}/">{html.escape(service["name"])}</a>'
            f" ({service['code']})",
        ),
        ("Pictogram category", html.escape(sign.get("pictogram_category", ""))),
    ]
    nature = nature_label(sign["service_category"], sign.get("pictogram_category", ""))
    if nature:
        rows.append(("Group", html.escape(nature)))
    status = sign.get("status", "")
    if status:
        label = STATUS_LABELS.get(status, status)
        rows.append(("Status", f"{html.escape(label)} ({html.escape(status)})"))
    if sign.get("registered"):
        rows.append(("Registered", html.escape(sign["registered"])))
    if sign.get("retired"):
        rows.append(("Retired", html.escape(sign["retired"])))
    if sign.get("vienna"):
        rows.append(("UN / Vienna Convention", html.escape(sign["vienna"])))
    if sign.get("related_attributes"):
        rows.append(("Related attributes", html.escape(sign["related_attributes"])))
    table = ["| | |", "| --- | --- |"]
    for label, value in rows:
        table.append(f"| {label} | {value} |")
    lines.append("\n".join(table))

    if sign.get("notes"):
        lines.append("\n## Notes\n")
        lines.append(
            f"<p>{_linkify_html(sign['notes'], known_ids, set(services))}</p>"
        )

    lines.append("\n## Country graphics\n")
    lines.append(_country_cards(sign, files_by_country, root))

    workbook: list[str] = []
    written = sign.get("service_category_as_written")
    if written:
        workbook.append(
            "<p>The workbook cell records service category "
            f"{html.escape(written)}. This row is on the "
            f"{html.escape(service['name'].lower())} sheet, so the register "
            f"files it as {html.escape(sign['id'])}.</p>"
        )
    if sign.get("comments"):
        workbook.append(f"<p>{_linkify_html(sign['comments'], known_ids, set(services))}</p>")
    for code, text in (sign.get("requests") or {}).items():
        label = REQUEST_LABELS.get(code, code.upper())
        if text.strip().upper() == "X":
            workbook.append(f"<p>Request recorded for {html.escape(label)}.</p>")
        else:
            workbook.append(f"<p>{html.escape(label)}: {html.escape(text)}</p>")
    if workbook:
        lines.append("\n## Workbook notes\n")
        lines.extend(workbook)

    page_path = f"signs/{sign['id']}.md"
    lines.append(
        f"\n[Comment on this page]({feedback_link(heading(sign), page_path)})\n"
    )
    return "\n".join(lines).rstrip() + "\n"


def render_category(
    service: dict,
    signs: list[dict],
    draft_ids: set[str],
    draft_mode: str,
) -> str:
    lines = [f"# {service['code']} · {service['name']}\n", f"{service['summary']}\n"]
    if draft_mode == "unreleased":
        lines.append(
            '<p class="draft-note">Sign pages in this category carry the '
            '<a href="../#draft-watermark">DRAFT watermark</a> '
            "until a full release is approved.</p>\n"
        )
    elif any(sign["id"] in draft_ids for sign in signs):
        lines.append(
            '<p class="draft-note">Entries marked Draft have changed since the last '
            '<a href="../#draft-watermark">full release</a>.</p>\n'
        )
    lines.append(
        f'<p><a href="../find/?category={service["code"]}">Filter this category</a></p>\n'
    )
    deprecated = [sign for sign in signs if sign.get("status") == "D"]
    lines.append('<div class="browse">')
    if deprecated:
        lines.append(
            '<label class="dep-switch">'
            '<input type="checkbox" checked>'
            '<span class="dep-switch-track" aria-hidden="true"></span>'
            "<span>Hide deprecated</span>"
            "</label>"
        )
    lines.append("<table class=\"sign-table\">")
    lines.append("<thead><tr><th>Code</th><th>Name</th><th>Status</th><th>Definition</th></tr></thead>")
    lines.append("<tbody>")
    for sign in signs:
        classes = ' class="is-deprecated"' if sign.get("status") == "D" else ""
        code = f'<a href="../signs/{sign["id"]}/">{html.escape(sign["id"])}</a>'
        name = html.escape(title_name(sign))
        status = chips(sign, draft=sign["id"] in draft_ids)
        definition = html.escape(shorten(sign.get("definition", "")))
        lines.append(
            f"<tr{classes}><td>{code}</td><td>{name}</td><td>{status}</td><td>{definition}</td></tr>"
        )
    lines.append("</tbody></table>")
    lines.append("</div>\n")
    lines.append(f"\n[Find a sign](../find.md) · [Home](../index.md)\n")
    return "\n".join(lines).rstrip() + "\n"


def render_counts(signs: list[dict]) -> str:
    services = service_by_code()
    current = sum(1 for sign in signs if sign.get("kind") == "sign" and sign.get("status") == "C")
    deprecated = sum(1 for sign in signs if sign.get("status") == "D")
    reserved = sum(1 for sign in signs if sign.get("kind") == "reserved")
    ranges = sum(1 for sign in signs if sign.get("kind") == "range")
    cards = []
    for code, service in services.items():
        group = [sign for sign in signs if sign["service_category"] == code]
        group_current = sum(1 for sign in group if sign.get("kind") == "sign" and sign.get("status") == "C")
        group_deprecated = sum(1 for sign in group if sign.get("status") == "D")
        group_reserved = sum(1 for sign in group if sign.get("kind") == "reserved")
        group_ranges = sum(1 for sign in group if sign.get("kind") == "range")
        parts: list[str] = []
        if group_current or not (group_deprecated or group_reserved or group_ranges):
            parts.append(f"{group_current} current")
        if group_deprecated:
            parts.append(f"{group_deprecated} deprecated")
        if group_reserved:
            parts.append(f"{group_reserved} reserved")
        if group_ranges:
            parts.append("1 code range" if group_ranges == 1 else f"{group_ranges} code ranges")
        detail = " · ".join(parts)
        cards.append(
            f'<a class="cat-card" href="categories/{code}/">'
            f'<span class="cat-code">{code}</span>'
            f'<span class="cat-name">{html.escape(service["name"])}</span>'
            f'<span class="cat-count">{detail}</span>'
            "</a>"
        )
    summary = (
        f"<p>{len(signs)} pictogram codes are in this edition of the workbook: "
        f"{current} current, {deprecated} deprecated, {reserved} reserved"
        + (f", and {ranges} code range." if ranges == 1 else f", and {ranges} code ranges.")
        + "</p>"
    )
    grid = '<div class="cat-grid">\n' + "\n".join(cards) + "\n</div>"
    return summary + "\n" + grid


def update_counts(index_text: str, signs: list[dict]) -> str:
    if COUNTS_START not in index_text or COUNTS_END not in index_text:
        raise ValueError("docs/index.md is missing the registry-counts markers")
    pre, rest = index_text.split(COUNTS_START, 1)
    _, post = rest.split(COUNTS_END, 1)
    block = render_counts(signs)
    return f"{pre}{COUNTS_START}\n{block}\n{COUNTS_END}{post}"


def search_document(document: dict, draft_ids: set[str], graphics_by_sign: dict[str, dict[str, list[Path]]]) -> dict:
    services = service_by_code()
    signs = []
    for sign in document["signs"]:
        files = graphics_by_sign.get(sign["id"], {})
        signs.append(
            {
                "id": sign["id"],
                "name": title_name(sign),
                "definition": sign.get("definition", ""),
                "service": sign["service_category"],
                "serviceName": services[sign["service_category"]]["name"],
                "status": sign.get("status", ""),
                "kind": sign.get("kind", "sign"),
                "vienna": sign.get("vienna", ""),
                "notes": sign.get("notes", ""),
                "draft": sign["id"] in draft_ids,
                "countries": sorted(files),
                "code5": five_digit(sign["service_category"], sign.get("pictogram_category", "")),
            }
        )
    return {
        "categories": [
            {"code": item["code"], "name": item["name"]}
            for item in document["service_categories"]
        ],
        "countries": document["countries"],
        "signs": signs,
    }


def render_find(payload: dict, draft_mode: str) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    note = ""
    if draft_mode == "unreleased":
        note = (
            '<p class="draft-note">Sign pages carry the '
            '<a href="../#draft-watermark">DRAFT watermark</a> '
            "until a full release is approved. Results marked Draft point at those pages.</p>\n"
        )
    return f"""# Find a sign

Search by pictogram code or by words from the name, definition, or Vienna Convention reference.

{note}
<div class="find-bar">
<label>Search
<input id="find-q" name="q" type="search" placeholder="12-112 or stop" autocomplete="off" autofocus>
</label>
<label>Category
<select id="find-category"><option value="">All categories</option></select>
</label>
<label>Status
<select id="find-status">
<option value="">Any status</option>
<option value="C" selected>Current</option>
<option value="D">Deprecated</option>
<option value="reserved">Reserved</option>
<option value="range">Code range</option>
</select>
</label>
<label>Country graphic
<select id="find-country"><option value="">Any country</option></select>
</label>
</div>

<p id="find-count" aria-live="polite"></p>
<div id="find-results"></div>
<noscript><p>Filtering uses JavaScript. The service categories in the menu list every code.</p></noscript>

<script id="sign-index" type="application/json">{data}</script>
"""
