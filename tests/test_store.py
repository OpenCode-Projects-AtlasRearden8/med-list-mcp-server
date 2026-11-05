"""Tests for Markdown persistence: parse, render, round-trip."""

from datetime import date

from med_list_mcp.store import (
    Medication,
    Settings,
    load_meds,
    load_settings,
    parse_meds_table,
    parse_settings,
    render_meds_table,
    save_meds,
    save_settings,
)


def test_parse_basic_table():
    md = (
        "# Medication list\n\n"
        "| Name | Strength | Timing | Days supplied | Last refill | Pharmacy | Notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| Lisinopril | 10 mg | morning | 30 | 2026-11-01 | CVS | |\n"
        "| Omeprazole | | before breakfast, as needed | | | | |\n"
    )
    meds = parse_meds_table(md)
    assert len(meds) == 2
    a, b = meds
    assert a.name == "Lisinopril"
    assert a.strength == "10 mg"
    assert a.timing == "morning"
    assert a.days_supplied == 30
    assert a.last_refill == date(2026, 11, 1)
    assert a.pharmacy == "CVS"
    assert b.name == "Omeprazole"
    assert b.days_supplied is None
    assert b.last_refill is None


def test_parse_skips_divider_and_non_table_lines():
    md = "Some prose about refill plans.\n| --- | 2026-11-01 |\n| Aspirin | 81 mg |\n"
    meds = parse_meds_table(md)
    names = [m.name for m in meds]
    assert "Aspirin" in names
    assert "---" not in names


def test_render_then_parse_round_trip():
    meds = [
        Medication(
            name="Metformin 500|weird",
            strength="500 mg",
            timing="with dinner",
            days_supplied=60,
            last_refill=date(2026, 10, 15),
            pharmacy="Walgreens",
            notes="bring to appointment",
        ),
        Medication(name="Vitamin D", timing="morning"),
    ]
    rendered = render_meds_table(meds)
    # pipe in a name must be neutralized so the table stays parseable
    reparsed = parse_meds_table(rendered)
    assert reparsed[0].name == "Metformin 500/weird"
    assert reparsed[0].days_supplied == 60
    assert reparsed[0].last_refill == date(2026, 10, 15)
    assert reparsed[1].name == "Vitamin D"


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("MED_LIST_DATA_DIR", str(tmp_path))
    meds = [
        Medication(
            name="Lisinopril",
            strength="10 mg",
            timing="morning",
            days_supplied=30,
            last_refill=date(2026, 11, 1),
            pharmacy="CVS",
        )
    ]
    save_meds(meds)
    loaded = load_meds()
    assert len(loaded) == 1
    assert loaded[0] == meds[0]
    # in-repo, human-readable markdown
    text = (tmp_path / "medications.md").read_text(encoding="utf-8")
    assert text.startswith("# Medication list")
    assert "| Lisinopril | 10 mg | morning | 30 | 2026-11-01 | CVS |" in text


def test_load_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MED_LIST_DATA_DIR", str(tmp_path / "does-not-exist"))
    assert load_meds() == []


def test_settings_parse_and_round_trip(tmp_path, monkeypatch):
    settings = parse_settings("# Settings\n\n- Refill lead days: 21\n- Default pharmacy: My Meds Plus\n")
    assert settings.refill_lead_days == 21
    assert settings.default_pharmacy == "My Meds Plus"
    monkeypatch.setenv("MED_LIST_DATA_DIR", str(tmp_path))
    save_settings(settings)
    assert load_settings() == settings


def test_settings_defaults_when_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("MED_LIST_DATA_DIR", str(tmp_path))
    loaded = load_settings()
    assert loaded.refill_lead_days == 5
    assert loaded.default_pharmacy == ""
