"""Tests for refill date math (pure functions in refills.py)."""

from datetime import date

import pytest

from med_list_mcp.refills import (
    SOON_DAYS,
    normalize_date,
    refill_due_on,
    runs_out_on,
    status_for,
)


class TestRunsOut:
    def test_runs_out_adds_days_supplied(self):
        assert runs_out_on(date(2026, 11, 1), 30) == date(2026, 12, 1)

    def test_runs_out_day_granularity(self):
        # 1-day supply picked up today runs out tomorrow.
        assert runs_out_on(date(2026, 3, 15), 1) == date(2026, 3, 16)

    def test_zero_days_supplied_means_today(self):
        assert runs_out_on(date(2026, 5, 10), 0) == date(2026, 5, 10)


class TestRefillDue:
    def test_due_is_runs_out_minus_lead(self):
        assert refill_due_on(date(2026, 11, 1), 30, 5) == date(2026, 11, 26)

    def test_no_lead_means_due_when_supply_ends(self):
        assert refill_due_on(date(2026, 1, 1), 90, 0) == date(2026, 4, 1)

    def test_long_supply_weekly_lead(self):
        # 7-day supply, 2-day lead.
        assert refill_due_on(date(2026, 2, 2), 7, 2) == date(2026, 2, 7)

    def test_lead_larger_than_supply_clamps_not_before_pickup(self):
        # Lead days can never push the estimate before the pickup day.
        assert refill_due_on(date(2026, 6, 10), 3, 30) == date(2026, 6, 10)


class TestStatusFor:
    def test_ok_when_far_future(self):
        status = status_for("A", date(2026, 11, 1), 30, 5, date(2026, 11, 5))
        assert status.state == "ok"
        assert status.days_to_refill == 21
        assert status.refill_due == date(2026, 11, 26)

    def test_soon_boundary_inclusive(self):
        # 35-day supply picked up 28 days ago -> due tomorrow? Let's be exact:
        # last=2026-11-01, supply=35 => runs out 12-06; lead 5 => due 12-01.
        status = status_for("A", date(2026, 11, 1), 35, 5, date(2026, 11, 24))
        assert status.days_to_refill == SOON_DAYS
        assert status.state == "soon"

    def test_due_today_is_soon(self):
        status = status_for("A", date(2026, 11, 1), 30, 5, date(2026, 11, 26))
        assert status.days_to_refill == 0
        assert status.state == "soon"

    def test_overdue_one_day_past(self):
        status = status_for("A", date(2026, 11, 1), 30, 5, date(2026, 11, 27))
        assert status.days_to_refill == -1
        assert status.state == "overdue"

    def test_missing_data_returns_none(self):
        assert status_for("A", None, 30, 5, date(2026, 11, 5)) is None
        assert status_for("A", date(2026, 11, 1), None, 5, date(2026, 11, 5)) is None
        assert status_for("A", date(2026, 11, 1), 0, 5, date(2026, 11, 5)) is None
        assert status_for("A", date(2026, 11, 1), -4, 5, date(2026, 11, 5)) is None

    def test_carries_name_and_pharmacy_through(self):
        status = status_for("Lisinopril", date(2026, 11, 1), 30, 5, date(2026, 11, 5), pharmacy="CVS")
        assert status.name == "Lisinopril"
        assert status.pharmacy == "CVS"


class TestNormalizeDate:
    def test_iso_string(self):
        assert normalize_date("2026-11-01") == date(2026, 11, 1)

    def test_bad_string_is_none(self):
        assert normalize_date("november") is None
        assert normalize_date("") is None
        assert normalize_date(None) is None

    def test_truncates_time_suffix(self):
        assert normalize_date("2026-11-01T09:00") == date(2026, 11, 1)

    def test_leap_day(self):
        assert normalize_date("2028-02-29") == date(2028, 2, 29)

    def test_non_leap_rejected(self):
        with pytest.raises(ValueError):
            date.fromisoformat("2026-02-29")
