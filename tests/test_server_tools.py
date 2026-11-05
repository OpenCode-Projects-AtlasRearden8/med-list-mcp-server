"""Tool-level tests: add/update/list/refills/weekly-sheet against a temp dir."""

from datetime import date

import pytest

import med_list_mcp.server as srv


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MED_LIST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(srv, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(srv, "_today", lambda: date(2026, 11, 5))
    return tmp_path / "data"


def add(name="Lisinopril", **kwargs):
    returns = srv.add_medication(name=name, **kwargs)
    return returns


def test_add_and_list(data_dir):
    out = srv.add_medication(
        name="Lisinopril",
        strength="10 mg",
        timing="morning",
        days_supplied=30,
        last_refill="2026-11-01",
        pharmacy="CVS",
    )
    assert "Added" in out
    listing = srv.get_med_list()
    assert "Lisinopril 10 mg" in listing
    assert "morning" in listing
    assert " CVS" in listing

    text = (data_dir / "medications.md").read_text(encoding="utf-8")
    assert "| Lisinopril | 10 mg | morning | 30 | 2026-11-01 | CVS |" in text


def test_add_needs_valid_date(data_dir):
    out = srv.add_medication(name="X", last_refill="yesterday")
    assert "YYYY-MM-DD" in out


def test_add_rejects_bad_days_supplied(data_dir):
    out = srv.add_medication(name="X", days_supplied=0)
    assert "positive" in out


def test_duplicate_add_blocked(data_dir):
    srv.add_medication(name="Dup Med")
    out = srv.add_medication(name="Dup Med")
    assert "already" in out


def test_update_and_remove(data_dir):
    srv.add_medication(name="A", days_supplied=30, last_refill="2026-11-01")
    out = srv.update_medication(name="A", days_supplied=45, pharmacy="Kroger")
    assert "Updated" in out
    text = (data_dir / "medications.md").read_text(encoding="utf-8")
    assert "45" in text and "Kroger" in text
    assert "Removed" in srv.remove_medication(name="A")
    assert (data_dir / "medications.md").read_text(encoding="utf-8").count("| A |") == 0


def test_update_missing_med(data_dir):
    out = srv.update_medication(name="Nope", timing="morning")
    assert "not on the list" in out


def test_refill_schedule_math_end_to_end(data_dir):
    srv.add_medication(
        name="Lisinopril",
        days_supplied=30,
        last_refill="2026-11-01",
    )
    out = srv.refill_schedule()
    assert "ESTIMATES" in out
    assert "2026-11-26" in out  # 11-01 + 30 - lead 5
    # 2026-11-05 -> due 2026-11-26 is 21 days out, outside the 7-day 'soon'
    assert "not due yet" in out


def test_refill_schedule_overdue_and_soon(data_dir):
    today = date(2026, 11, 5)
    srv.add_medication(name="Soon Med", days_supplied=10, last_refill="2026-10-28")
    srv.add_medication(name="Old Med", days_supplied=10, last_refill="2026-10-10")
    out = srv.refill_schedule()
    # Soon: 10-28 + 10 = 11-07, minus lead 5 => 11-02 => 3 days out -> soon
    assert "Soon Med, supply estimate runs out 2026-11-07" in out
    assert "Old Med" in out


def test_refill_schedule_reports_missing_data(data_dir):
    srv.add_medication(name="No Dates Yet", timing="morning")
    out = srv.refill_schedule()
    assert "No Dates Yet" in out
    assert "waiting on data" in out
    assert "2026-11-26" not in out


def test_pickup_reminders_window(data_dir):
    srv.add_medication(name="Due Soon", days_supplied=10, last_refill="2026-11-05")
    assert "Due Soon" in srv.pickup_reminders(7)
    assert "No est. pickups" in srv.pickup_reminders(0)


def test_mark_refilled_and_checks(data_dir):
    srv.add_medication(name="M", days_supplied=30, last_refill="2026-10-01")
    out = srv.mark_refilled(name="M", date_str="2026-11-04")
    assert "2026-11-04" in out
    meds = srv.load_meds()
    assert meds[0].last_refill == date(2026, 11, 4)
    assert "not on the list" in srv.mark_refilled(name="Ghost")
    assert "YYYY-MM-DD" in srv.mark_refilled(name="M", date_str="marbles")


def test_weekly_sheet_tool_writes_output(data_dir):
    srv.add_medication(name="Lisinopril", strength="10 mg", timing="morning", days_supplied=30, last_refill="2026-11-01")
    out = srv.weekly_sheet()
    assert "Saved:" in out
    assert "Lisinopril 10 mg" in out
    import re

    written = re.search(r"weekly-sheet-\d{4}-\d{2}-\d{2}\.md", out).group(0)
    saved = re.search(r"Saved: (\S+)", out).group(1)
    with open(saved, encoding="utf-8") as fh:
        text = fh.read()
    assert written in saved
    assert "| Lisinopril 10 mg" in text
    assert "not medical advice" in text


def test_set_refill_lead_days(data_dir):
    assert "set to 10" in srv.set_refill_lead_days(10)
    settings = srv.load_settings()
    assert settings.refill_lead_days == 10
    assert "Use 0 or more" in srv.set_refill_lead_days(-1)


def test_sort_daily_timing_preview(data_dir):
    assert "Midday" in srv.sort_daily_timing(name="X", timing="at noon")
    assert "As instructed" in srv.sort_daily_timing(name="X", timing="twice a day")


def test_resource_reads_file(data_dir):
    srv.add_medication(name="Z Med")
    content = srv.medications_file()
    assert "Z Med" in content


def test_seed_file_parses():
    from med_list_mcp.store import DEFAULT_ROOT, parse_meds_table

    seed = (DEFAULT_ROOT / "medications.md").read_text(encoding="utf-8")
    meds = parse_meds_table(seed)
    assert len(meds) == 1
    assert meds[0].name == "Example Med"
