"""Read the ISO 14823-1 Annex I workbook into register records.

The workbook is one sheet per service category. Country columns hold embedded
drawings rather than text; those drawings are published separately as
``graphics/<country>/<service>-<pictogram>.png``.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# ISO 3166-1 alpha-2, except the annex column that groups Russia and Belarus.
# That column has no combined ISO code; graphics for it use ``ru``.
COUNTRIES: list[tuple[str, str, str]] = [
    ("de", "Germany", "Germany"),
    ("fr", "France", "France"),
    ("gb", "United Kingdom", "UK"),
    ("it", "Italy", "Italy"),
    ("es", "Spain", "Spain"),
    ("nl", "Netherlands", "Netherlands"),
    ("be", "Belgium", "Belgium"),
    ("ch", "Switzerland", "Switzerland"),
    ("at", "Austria", "Austria"),
    ("ie", "Ireland", "Ireland"),
    ("pl", "Poland", "Poland"),
    ("se", "Sweden", "Sweden"),
    ("fi", "Finland", "Finland"),
    ("no", "Norway", "Norway"),
    ("gr", "Greece", "Greece"),
    ("cz", "Czechia", "Czech Rep"),
    ("sk", "Slovakia", "Slovakia"),
    ("ru", "Russia & Belarus", "Russia & Belarus"),
    ("us", "United States", "U.S."),
    ("kr", "Korea, Republic of", "South Korea"),
    ("cn", "China", "China"),
    ("jp", "Japan", "Japan"),
]

REQUESTS = {
    "request by nl": ("nl", "Netherlands"),
    "request by at": ("at", "Austria"),
    "request by de": ("de", "Germany"),
}

# Sheet title in the workbook, service category code, public name, short description.
SERVICE_CATEGORIES: list[dict[str, str]] = [
    {
        "sheet": "Warning (11)",
        "code": "11",
        "name": "Warning",
        "summary": (
            "Advance warning of a hazard, an adverse road condition, or another "
            "situation a road user needs to notice."
        ),
    },
    {
        "sheet": "Regulatory(12)",
        "code": "12",
        "name": "Regulatory",
        "summary": (
            "Orders and prohibitions, including priority, restrictions, and "
            "mandatory directions."
        ),
    },
    {
        "sheet": "informative(13)",
        "code": "13",
        "name": "Informative",
        "summary": (
            "Direction, instruction, notification, lane guidance, and place "
            "identification."
        ),
    },
    {
        "sheet": "Public Facilities (21)",
        "code": "21",
        "name": "Public facilities",
        "summary": "Public facilities and services, such as hospitals, fuel, and toilets.",
    },
    {
        "sheet": "Ambient Conditions (31)",
        "code": "31",
        "name": "Ambient conditions",
        "summary": "Weather and other ambient conditions that can affect the trip.",
    },
    {
        "sheet": "Road Conditions (32)",
        "code": "32",
        "name": "Road conditions",
        "summary": "Road conditions that can affect traffic, such as congestion or an incident.",
    },
    {
        "sheet": "Supplementary Panel(41)",
        "code": "41",
        "name": "Supplementary panel",
        "summary": (
            "Panels attached to a main sign to limit when it applies or to add "
            "a short qualification."
        ),
    },
]

# First digit of a three-digit pictogram category, from the service-category groups
# in ISO 14823-1 Table 1. Used only as a reading aid on the sign page.
NATURE: dict[tuple[str, str], str] = {
    ("11", "1"): "Danger warning",
    ("11", "2"): "Danger warning",
    ("11", "3"): "Danger warning",
    ("11", "4"): "Danger warning",
    ("11", "5"): "Danger warning",
    ("11", "6"): "Danger warning",
    ("11", "7"): "Danger warning",
    ("11", "8"): "Danger warning",
    ("11", "9"): "Danger warning",
    ("12", "1"): "Priority",
    ("12", "2"): "Priority",
    ("12", "3"): "Priority",
    ("12", "4"): "Prohibition or restriction",
    ("12", "5"): "Prohibition or restriction",
    ("12", "6"): "Prohibition or restriction",
    ("12", "7"): "Mandatory",
    ("12", "8"): "Mandatory",
    ("12", "9"): "Mandatory",
    ("13", "1"): "Advance direction",
    ("13", "2"): "Advance direction",
    ("13", "3"): "Advance direction",
    ("13", "4"): "Instruction",
    ("13", "5"): "Notification",
    ("13", "6"): "Lane guidance",
    ("13", "7"): "Alert",
    ("13", "8"): "Road or place identification",
    ("13", "9"): "Road or place identification",
    ("21", "1"): "Public facilities and services",
    ("21", "2"): "Public facilities and services",
    ("31", "1"): "Ambient conditions",
    ("31", "2"): "Ambient conditions",
    ("32", "1"): "Road conditions",
    ("41", "1"): "Supplementary panel",
}

HEADER_ROLES = {
    "category code name": "name",
    "definition": "definition",
    "service category": "service",
    "pictogram category": "pictogram",
    "status": "status",
    "registered": "registered",
    "retired": "retired",
    "notes": "notes",
    "un/vienna": "vienna",
    "related attributes": "related_attributes",
    "comments from lb": "comments",
}

COUNTRY_BY_HEADER = {
    re.sub(r"[.\s]+", " ", label).strip().lower(): code
    for code, _name, label in COUNTRIES
}
# Headers lose their dots in ``norm_header`` ("u.s." -> "us").
COUNTRY_BY_HEADER["us"] = "us"
COUNTRY_BY_HEADER["uk"] = "gb"

STATUS_LABELS = {
    "C": "Current",
    "D": "Deprecated",
}


def clean(value: str | None) -> str:
    if not value:
        return ""
    text = value.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", " ", text)
    return text.strip()


def norm_header(value: str) -> str:
    text = clean(value).lower().replace(".", "")
    return re.sub(r"\s+", " ", text).strip()


def service_by_code() -> dict[str, dict[str, str]]:
    return {item["code"]: item for item in SERVICE_CATEGORIES}


def country_by_code() -> dict[str, tuple[str, str, str]]:
    return {code: item for item in COUNTRIES for code in (item[0],)}


def five_digit(service: str, pictogram: str) -> str:
    if re.fullmatch(r"\d{2}", service) and re.fullmatch(r"\d{3}", pictogram):
        return f"{service}{pictogram}"
    return ""


def nature_label(service: str, pictogram: str) -> str:
    if re.fullmatch(r"\d{3}", pictogram):
        return NATURE.get((service, pictogram[0]), "")
    return ""


def parse_pictogram(raw: str) -> tuple[str, str]:
    """Return ``(normalized, shape)`` where shape is ``sign``, ``range``, or ``other``."""
    text = clean(raw)
    compact = re.sub(r"\s+", "", text)
    if re.fullmatch(r"\d{3}", compact):
        return compact, "sign"
    match = re.fullmatch(r"(\d{3})[-~](\d{3})", compact)
    if match:
        return f"{match.group(1)}-{match.group(2)}", "range"
    return compact, "other"


def entry_kind(name: str, definition: str, shape: str) -> str:
    blob = f"{name} {definition}".lower()
    if "reserved for future" in blob:
        return "reserved"
    if shape == "range":
        return "range"
    return "sign"


def _col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    number = 0
    for ch in letters:
        number = number * 26 + (ord(ch) - 64)
    return number


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("m:si", NS):
        parts = [node.text or "" for node in item.iter(f"{MAIN}t")]
        values.append("".join(parts))
    return values


def _sheet_targets(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall("m:sheets/m:sheet", NS):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        target = targets[rel_id]
        if not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")
        sheets.append((name, target))
    return sheets


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    kind = cell.attrib.get("t")
    value = cell.find("m:v", NS)
    inline = cell.find("m:is", NS)
    if kind == "s" and value is not None and value.text:
        return shared[int(value.text)]
    if kind == "inlineStr" and inline is not None:
        return "".join(node.text or "" for node in inline.iter(f"{MAIN}t"))
    if value is not None and value.text:
        return value.text
    return ""


def _sheet_rows(archive: zipfile.ZipFile, target: str, shared: list[str]) -> dict[int, dict[int, str]]:
    root = ET.fromstring(archive.read(target))
    rows: dict[int, dict[int, str]] = {}
    for row in root.findall("m:sheetData/m:row", NS):
        number = int(row.attrib["r"])
        cells: dict[int, str] = {}
        for cell in row.findall("m:c", NS):
            text = _cell_value(cell, shared)
            if text:
                cells[_col_index(cell.attrib["r"])] = text
        if cells:
            rows[number] = cells
    return rows


def _roles_for(header: dict[int, str], subheader: dict[int, str]) -> dict[int, tuple[str, str]]:
    roles: dict[int, tuple[str, str]] = {}
    columns = set(header) | set(subheader)
    for column in columns:
        label = norm_header(subheader.get(column, "")) or norm_header(header.get(column, ""))
        if not label or label == "gdd code":
            roles[column] = ("blank", "")
            continue
        if label in HEADER_ROLES:
            roles[column] = (HEADER_ROLES[label], "")
        elif label in COUNTRY_BY_HEADER:
            roles[column] = ("country", COUNTRY_BY_HEADER[label])
        elif label in REQUESTS:
            roles[column] = ("request", REQUESTS[label][0])
        else:
            roles[column] = ("extra", label)
    return roles


def _append_text(current: str, addition: str) -> str:
    addition = clean(addition)
    if not addition:
        return current
    if not current:
        return addition
    return f"{current} {addition}"


def load_workbook(path: Path) -> dict:
    """Parse Annex I into a JSON-ready register document."""
    expected = {item["sheet"]: item for item in SERVICE_CATEGORIES}
    signs: list[dict] = []
    unknown_sheets: list[str] = []
    unknown_headers: set[str] = set()
    mismatches: list[str] = []
    skipped_stubs: list[str] = []
    rows_without_code: list[str] = []

    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        found: set[str] = set()
        for sheet_name, target in _sheet_targets(archive):
            meta = expected.get(sheet_name)
            if meta is None:
                unknown_sheets.append(sheet_name)
                continue
            found.add(sheet_name)
            rows = _sheet_rows(archive, target, shared)
            roles = _roles_for(rows.get(1, {}), rows.get(2, {}))
            for label in {extra for kind, extra in roles.values() if kind == "extra"}:
                unknown_headers.add(f"{sheet_name}: {label}")
            for row_number in sorted(rows):
                if row_number < 3:
                    continue
                record = _record_from_row(
                    meta, roles, rows[row_number], row_number, rows_without_code
                )
                if record is None:
                    continue
                written = record.pop("service_category_as_written", "")
                if written and written != meta["code"]:
                    mismatches.append(
                        f"{record['id']} sheet {meta['code']} cell {written} (row {row_number})"
                    )
                    # A one-digit fragment such as "1" on sheet 11 is a truncated
                    # sheet code. A full two-digit value is kept on the record.
                    if re.fullmatch(r"\d{2}", written):
                        record["service_category_as_written"] = written
                signs.append(record)

    missing = [name for name in expected if name not in found]
    if missing or unknown_sheets:
        raise ValueError(
            "Workbook sheets do not match Annex I. "
            f"Missing: {missing or 'none'}. Unexpected: {unknown_sheets or 'none'}."
        )

    signs, dropped = _drop_duplicate_stubs(signs)
    skipped_stubs.extend(dropped)
    _reject_duplicate_ids(signs)
    signs.sort(key=_sort_key)
    return {
        "standard": "ISO 14823-1:2024",
        "annex": "I",
        "source": path.name,
        "service_categories": SERVICE_CATEGORIES,
        "countries": [
            {"code": code, "name": name, "column": column}
            for code, name, column in COUNTRIES
        ],
        "signs": signs,
        "warnings": {
            "service_category_mismatches": mismatches,
            "skipped_stubs": skipped_stubs,
            "rows_without_code": rows_without_code,
            "unmapped_headers": sorted(unknown_headers),
        },
    }


def _record_from_row(
    meta: dict[str, str],
    roles: dict[int, tuple[str, str]],
    cells: dict[int, str],
    row_number: int,
    rows_without_code: list[str] | None = None,
) -> dict | None:
    fields = {
        "name": "",
        "definition": "",
        "service": "",
        "pictogram": "",
        "status": "",
        "registered": "",
        "retired": "",
        "notes": "",
        "vienna": "",
        "related_attributes": "",
        "comments": "",
    }
    country_notes: dict[str, str] = {}
    requests: dict[str, str] = {}
    extras: list[str] = []
    for column, raw in cells.items():
        kind, argument = roles.get(column, ("blank", ""))
        text = clean(raw)
        if not text:
            continue
        if kind == "blank":
            extras.append(text)
        elif kind == "country":
            country_notes[argument] = _append_text(country_notes.get(argument, ""), text)
        elif kind == "request":
            requests[argument] = _append_text(requests.get(argument, ""), text)
        elif kind == "extra":
            extras.append(f"{argument}: {text}")
        elif kind in fields:
            fields[kind] = _append_text(fields[kind], text)
        else:
            extras.append(text)

    if fields["name"].lower() == "category code name":
        return None
    pictogram, shape = parse_pictogram(fields["pictogram"])
    if not any((fields["name"], fields["definition"], pictogram)):
        return None
    if not pictogram:
        if rows_without_code is not None and (fields["name"] or fields["definition"]):
            rows_without_code.append(
                f"{meta['sheet']} row {row_number} has no pictogram category"
            )
        return None
    stub = not fields["name"] and not fields["definition"]

    service_cell = re.sub(r"\.0$", "", fields["service"])
    kind = entry_kind(fields["name"], fields["definition"], shape)
    if stub and not fields["name"]:
        if shape == "range":
            fields["name"] = f"Pictogram categories {pictogram}"
        else:
            fields["name"] = "Unnamed pictogram code"
    sign_id = f"{meta['code']}-{pictogram}"
    record = {
        "id": sign_id,
        "service_category": meta["code"],
        "pictogram_category": pictogram,
        "kind": kind,
        "name": fields["name"],
        "definition": fields["definition"],
        "status": fields["status"].upper(),
        "registered": re.sub(r"\.0$", "", fields["registered"]),
        "retired": re.sub(r"\.0$", "", fields["retired"]),
        "notes": fields["notes"],
        "vienna": fields["vienna"],
        "related_attributes": fields["related_attributes"],
        "comments": _append_text(fields["comments"], " ".join(extras)),
        "requests": requests,
        "country_notes": country_notes,
        "sheet": meta["sheet"],
        "row": row_number,
        "stub": stub,
    }
    if service_cell and service_cell != meta["code"]:
        record["service_category_as_written"] = service_cell
    return {key: value for key, value in record.items() if value not in ("", {}, [])}


def _drop_duplicate_stubs(signs: list[dict]) -> tuple[list[dict], list[str]]:
    """Drop a nameless duplicate when the same code also has a real entry.

    The workbook repeats 41-191 on a row that carries only the code, the
    status, and the year. The following row is the sign itself.
    """
    full_ids = {sign["id"] for sign in signs if not sign.get("stub")}
    kept: list[dict] = []
    dropped: list[str] = []
    for sign in signs:
        if sign.get("stub") and sign["id"] in full_ids:
            dropped.append(
                f"{sign['id']} row {sign.get('row')} repeats a code that has a name"
            )
            continue
        sign.pop("stub", None)
        kept.append(sign)
    return kept, dropped


def _reject_duplicate_ids(signs: list[dict]) -> None:
    seen: dict[str, dict] = {}
    duplicates: list[str] = []
    for sign in signs:
        previous = seen.get(sign["id"])
        if previous is None:
            seen[sign["id"]] = sign
            continue
        duplicates.append(
            f"{sign['id']} rows {previous.get('row')} and {sign.get('row')} ({sign.get('sheet')})"
        )
    if duplicates:
        raise ValueError("Duplicate pictogram codes:\n" + "\n".join(duplicates))


def _sort_key(sign: dict) -> tuple:
    pictogram = sign.get("pictogram_category", "")
    match = re.match(r"\d+", pictogram)
    start = int(match.group()) if match else 10_000
    return (sign.get("service_category", ""), start, pictogram, sign.get("id", ""))


def content_signature(sign: dict) -> str:
    """Stable text for comparing a register entry across releases.

    Sheet coordinates are omitted so a workbook re-import does not mark every
    page as changed when a row only moves.
    """
    import json

    kept = {
        key: sign.get(key, "")
        for key in (
            "id",
            "service_category",
            "pictogram_category",
            "kind",
            "name",
            "definition",
            "status",
            "registered",
            "retired",
            "notes",
            "vienna",
            "related_attributes",
            "comments",
            "requests",
            "country_notes",
            "service_category_as_written",
        )
        if sign.get(key) not in (None, "", {}, [])
    }
    return json.dumps(kept, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
