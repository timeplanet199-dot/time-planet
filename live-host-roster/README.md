# Live Host Roster Plan

- `Live_Host_Roster_Plan.xlsx` – roster + emergency cover plan (open sheet "1 Summary" first).
- `build_roster.py` – generates the workbook. Edit the CONFIG part (off days, sessions, account
  priority, Wani's monthly slot) and run `python3 build_roster.py` to regenerate. The script
  checks there are no double bookings and no live session longer than 3h.

Sheets: HQ host schedule (Week A/B rotation), HQ hourly coverage grid, Sunway roster,
HQ + Sunway emergency cover tables (who replaces whom, per day), emergency SOP / promo-day
plan, live-hours check, and items to confirm.
