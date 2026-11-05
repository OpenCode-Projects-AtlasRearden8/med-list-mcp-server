"""Readable-Markdown persistence for the medication list and settings.

Everything lives in the repository as plain Markdown you can open, print,
or edit by hand. Tools in this project only reformat/copy your own info.

Education and paper-management only: no medical advice, no interaction
checks, no dose calculations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

MEDS_TABLE_HEADER = (
    "Name",
    "Strength",
    "Timing",
    "Days supplied",
    "Last refill",
    "Pharmacy",
    "Notes",
)
TABLE_HEADER_LINE = "| " + " | ".join(MEDS_TABLE_HEADER) + " |"
TABLE_DIVIDER = "| " + " | ".join("---" for _ in MEDS_TABLE_HEADER) + " |"

MEDS_FILE = "medications.md"
SETTINGS_FILE = "settings.md"
DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "data"

DATE_HINT = "YYYY-MM-DD"


def data_root() -> Path:
    """Return the data directory, overridable with MED_LIST_DATA_DIR."""
    import os

    override = os.environ.get("MED_LIST_DATA_DIR")
    return Path(override) if override else DEFAULT_ROOT


@dataclass
class Medication:
    name: str
    strength: str = ""
    timing: str = ""
    days_supplied: Optional[int] = None
    last_refill: Optional[date] = None
    pharmacy: str = ""
    notes: str = ""


def _fmt(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "/").replace("\n", " ").strip()


def _clean_cell(cell: str) -> str:
    cell = cell.strip()
    cell = re.sub(r"\s+", " ", cell)
    return "" if cell.lower() == "(empty)" else cell


def _fmt_date(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "")


def _parse_int(raw: str) -> Optional[int]:
    raw = raw.strip()
    if not raw:
        return None
    match = re.match(r"(\d+)", raw)
    return int(match.group(1)) if match else None


def _parse_date(raw: str) -> Optional[date]:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def parse_meds_table(markdown: str) -> list[Medication]:
    """Parse the medications Markdown table into Medication records."""
    meds: list[Medication] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells or _clean_cell(cells[0]) in ("Name", "", "---"):
            continue
        if all(_clean_cell(c) in ("---", "") for c in cells):
            continue
        cells += [""] * (len(MEDS_TABLE_HEADER) - len(cells))
        name = _clean_cell(cells[0])
        if not name:
            continue  # keep working even if the table gets a stray row
        note_text = _clean_cell(" ".join(cells[6:]))
        meds.append(
            Medication(
                name=name,
                strength=_clean_cell(cells[1]),
                timing=_clean_cell(cells[2]),
                days_supplied=_parse_int(cells[3]),
                last_refill=_parse_date(cells[4]),
                pharmacy=_clean_cell(cells[5]),
                notes=note_text,
            )
        )
    return meds


def medication_row(med: Medication) -> str:
    return (
        f"| {_fmt(med.name)} | {_fmt(med.strength)} | {_fmt(med.timing)} | "
        f"{_fmt(med.days_supplied)} | {_fmt_date(med.last_refill)} | "
        f"{_fmt(med.pharmacy)} | {_fmt(med.notes)} |"
    )


def render_meds_table(meds: list[Medication]) -> str:
    lines = [f"# Medication list ({DATE_HINT} dates)", "", TABLE_HEADER_LINE, TABLE_DIVIDER]
    lines += [medication_row(m) for m in meds]
    lines += [
        "",
        "Each row is one med: strength as written on the bottle, personal timing",
        "preferences, days each fill lasts, the last refill date, and the pharmacy.",
        "This list is a paper-management copy of your own labels. It is not medical",
        "advice and it never predicts interactions or adjusts doses.",
        "",
        "Refill dates are simple estimates only: last refill date plus days",
        f"supplied (see settings.md, including the call-ahead window). Enter dates as {DATE_HINT}.",
    ]
    return "\n".join(lines) + "\n"


def load_meds() -> list[Medication]:
    path = data_root() / MEDS_FILE
    if not path.exists():
        return []
    return parse_meds_table(path.read_text(encoding="utf-8"))


def save_meds(meds: list[Medication]) -> None:
    root = data_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root / MEDS_FILE
    if path.exists():
        old = path.read_text(encoding="utf-8")
    else:
        old = ""
    path.write_text(render_meds_table(meds), encoding="utf-8")


SETTING_KEYS = ("refill_lead_days", "default_pharmacy")


@dataclass
class Settings:
    refill_lead_days: int = 5
    default_pharmacy: str = ""


def parse_settings(markdown: str) -> Settings:
    settings = Settings()
    for line in markdown.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lstrip("-*# ").lower()
        value = value.strip()
        if key == "refill lead days":
            n = _parse_int(value)
            if n is not None:
                settings.refill_lead_days = n
        elif key == "default pharmacy":
            settings.default_pharmacy = value
    return settings


def settings_path() -> Path:
    return data_root() / SETTINGS_FILE


def load_settings() -> Settings:
    path = settings_path()
    if path.exists():
        return parse_settings(path.read_text(encoding="utf-8"))
    return Settings()


def save_settings(settings: Settings) -> None:
    root = data_root()
    root.mkdir(parents=True, exist_ok=True)
    content = (
        "# Settings\n\n"
        f"- Refill lead days: {settings.refill_lead_days}\n"
        f"- Default pharmacy: {settings.default_pharmacy}\n\n"
        '"Refill lead days" is how many days before a bottle runs out you want '
        "a refill reminder to appear. Example: 5 means get the call in 5 days "
        "early. All refill dates here are estimates from your own entries.\n"
    )
    (root / SETTINGS_FILE).write_text(content, encoding="utf-8")
