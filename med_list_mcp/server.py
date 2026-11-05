"""MCP server: personal medication list, refills, printable weekly sheet.

Runs locally over stdio. Files stay in-repo as readable Markdown
(data/medications.md, data/settings.md), outputs go to output/.

Education and paper-management ONLY:
- No medical advice of any kind.
- Never calculates doses or predicts drug interactions.
- All refill dates are simple estimates from numbers you enter yourself.

Privacy: everything stays in this folder. No network calls, no API keys.
The names/pharmacy strings you store are your own data on your own disk.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import MCPServer

from . import __version__, refills
from .store import (
    Medication,
    Settings,
    data_root,
    load_meds,
    load_settings,
    save_meds,
    save_settings,
    settings_path,
)
from .weekly import render_weekly_sheet, timing_bucket_for, write_weekly_sheet

server = MCPServer(
    name="med-list-mcp-server",
    title="Med List (paper management only)",
    instructions=(
        "Personal medication list and refill paper-management. Store what is "
        "written on your own bottles, estimate pickup dates from days-supplied, "
        "and print a weekly sheet for doctor visits. This server never gives "
        "medical advice, never checks drug interactions, and never calculates "
        "doses. Ask a prescriber or pharmacist for anything clinical."
    ),
    version=__version__,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _today() -> date:
    return date.today()


def _find(meds: list[Medication], name: str) -> Optional[Medication]:
    wanted = name.strip().lower()
    for med in meds:
        if med.name.strip().lower() == wanted:
            return med
    return None


@server.resource(
    "medlist://medications",
    name="Medication list (Markdown)",
    description="Your in-repo medications.md file, exactly as stored.",
)
def medications_file() -> str:
    path = data_root() / "medications.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


@server.tool()
def get_med_list() -> str:
    """Show the full medication list with any refill estimates."""
    meds = load_meds()
    settings = load_settings()
    if not meds:
        return "No medications on file yet. Data file: data/medications.md (add with add_medication)."
    lines = []
    for med in meds:
        desc = f"- {med.name}" + (f" {med.strength}" if med.strength else "")
        if med.timing:
            desc += f" — timing: {med.timing}"
        if med.pharmacy or settings.default_pharmacy:
            desc += f" — pharmacy: {med.pharmacy or settings.default_pharmacy}"
        if med.last_refill and med.days_supplied:
            desc += f" — last refill {med.last_refill.isoformat()}, {med.days_supplied} day supply"
        lines.append(desc)
    return "\n".join(lines)


@server.tool()
def add_medication(
    name: str,
    strength: str = "",
    timing: str = "",
    days_supplied: Optional[int] = None,
    last_refill: Optional[str] = None,
    pharmacy: str = "",
    notes: str = "",
) -> str:
    """Add a medication exactly as your label reads.

    name: as written on the bottle. strength: e.g. "10 mg" (copy only).
    timing: your personal preference text, e.g. "morning and bedtime".
    days_supplied: how long one fill lasts. last_refill: YYYY-MM-DD.
    Copy-only tool: records what you type, computes nothing clinical.
    """
    meds = load_meds()
    if _find(meds, name):
        return f"'{name}' is already on the list. Use update_medication instead."
    parsed_last = refills.normalize_date(last_refill) if last_refill else None
    if last_refill and parsed_last is None:
        return "Could not read last_refill. Use YYYY-MM-DD."
    if days_supplied is not None and days_supplied <= 0:
        return "days_supplied must be a positive number of days, or left out."
    meds.append(
        Medication(
            name=name.strip(),
            strength=strength.strip(),
            timing=timing.strip(),
            days_supplied=days_supplied,
            last_refill=parsed_last,
            pharmacy=pharmacy.strip() or load_settings().default_pharmacy,
            notes=notes.strip(),
        )
    )
    save_meds(meds)
    return f"Added {name.strip()} to data/medications.md."


@server.tool()
def update_medication(
    name: str,
    strength: Optional[str] = None,
    timing: Optional[str] = None,
    days_supplied: Optional[int] = None,
    last_refill: Optional[str] = None,
    pharmacy: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """Update listed fields for a medication already on the list."""
    meds = load_meds()
    med = _find(meds, name)
    if med is None:
        return f"'{name}' is not on the list. Use add_medication first."
    if last_refill is not None:
        parsed = refills.normalize_date(last_refill)
        if parsed is None:
            return "Could not read last_refill. Use YYYY-MM-DD."
        med.last_refill = parsed
    updates = {
        "strength": strength,
        "timing": timing,
        "days_supplied": days_supplied,
        "pharmacy": pharmacy,
        "notes": notes,
    }
    for field, value in updates.items():
        if value is not None:
            setattr(med, field, value)
    save_meds(meds)
    return f"Updated {med.name}."


@server.tool()
def remove_medication(name: str) -> str:
    """Remove a medication from the list (no backup; the file is in git)."""
    meds = load_meds()
    med = _find(meds, name)
    if med is None:
        return f"'{name}' is not on the list."
    meds.remove(med)
    save_meds(meds)
    return f"Removed {med.name}. (data/medications.md history stays in git.)"


@server.tool()
def set_refill_lead_days(days: int) -> str:
    """Set how many days before a bottle runs out you want pickup reminders."""
    if days < 0:
        return "Use 0 or more days."
    settings = load_settings()
    settings.refill_lead_days = days
    save_settings(settings)
    return f"Refill lead days set to {days} in data/settings.md."


@server.tool()
def refill_schedule(lead_days: Optional[int] = None) -> str:
    """Estimate each med's pickup date from its own entries.

    For every med with days_supplied and last_refill on file, this adds the
    two numbers (last refill + days supplied, minus your lead days) to
    produce an ESTIMATE of when to contact the pharmacy. It only adds the
    numbers you entered; it is not medical advice.
    """
    meds = load_meds()
    settings = load_settings()
    lead = settings.refill_lead_days if lead_days is None else lead_days
    today = _today()
    rows = []
    for med in meds:
        status = refills.status_for(med.name, med.last_refill, med.days_supplied, lead, today, med.pharmacy)
        if status is None:
            rows.append(
                f"- {med.name}: waiting on data (days_supplied and last_refill)."
            )
            continue
        state_note = {
            "ok": "not due yet",
            "soon": "coming up — consider contacting the pharmacy",
            "overdue": "planned pickup day passed — check with your pharmacy",
        }[status.state]
        rows.append(f"- {status.summary()} — {state_note}")
    if not rows:
        return "Nothing to estimate yet. data/medications.md is empty."
    return (
        "Refill ESTIMATES (simple date math on your own entries — not medical advice):"
        f" (lead = {lead} days, today = {today.isoformat()})\n" + "\n".join(rows)
    )


@server.tool()
def pickup_reminders(days_ahead: int = 7) -> str:
    """List meds whose estimated pickup day falls within the next N days."""
    meds = load_meds()
    settings = load_settings()
    today = _today()
    reminders = []
    for med in meds:
        status = refills.status_for(
            med.name, med.last_refill, med.days_supplied, settings.refill_lead_days, today, med.pharmacy
        )
        if status is None:
            continue
        if 0 <= status.days_to_refill <= max(0, days_ahead):
            where = f" at {status.pharmacy}" if status.pharmacy else ""
            reminders.append(
                f"{med.name}{where}: planned pickup day "
                f"{status.refill_due.isoformat()} ({status.days_to_refill} day(s) out)"
            )
    if not reminders:
        return f"No est. pickups within {days_ahead} day(s) of {today.isoformat()}."
    return "Pickup reminders upcoming:\n" + "\n".join(reminders)


@server.tool()
def mark_refilled(name: str, date_str: Optional[str] = None) -> str:
    """Record that a fill was picked up today (or on a given YYYY-MM-DD)."""
    meds = load_meds()
    med = _find(meds, name)
    if med is None:
        return f"'{name}' is not on the list."
    when = refills.normalize_date(date_str) if date_str else _today()
    if when is None:
        return "Could not read date_str. Use YYYY-MM-DD or leave it out for today."
    med.last_refill = when
    save_meds(meds)
    return f"{med.name}: last refill set to {when.isoformat()}."


@server.tool()
def weekly_sheet() -> str:
    """Write output/weekly-sheet-YYYY-MM-DD.md and return its Markdown.

    A grid of your meds sorted by the time-of-day wording you typed,
    plus a refill-prep table from your own estimates, plus blank lines
    for questions for the doctor. Print it and bring it along.
    """
    meds = load_meds()
    settings = load_settings()
    today = _today()
    statuses = [
        s
        for s in (
            refills.status_for(m.name, m.last_refill, m.days_supplied, settings.refill_lead_days, today, m.pharmacy)
            for m in meds
        )
        if s
    ]
    path = write_weekly_sheet(meds, statuses, today, OUTPUT_DIR, settings.default_pharmacy)
    content = render_weekly_sheet(meds, statuses, today, pharmacy_default=settings.default_pharmacy)
    return f"Saved: {path}\n\n{content}"


@server.tool()
def sort_daily_timing(name: str, timing: str) -> str:
    """Preview which printable bucket a timing note will land in.

    Bucket options are Morning / Midday / Evening / Bedtime / As needed /
    As instructed. Words like "noon" map to Midday; unrecognized wording
    prints 'As instructed'. Pure keyword matching for sheet layout.
    """
    return f"'{timing}' prints under: {timing_bucket_for(timing)}"


@server.prompt()
def doctor_visit_prep() -> str:
    """Step-by-step prep for bringing the weekly sheet to an appointment."""
    return (
        "For a doctor visit, I can help me stay organized (not advise anyone):\n"
        "1. Call get_med_list and check each row against the bottles.\n"
        "2. Call refill_schedule to update my own pickup estimates.\n"
        "3. Call weekly_sheet and print output/weekly-sheet-TODAY.md.\n"
        "4. Write questions for the doctor in the numbered blanks.\n"
        "5. Bring the printed sheet and my insurance card. Ask the "
        "prescriber or pharmacist about anything clinical — this list is "
        "paper management only."
    )


@server.prompt()
def pharmacy_call_script() -> str:
    """A short checklist for calling the pharmacy about a pickup."""
    return (
        "Help me stay organized for the call (no advice, no numbers computed):\n"
        "1. Have pickup_reminders output handy.\n"
        "2. Note which meds and which pharmacy per row.\n"
        "3. Check refill openings on data/medications.md dates.\n"
        "4. After pickup, call mark_refilled for each med collected."
    )


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
