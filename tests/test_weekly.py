"""Tests for the printable weekly sheet."""

from datetime import date

from med_list_mcp.refills import status_for
from med_list_mcp.store import Medication
from med_list_mcp.weekly import (
    BUCKETS,
    render_weekly_sheet,
    timing_bucket_for,
    write_weekly_sheet,
)

TODAY = date(2026, 11, 5)  # a Thursday


def make_statuses(meds, lead=5, today=TODAY):
    out = []
    for m in meds:
        s = status_for(m.name, m.last_refill, m.days_supplied, lead, today, m.pharmacy)
        if s:
            out.append(s)
    return out


MEDS = [
    Medication("Lisinopril", "10 mg", "morning", 30, date(2026, 11, 1), "CVS"),
    Medication("Omeprazole", "", "as needed noon", None, None, ""),
    Medication("Melatonin", "5 mg", "bedtime", 60, date(2026, 10, 1), "Rite Aid"),
    Medication("Unknown Timing", "", "twice a day", None, None, ""),
]


class TestTimingBuckets:
    def test_morning(self):
        assert timing_bucket_for("morning before breakfast") == "Morning"

    def test_noon_maps_to_midday(self):
        assert timing_bucket_for("at noon") == "Midday"

    def test_evening_and_bedtime(self):
        assert timing_bucket_for("evening") == "Evening"
        assert timing_bucket_for("at bedtime") == "Bedtime"

    def test_as_needed_wins(self):
        assert timing_bucket_for("as needed at noon") == "As needed"

    def test_unknown_wording(self):
        assert timing_bucket_for("every other hour") == "As instructed"
        assert timing_bucket_for("") == "As instructed"

    def test_multiple_buckets(self):
        assert timing_bucket_for("morning and bedtime with dinner") == "Morning + Evening + Bedtime"

    def test_all_known_buckets_are_in_order_list(self):
        assert set(BUCKETS) >= {"Morning", "Midday", "Evening", "Bedtime", "As needed", "As instructed"}


class TestSheetLayout:
    def test_grid_has_seven_day_header(self):
        sheet = render_weekly_sheet(MEDS, make_statuses(MEDS), TODAY)
        assert "| Time of day | Mon | Tue | Wed | Thu | Fri | Sat | Sun |" in sheet

    def test_meds_appear_in_full_week_row(self):
        sheet = render_weekly_sheet(MEDS, make_statuses(MEDS), TODAY)
        assert "Lisinopril 10 mg" in sheet
        assert "Melatonin 5 mg" in sheet
        # a daily morning med should appear in all 7 columns
        row = [ln for ln in sheet.splitlines() if ln.startswith("| Morning | ")][0]
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert cells[0] == "Morning"
        day_cells = cells[1:]
        assert len(day_cells) == 7
        assert set(day_cells) == {day_cells[0]}
        assert "Lisinopril 10 mg" in day_cells[0]

    def test_refill_table_lists_estimates(self):
        sheet = render_weekly_sheet(MEDS, make_statuses(MEDS), TODAY)
        assert "| Med | Pickup due (est.) | Supply out (est.) | Pharmacy | Status |" in sheet
        assert "2026-11-26" in sheet  # Lisinopril: 11-01 + 30 - 5
        assert "CVS" in sheet

    def test_empty_refill_table_hint(self):
        sheet = render_weekly_sheet([MEDS[1]], [], TODAY)
        assert "Add days-supplied and last-refill dates" in sheet

    def test_disclaimer_lines_present(self):
        sheet = render_weekly_sheet(MEDS, [], TODAY)
        assert "not medical advice" in sheet
        assert "Questions flagged for the doctor:" in sheet

    def test_week_starts_on_monday(self):
        # TODAY is a Thursday -> week of Monday 2026-11-02
        sheet = render_weekly_sheet(MEDS, [], TODAY)
        assert "week of 2026-11-02" in sheet


def test_write_weekly_sheet_writes_file(tmp_path):
    path = write_weekly_sheet(MEDS, make_statuses(MEDS), TODAY, tmp_path, "CVS")
    assert path.name == "weekly-sheet-2026-11-05.md"
    text = path.read_text(encoding="utf-8")
    assert "Lisinopril" in text
    assert text == render_weekly_sheet(MEDS, make_statuses(MEDS), TODAY, pharmacy_default="CVS")
