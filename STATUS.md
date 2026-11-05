# STATUS.md — med-list-mcp-server

Last updated: 2026-11-05

## What was built

A local MCP server (stdio transport) that organizes a personal medication
list and refill logistics as readable Markdown files inside this repo.

- `med_list_mcp/store.py` — read/write `data/medications.md` and
  `data/settings.md` as plain Markdown tables (parse + render round-trips,
  pipe-escaping so hand edits stay safe).
- `med_list_mcp/refills.py` — refill math: `runs_out_on` (last refill +
  days supplied), `refill_due_on` (runs-out day minus a lead window,
  clamped so it never lands before the pickup day), `status_for` /
  `days_until` with `ok` / `soon` (≤ 7 days) / `overdue` labels.
- `med_list_mcp/weekly.py` — printable weekly sheet: Mon–Sun grid grouped
  by the user's own timing wording (Morning / Midday / Evening / Bedtime /
  As needed / As instructed), plus a refill-prep table and blank question
  lines for the doctor.
- `med_list_mcp/server.py` — 10 MCP tools (`get_med_list`,
  `add_medication`, `update_medication`, `remove_medication`,
  `set_refill_lead_days`, `refill_schedule`, `pickup_reminders`,
  `mark_refilled`, `weekly_sheet`, `sort_daily_timing`), 2 prompts
  (`doctor_visit_prep`, `pharmacy_call_script`), and a resource exposing
  `medlist://medications`.
- Seed data ships with one clearly-labeled example row you edit or delete.

## Scope guardrails (by design)

Education and paper-management only:
- No medical advice, no drug-interaction checks, no dose calculations.
  Refill dates are pure "add two numbers the user typed" estimates.
- No network calls, no API keys, no telemetry. All data stays in `data/`.

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# run the server (an MCP client would start it this way):
.venv/bin/python -m med_list_mcp.server

# tests
.venv/bin/pytest -v
```

MCP host config (stdio): see README.md for a ready-to-paste JSON block.

## Verification results

- `pytest -v`: **55 passed** (refill math boundaries, lead-window clamping,
  Markdown round-trips, tool behavior against a temp data dir, weekly-sheet
  layout, seed-file parse).
- Live stdio smoke test (hand-rolled JSON-RPC client against
  `python -m med_list_mcp.server`): initialize handshake OK, `tools/list`
  returned all 10 tools, `get_med_list` / `refill_schedule` /
  `weekly_sheet` / `pickup_reminders` all returned correct output, and
  `output/weekly-sheet-2026-11-05.md` was written and formatted correctly.
- Verified the seed `data/medications.md` parses to the example row and the
  2026-11-01 + 30 days − 5 lead-days estimate produces 2026-11-26.

## Known gaps

- Markdown tables only (no JSON/CSV export); highly edited hand files could
  break parsing, though the renderer escapes `|` on write.
- `weekly_sheet` timing buckets use simple keyword matching; unrecognized
  wording prints under "As instructed" (by design, conservative).
- No deduplication of near-identical med names; "CVS" vs "CVS Pharmacy"
  are treated as different strings.
- No per-day-of-week dosing (e.g. "Mon only") — the grid repeats daily
  meds across all seven days.
- Output sheets are not committed (regenerable from `data/` by design).
- Not yet published to any package index; install is venv + pip from this
  folder only.
