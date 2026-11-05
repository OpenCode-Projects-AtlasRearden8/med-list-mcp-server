"""Printable weekly medication sheet (Markdown) for doctor visits.

This is a formatting/copy tool for your own notes -- it never decides
anything clinical. Print it (or copy it into a doc) and bring it along.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from .refills import RefillStatus
from .store import Medication

BUCKETS = ("Morning", "Midday", "Evening", "Bedtime", "As needed", "As instructed")

MORNING = ("morning", "am", "wake", "breakfast", "before breakfast", "with breakfast")
MIDDAY = ("noon", "midday", "afternoon", "lunch", "with lunch")
EVENING = ("evening", "dinner", "supper", "pm", "late day")
BEDTIME = ("bedtime", "night", "sleep", "before bed")
AS_NEEDED = ("as needed", "prn", "when needed", "only if")

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def timing_bucket_for(timing: str) -> str:
    """Sort a personal timing note into one printable bucket.

    This is pattern matching on the user's own wording to lay out a paper
    sheet -- it is not a dosing instruction and not medical advice.
    """
    text = " ".join((timing or "").lower().split())
    if not text:
        return "As instructed"
    if "as needed" in text or "prn" in text:
        return "As needed"
    bucket = []
    if any(word in text for word in MORNING):
        bucket.append("Morning")
    if any(word in text for word in MIDDAY):
        bucket.append("Midday")
    if any(word in text for word in EVENING):
        bucket.append("Evening")
    if any(word in text for word in BEDTIME):
        bucket.append("Bedtime")
    if bucket:
        return " + ".join(bucket)
    return "As instructed"


def bucket_order_key(bucket: str) -> int:
    try:
        return BUCKETS.index(bucket)
    except ValueError:
        return len(BUCKETS)


def _bucket_row(bucket: str, meds: list[tuple[Medication, str]]) -> list[str]:
    if not meds:
        return ["—"] * 7
    cells = "; ".join(
        f"{m.name}{' ' + m.strength if m.strength else ''}" + (f" ({m.timing})" if bucket == "As needed" else "")
        for m, _ in meds
    )
    return [cells] * 7


def render_weekly_sheet(
    meds: list[Medication],
    statuses: list[RefillStatus],
    today: date,
    pharmacy_default: str = "",
) -> str:
    """A tidy one-page sheet: med grid plus a refill-ready list."""
    start = today - timedelta(days=today.weekday())
    week = [start + timedelta(days=i) for i in range(7)]

    grouped: dict[str, list[tuple[Medication, str]]] = {}
    for med in sorted(meds, key=lambda m: m.name.lower()):
        grouped.setdefault(timing_bucket_for(med.timing), []).append((med, med.timing))
    buckets = sorted(
        grouped,
        key=lambda b: (
            min((bucket_order_key(part) for part in b.split(" + ")), default=99),
            b,
        ),
    )

    lines: list[str] = []
    lines.append(f"# Medications — week of {week[0].isoformat()}")
    lines.append("")
    lines.append("Paper copy for my next doctor visit. Personal list only —")
    lines.append("not medical advice, not a prescribing record.")
    lines.append("")
    header = f"| Time of day | " + " | ".join(DAY_NAMES) + " |"
    divider = "| ---" * 8 + " |"
    lines.append(header)
    lines.append(divider)
    for bucket in buckets:
        row = [bucket] + _bucket_row(bucket, grouped[bucket])
        lines.append("| " + " | ".join(row) + " |")
    if not buckets:
        lines.append("| — | — | — | — | — | — | — | — |")
    lines.append("")
    lines.append("Fill in with your prescriber as directed:")
    lines.append("")
    lines.append("| Med | Prescriber | Why I take it |")
    lines.append("| --- | --- | --- |")
    for med in sorted(meds, key=lambda m: m.name.lower()):
        lines.append(f"| {med.name}{' ' + med.strength if med.strength else ''} |  |  |")
    lines.append("")
    lines.append("## Refill prep (estimates from my own entries)")
    lines.append("")
    if statuses:
        lines.append("| Med | Pickup due (est.) | Supply out (est.) | Pharmacy | Status |")
        lines.append("| --- | --- | --- | --- | --- |")
        for s in sorted(statuses, key=lambda s: s.runs_out or date.max):
            lines.append(
                f"| {s.name} | {s.refill_due.isoformat() if s.refill_due else '—'} "
                f"| {s.runs_out.isoformat() if s.runs_out else '—'} "
                f"| {s.pharmacy or pharmacy_default or '—'} | {s.state} |"
            )
    else:
        lines.append("_Add days-supplied and last-refill dates to medications.md to fill this table._")
    lines.append("")
    lines.append("Questions flagged for the doctor:")
    lines.append("")
    lines.append("1. ")
    lines.append("2. ")
    lines.append("3. ")
    lines.append("")
    lines.append(f"Printed {today.isoformat()} · med-list-mcp-server (paper management only, never medical advice)")
    return "\n".join(lines) + "\n"


def write_weekly_sheet(
    meds: list[Medication],
    statuses: list[RefillStatus],
    today: date,
    output_dir: Path,
    pharmacy_default: str = "",
) -> Path:
    path = Path(output_dir) / f"weekly-sheet-{today.isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_weekly_sheet(meds, statuses, today, pharmacy_default=pharmacy_default),
        encoding="utf-8",
    )
    return path
