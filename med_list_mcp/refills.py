"""Simple date arithmetic for refill reminders.

These are estimates from numbers the user enters themselves (days supplied,
last pickup date). Nothing here touches doses, schedules, or drug safety --
it is a paper-management aid only, never medical advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

SOON_DAYS = 7


def normalize_date(value: object) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except (ValueError, TypeError):
        return None


def runs_out_on(last_refill: date, days_supplied: int) -> date:
    """The day the current supply is expected to run dry (estimate)."""
    return last_refill + timedelta(days=max(0, days_supplied))


def refill_due_on(last_refill: date, days_supplied: int, lead_days: int = 0) -> date:
    """Estimated call-the-pharmacy day: runs-out day minus lead days.

    Clamped so the estimate never falls before the pickup day itself,
    even with a very long lead window.
    """
    return max(last_refill, runs_out_on(last_refill, days_supplied) - timedelta(days=max(0, lead_days)))


def days_until(due: date, today: date) -> int:
    return (due - today).days


@dataclass
class RefillStatus:
    name: str
    days_supplied: Optional[int]
    last_refill: Optional[date]
    pharmacy: str
    runs_out: Optional[date] = None
    refill_due: Optional[date] = None
    days_to_refill: Optional[int] = None
    state: str = "unknown"

    def summary(self) -> str:
        bits = [f"{self.name}"]
        if self.runs_out:
            bits.append(f"supply estimate runs out {self.runs_out.isoformat()}")
        if self.refill_due:
            bits.append(f"planned pickup day {self.refill_due.isoformat()}")
        if self.days_to_refill is not None:
            if self.state == "overdue":
                bits.append(f"{self.days_to_refill * -1} day(s) past the planned pickup day")
            else:
                bits.append(f"{self.days_to_refill} day(s) out")
        if self.pharmacy:
            bits.append(self.pharmacy)
        return ", ".join(bits)


def status_for(
    name: str,
    last_refill: Optional[date],
    days_supplied: Optional[int],
    lead_days: int,
    today: date,
    pharmacy: str = "",
) -> Optional[RefillStatus]:
    """Status for one med, or None if not enough data has been entered yet.

    States: ok, soon (due within SOON_DAYS), overdue. Pure arithmetic plus
    labels; the user's own entries are the only inputs. Never medical advice.
    """
    if last_refill is None or not days_supplied or days_supplied <= 0:
        return None
    runs_out = runs_out_on(last_refill, days_supplied)
    due = refill_due_on(last_refill, days_supplied, lead_days)
    delta = days_until(due, today)
    if delta < 0:
        state = "overdue"
    elif delta <= SOON_DAYS:
        state = "soon"
    else:
        state = "ok"
    return RefillStatus(
        name=name,
        days_supplied=days_supplied,
        last_refill=last_refill,
        pharmacy=pharmacy,
        runs_out=runs_out,
        refill_due=due,
        days_to_refill=delta,
        state=state,
    )
