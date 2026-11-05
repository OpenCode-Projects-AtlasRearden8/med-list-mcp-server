# med-list-mcp-server

A local MCP server that keeps your personal medication list organized as
plain, readable Markdown — receipt style, not a medical journal. Edit the
files by hand or with your editor; every tool keeps them in your repo.

Built by **Asdale Dynamics, LLC** as a beginner-friendly, local-first tool.

## What it does

- **Medication list** — store what is on the bottle: name, strength,
  personal timing preferences ("morning and bedtime"), and pharmacy.
- **Refill estimates** — from *days supplied* and the *last refill date*,
  it adds the two numbers (minus a configurable "lead days" window) to
  estimate when to contact your pharmacy. That is the entire calculation.
- **Pickup reminders** — a window list of estimated pickups coming up.
- **Printable weekly sheet** — a Markdown grid (Mon–Sun by time-of-day
  wording) plus a refill-prep table, written to `output/` to print and
  bring to doctor visits.

## What it is NOT (by design)

- **Never medical advice.** No clinical guidance of any kind.
- **No drug-interaction checks.** It does not have any drug knowledge.
- **No dose calculations.** It only copies your text and adds two dates.
- **No network.** No API keys, no phones home. Data stays in this folder.

Always have prescribers, pharmacists, and clinical resources handle
anything medical. This tool is paperwork help, nothing more.

## Files

| File | Purpose |
| --- | --- |
| `data/medications.md` | Your readable medication table (committed). |
| `data/settings.md` | Refill lead days and default pharmacy. |
| `output/weekly-sheet-*.md` | Printable sheets, regenerated per run (not committed). |

Print with any Markdown viewer (`pandoc data.md -o sheet.pdf`, or open in
your IDE and use its preview/print button).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run (MCP stdio server)

Wire into any MCP host (Claude Code, Codex, Zed, …) with stdio:

```json
{
  "mcpServers": {
    "med-list": {
      "command": ".venv/bin/python",
      "args": ["-m", "med_list_mcp.server"],
      "cwd": "/full/path/to/med-list-mcp-server"
    }
  }
}
```

Or run manually: `.venv/bin/python -m med_list_mcp.server`.

## Tools

- `get_med_list` — show the list.
- `add_medication`, `update_medication`, `remove_medication`.
- `refill_schedule(lead_days=None)` — all estimated pickup dates.
- `pickup_reminders(days_ahead=7)` — window list.
- `mark_refilled(name, date_str=None)` — record a pickup (today default).
- `set_refill_lead_days(days)` — how early to nudge yourself.
- `weekly_sheet()` — write + return the printable sheet.
- `sort_daily_timing(name, timing)` — preview where a phrase lands on the sheet.

## Example

```console
$ # in your MCP client
> add_medication(name="Lisinopril", strength="10 mg", timing="morning",
                 days_supplied=30, last_refill="2026-11-01")
Added Lisinopril to data/medications.md.

> refill_schedule()
Refill ESTIMATES ...: Lisinopril, planned pickup day 2026-11-26, 21 day(s) out ...

> weekly_sheet()
Saved: output/weekly-sheet-2026-11-05.md
```

## Tests

```bash
.venv/bin/pytest -v
```

Covers the refill math (add-days-supplied, lead-window clamping, boundary
states), Markdown round-trips, and the weekly sheet layout.

## Credits

Part of the beginner-friendly tool collection by **Asdale Dynamics, LLC**
(Dylan Asdale) — see dylanasdale.github.io and *The Massive AI Manual*.

Licensed MIT — see [LICENSE](LICENSE).
