"""Builds the live-host roster + emergency cover plan (Live_Host_Roster_Plan.xlsx).
Edit the CONFIG section and re-run:  python3 build_roster.py
Hours are 24h integers; 24 = 12am, 25 = 1am, 26 = 2am (end of day)."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ACC = {"TP": "Time Planet TikTok", "BP": "Bilano Polo TikTok", "SH": "Time Planet Shopee",
       "TZ": "Timezone Gallery TikTok", "SW": "Time Planet Sunway TikTok"}
PRIORITY = {"TP": 1, "BP": 2, "SH": 3, "TZ": 4}          # 1 = most important (HQ)
HQ_FT = ["AYUNI", "PUTERI", "FARISAH", "NANI", "ARIESYA", "EISYA", "ELYANA", "YASMIN"]
OFF = {"AYUNI": "Wed", "PUTERI": "Mon", "FARISAH": "Fri", "NANI": "Sat", "ARIESYA": "Tue",
       "EISYA": "Fri", "ELYANA": "Thu", "YASMIN": "Sun",  # Yasmin proposed: Wed -> Sun
       "HUSNA": "Sun", "KARMEN": "Tue", "WANI": None,
       "PIKAH": "Mon", "AINA": "Tue", "SHIFA": "Thu", "ANGGUN": "Wed"}
ROLE = {"AYUNI": "TikTok Main (rotates M/D weekly)", "PUTERI": "TikTok Main (rotates M/D weekly)",
        "FARISAH": "TikTok Night", "HUSNA": "TikTok Late Night (part-time)",
        "NANI": "Bilano Polo Night", "ARIESYA": "Bilano Polo Afternoon/Night",
        "EISYA": "Shopee Day", "ELYANA": "Shopee Night", "YASMIN": "HQ RELIEF host (covers off days)",
        "KARMEN": "Timezone Gallery Day (freelance)", "WANI": "Timezone Gallery (part-time, changes monthly)",
        "PIKAH": "Sunway", "SHIFA": "Sunway", "AINA": "Sunway", "ANGGUN": "Sunway Standby"}

M = [("TP", 7, 10), ("TP", 13, 15)]      # Morning shift 7am-3pm
D = [("TP", 10, 13), ("TP", 15, 18)]     # Day shift 10am-6pm


def hq_day(week, day):
    """Planned HQ roster for one day (off days already covered)."""
    m_host, d_host = ("AYUNI", "PUTERI") if week == "A" else ("PUTERI", "AYUNI")
    r = {m_host: list(M), d_host: list(D),
         "FARISAH": [("TP", 18, 21), ("TP", 24, 26)],
         "NANI": [("BP", 18, 20), ("BP", 23, 26)],
         "ARIESYA": [("BP", 15, 18), ("BP", 20, 23)],
         "EISYA": [("SH", 11, 14), ("SH", 14, 17)],
         "ELYANA": [("SH", 17, 20), ("SH", 21, 24)],
         "YASMIN": [("TZ", 17, 20), ("TZ", 21, 24)],
         "KARMEN": [("TZ", 11, 13), ("TZ", 13, 15)],
         "WANI": [("TZ", 15, 17)]}
    r["HUSNA"] = [("TP", 21, 26)] if day in ("Fri", "Sat") else [("TP", 21, 24)]
    if day == "Tue":
        r["WANI"] = [("TZ", 14, 17), ("TZ", 18, 21)]
    if day == "Wed":
        r["WANI"] = [("TZ", 15, 17), ("TZ", 18, 21)]
    # ---- planned off-day cover (Yasmin = relief) ----
    if day == "Mon":
        r["YASMIN"] = r["PUTERI"]
    if day == "Tue":
        r["YASMIN"] = r["ARIESYA"]
    if day == "Wed":
        r["YASMIN"] = r["AYUNI"]
    if day == "Thu":
        r["YASMIN"] = r["ELYANA"]
    if day == "Fri":
        r["YASMIN"] = [("SH", 14, 17), ("TP", 18, 21)]   # Eisya + Farisah off; Husna does 9pm-2am
    if day == "Sat":
        r["YASMIN"] = [("BP", 18, 20), ("TZ", 21, 24)]
        r["FARISAH"] = [("TP", 18, 21), ("BP", 23, 26)]  # Husna does 9pm-2am, Farisah covers Nani late
    if day == "Sun":
        r["ELYANA"] = [("SH", 17, 20), ("TP", 21, 24)]   # Husna off Sunday
    for h, o in OFF.items():
        if o == day:
            r.pop(h, None)
    return r


# ---------------- Sunway (in-store only, mall 10am-10pm) ----------------
SW_L = {"L1": (11, 13), "L2": (13, 15), "L3": (16, 18), "L4": (18, 20), "L5": (20, 22)}
SW_HOSTS = ["PIKAH", "SHIFA", "AINA", "ANGGUN"]


def sunway_assign(present):
    """present: list of Sunway hosts at work. Returns host -> sessions."""
    n = len(present)
    if n >= 3:
        r, free = {}, [h for h in ["AINA", "ANGGUN"] if h in present]
        for owner, pair in (("PIKAH", ("L1", "L3")), ("SHIFA", ("L2", "L4"))):
            who = owner if owner in present else free.pop(0)
            r[who] = [("SW",) + SW_L[x] for x in pair]
        r[free.pop(0)] = [("SW",) + SW_L["L5"]]
        return r
    order = [h for h in SW_HOSTS if h in present]
    if n == 2:   # compression: 4 x 3h lives = full 10am-10pm
        return {order[0]: [("SW", 10, 13), ("SW", 16, 19)], order[1]: [("SW", 13, 16), ("SW", 19, 22)]}
    if n == 1:
        return {order[0]: [("SW", 13, 16), ("SW", 19, 22)]}
    return {}


def sunway_day(day, absent=None):
    present = [h for h in SW_HOSTS if OFF[h] != day and h != absent]
    return sunway_assign(present)


# ---------------- helpers ----------------
def t(h):
    h = h % 24
    return "12am" if h == 0 else "12pm" if h == 12 else f"{h}am" if h < 12 else f"{h-12}pm"


def rng(s, e):
    return f"{t(s)}-{t(e)}"


def live_at(r, host, hour):
    for a, s, e in r.get(host, []):
        if s <= hour < e:
            return a
    return None


def span(r, host):
    ss = r.get(host, [])
    return (min(s for _, s, _ in ss), max(e for _, _, e in ss)) if ss else None


def live_hours(r, host):
    return sum(e - s for _, s, e in r.get(host, []))


def validate(r, label):
    occ = {}
    for h, ss in r.items():
        assert len(ss) <= 2 or h == "HUSNA", (label, h)
        for a, s, e in ss:
            assert e - s <= 3 or h == "HUSNA", (label, h, a, s, e)
            for x in range(s, e):
                assert (a, x) not in occ, f"{label}: {a} {t(x)} double {occ.get((a, x))} & {h}"
                occ[(a, x)] = h
    return occ


def short(a):
    return {"TP": "TP TikTok", "BP": "Bilano", "SH": "Shopee", "TZ": "Timezone"}[a]


def max_run(hours):
    best = run = 0
    for x in range(0, 30):
        run = run + 1 if x in hours else 0
        best = max(best, run)
    return best


def emergency(week, day, absent):
    """Cover plan for an unplanned absence at HQ. Prefers ONE person per lost session.
    Tier 0 = host live on a lower-priority account switches over (that account pauses)
    Tier 1 = host on shift with a spare live hour (no OT)   Tier 2 = OT (extends shift)
    Constraints: max 3h continuous live, max 6 live h (9 with OT)."""
    base = hq_day(week, day)
    if absent not in base:
        return ["(off day)"]
    r = {h: list(v) for h, v in base.items() if h != absent}
    extra = {h: set() for h in HQ_FT}

    def tier(h, a, hr):
        if h not in r or hr in extra[h]:
            return None
        cur = live_at(r, h, hr)
        if cur:
            return (0, cur) if PRIORITY[cur] > PRIORITY[a] else None
        s0, e0 = span(r, h)
        if s0 <= hr < e0:
            return (1, None)
        if (s0 - 3 <= hr < s0 or e0 <= hr < e0 + 3) and hr >= 10:   # no call-in OT before 10am
            return (2, None)
        return None

    def ok(h, add, tiers):
        new = {x for _, s, e in r[h] for x in range(s, e)} | extra[h]
        added = {x for x, tr in zip(add, tiers) if tr[0] > 0}
        if not added:
            return True
        tot = live_hours(r, h) + len(extra[h]) + len(added)
        lim = 6 if all(tr[0] <= 1 for tr in tiers) else 9
        return max_run(new | added) <= 3 and tot <= lim

    def allowed(a, tiers, hrs):
        worst = max(tr[0] for tr in tiers)
        if a == "TZ":
            return worst == 1                       # lowest account: only spare hours
        if a == "SH":
            return worst <= 1 or all(h >= 20 for h in hrs)   # Shopee OT only for night peak
        return True

    rows = []
    for a, s, e in base[absent]:
        hrs = list(range(s, e))
        best = None
        for h in HQ_FT:
            tiers = [tier(h, a, x) for x in hrs]
            if None in tiers or not allowed(a, tiers, hrs) or not ok(h, hrs, tiers):
                continue
            key = (max(t_[0] for t_ in tiers), -max(PRIORITY[t_[1]] if t_[1] else 0 for t_ in tiers))
            if best is None or key < best[0]:
                best = (key, h, tiers)
        if best:
            _, h, tiers = best
            pieces = [(hrs, h, tiers)]
        else:   # split hour by hour
            pieces = []
            for x in hrs:
                pick = None
                for h in HQ_FT:
                    tr = tier(h, a, x)
                    if tr and allowed(a, [tr], [x]) and ok(h, [x], [tr]):
                        k = (tr[0], -(PRIORITY[tr[1]] if tr[1] else 0))
                        if pick is None or k < pick[0]:
                            pick = (k, h, tr)
                pieces.append(([x], pick[1] if pick else None, [pick[2]] if pick else None))
                if pick:
                    extra[pick[1]].add(x)
        # apply + describe (merge consecutive same-cover hours)
        merged = []
        for ph, h, tiers in pieces:
            if h:
                extra[h].update(ph)
            if merged and merged[-1][1] == h:
                merged[-1][0].extend(ph); merged[-1][2].extend(tiers or [])
            else:
                merged.append([list(ph), h, list(tiers or [])])
        for ph, h, tiers in merged:
            if not h:
                peak = any(20 <= x < 24 or 12 <= x < 14 for x in ph)
                if all(x < 10 for x in ph):
                    note = "PAUSE (low traffic morning)"
                elif a in ("TZ", "SH"):
                    note = "PAUSE (lower-priority account)"
                elif peak:
                    note = "PAUSE - PEAK: call Husna/Wani or approve OT"
                else:
                    note = "PAUSE 1h - nobody free within the 3h rule"
                rows.append([a, ph[0], ph[-1] + 1, note])
                continue
            sw = sorted({tr[1] for tr in tiers if tr[0] == 0}, key=lambda z: PRIORITY[z])
            ot = sum(1 for tr in tiers if tr[0] == 2)
            note = []
            if sw:
                note.append("switches from " + "/".join(short(z) for z in sw) + " (that slot pauses)")
            if any(tr[0] == 1 for tr in tiers):
                note.append("spare hour, no OT")
            if ot:
                note.append(f"OT +{ot}h")
            rows.append([a, ph[0], ph[-1] + 1, f"{h} - " + ", ".join(note)])
    out = []
    for row in rows:
        if out and out[-1][0] == row[0] and out[-1][2] == row[1] and out[-1][3] == row[3]:
            out[-1][2] = row[2]
        else:
            out.append(row)
    return [f"{short(a)} {rng(s_, e_)}: {n}" for a, s_, e_, n in out]


# ---------------- Excel ----------------
wb = Workbook()
HDR = PatternFill("solid", fgColor="1F3864"); HF = Font(bold=True, color="FFFFFF")
B = Font(bold=True); WRAP = Alignment(wrap_text=True, vertical="top")
CEN = Alignment(horizontal="center", vertical="center", wrap_text=True)
thin = Side(style="thin", color="BFBFBF"); BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
COL = {"AYUNI": "F8CBAD", "PUTERI": "FFE699", "FARISAH": "C6E0B4", "HUSNA": "BDD7EE", "NANI": "D9D2E9",
       "ARIESYA": "F4B183", "EISYA": "A9D08E", "ELYANA": "9BC2E6", "YASMIN": "FF99CC", "KARMEN": "E2EFDA",
       "WANI": "DDEBF7", "PIKAH": "F8CBAD", "SHIFA": "C6E0B4", "AINA": "BDD7EE", "ANGGUN": "FF99CC"}
EMPTY = PatternFill("solid", fgColor="FF7C80")


def header(ws, row, vals, widths=None):
    for i, v in enumerate(vals, 1):
        c = ws.cell(row, i, v); c.fill = HDR; c.font = HF; c.alignment = CEN; c.border = BOX
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w


def write_rows(ws, start, rows):
    for ri, row in enumerate(rows, start):
        for ci, v in enumerate(row, 1):
            c = ws.cell(ri, ci, v); c.alignment = WRAP; c.border = BOX


# --- Sheet: Summary
ws = wb.active; ws.title = "1 Summary"
ws.column_dimensions["A"].width = 28; ws.column_dimensions["B"].width = 110
lines = [
    ("LIVE HOST ROSTER PLAN", "Prepared 31 Oct 2026 - for November 2026 onwards (HQ 7am-2am, Sunway 10am-10pm)"),
    ("", ""),
    ("Is 7am-2am possible?", "YES for Time Planet TikTok (19h/day, every day) and Bilano Polo (3pm-2am). NOT for all 6 accounts: "
     "6 x 19h = 114 live-hours/day but 15 hosts give ~60/day. Secondary accounts run their best slots only."),
    ("Main account 1", "Time Planet TikTok: 7am-2am, 7 days, no gaps (was: gaps 10-11am, 5-6pm, 12-2am Sun-Thu, and 6h holes on Ayuni/Puteri off days)."),
    ("Main account 2", "Time Planet Sunway TikTok: 5 lives x 2h inside 11am-10pm (in-store). Anggun is the in-store standby."),
    ("Shift rule used", "Max 3h per live session, max 2 sessions/day for full-timers, OT only for emergencies and big sales days. "
     "Each HQ shift span is 8h (incl. break), so 6 days x ~7h stays under the 45h/week limit."),
    ("HQ shifts", "M = 7am-3pm (live 7-10am, 1-3pm) | D = 10am-6pm (live 10am-1pm, 3-6pm) | N = 6pm-2am (live 6-9pm, 12-2am). "
     "Ayuni & Puteri swap M/D every week (Week A: Ayuni M, Puteri D; Week B: opposite)."),
    ("Key change 1", "Ariesya -> Bilano Polo (3-6pm, 8-11pm) so Bilano runs 3pm-2am with Nani."),
    ("Key change 2", "Farisah -> Time Planet TikTok night shift (6-9pm, 12-2am). Husna stays 9pm-12am (Fri/Sat 9pm-2am)."),
    ("Key change 3", "Yasmin -> full-time HQ RELIEF host. She works whoever is on off day (Mon Puteri, Tue Ariesya, Wed Ayuni, "
     "Thu Elyana, Fri Farisah+Eisya, Sat Nani). On free time she lives on Timezone Gallery."),
    ("Key change 4 (needs OK)", "Move Yasmin's off day Wed -> Sun. Today Wed has 2 HQ hosts off (Ayuni + Yasmin) and Sun has none, "
     "so the relief host can't cover Wednesday. Sunday Husna gap (9pm-12am) is covered by Elyana."),
    ("Key change 5 (needs OK)", "Karmen: 11am-1pm + 1-3pm (instead of 3-5pm) so it doesn't clash with Wani's November 3-5pm slot on the same account."),
    ("Emergency principle", "The main account never goes dark at peak. A missing TP TikTok host is replaced by the host live on the LOWEST-priority "
     "account at the same time (that account pauses), then by a host with a spare hour, then by OT. Priority: "
     "TP TikTok > Bilano Polo > TP Shopee > Timezone Gallery (confirm this order)."),
    ("Sheets", "2-3 HQ host schedule (Week A/B) | 4-5 HQ hourly coverage grid | 6 Sunway | 7-8 HQ emergency cover (who replaces whom, by day) | "
     "9 Sunway emergency | 10 Emergency SOP & promo days | 11 Live-hours check | 12 Items to confirm"),
]
for i, (a, b) in enumerate(lines, 1):
    ws.cell(i, 1, a).font = B; ws.cell(i, 2, b).alignment = WRAP
ws["A1"].font = Font(bold=True, size=14)

# --- Host schedule sheets
for week in ("A", "B"):
    ws = wb.create_sheet(f"{2 if week=='A' else 3} HQ Hosts Week {week}")
    ws.cell(1, 1, f"HQ HOST SCHEDULE - WEEK {week}  ({'Ayuni = Morning, Puteri = Day' if week=='A' else 'Puteri = Morning, Ayuni = Day'}). Alternate Week A / Week B every week.").font = B
    header(ws, 2, ["Host", "Role"] + DAYS, [12, 30] + [26] * 7)
    hosts = HQ_FT[:3] + ["HUSNA"] + HQ_FT[3:] + ["KARMEN", "WANI"]
    for ri, h in enumerate(hosts, 3):
        ws.cell(ri, 1, h).font = B; ws.cell(ri, 2, ROLE[h]).alignment = WRAP
        for ci, d in enumerate(DAYS, 3):
            r = hq_day(week, d)
            txt = "OFF" if h not in r else "\n".join(f"{short(a)} {rng(s,e)}" for a, s, e in r[h])
            c = ws.cell(ri, ci, txt); c.alignment = WRAP; c.border = BOX
            c.fill = PatternFill("solid", fgColor="D9D9D9" if txt == "OFF" else COL[h])
        ws.row_dimensions[ri].height = 32
    ws.freeze_panes = "C3"

# --- Hourly grid sheets
HOURS = list(range(7, 26))
for week in ("A", "B"):
    ws = wb.create_sheet(f"{4 if week=='A' else 5} HQ Grid Week {week}")
    ws.cell(1, 1, f"HOURLY COVERAGE - WEEK {week}. Red = nobody live (planned gap on secondary accounts).").font = B
    header(ws, 2, ["Day", "Account"] + [rng(h, h + 1) for h in HOURS], [6, 22] + [9] * len(HOURS))
    row = 3
    for d in DAYS:
        r = hq_day(week, d)
        occ = validate(r, f"{week}-{d}")
        for a in ("TP", "BP", "SH", "TZ"):
            ws.cell(row, 1, d).font = B; ws.cell(row, 2, ACC[a])
            for ci, hr in enumerate(HOURS, 3):
                h = occ.get((a, hr))
                c = ws.cell(row, ci, h or ""); c.alignment = CEN; c.border = BOX; c.font = Font(size=8)
                c.fill = PatternFill("solid", fgColor=COL[h]) if h else EMPTY
            row += 1
        row += 1
    ws.freeze_panes = "C3"

# --- Sunway
ws = wb.create_sheet("6 Sunway")
ws.cell(1, 1, "TIME PLANET SUNWAY TIKTOK (in-store, mall 10am-10pm). 5 lives/day x 2h. L1 11am-1pm | L2 1-3pm | L3 4-6pm | L4 6-8pm | L5 8-10pm").font = B
ws.cell(2, 1, "Rule (same as yours): on Pikah/Shifa off day Aina takes their 2 lives and Anggun does L5; on Aina's off day Anggun does L5. Anggun = in-store standby other days.")
header(ws, 4, ["Host", "Off day"] + DAYS, [12, 10] + [22] * 7)
for ri, h in enumerate(SW_HOSTS, 5):
    ws.cell(ri, 1, h).font = B; ws.cell(ri, 2, OFF[h])
    for ci, d in enumerate(DAYS, 3):
        r = sunway_day(d)
        validate(r, f"SW-{d}")
        if OFF[h] == d:
            txt, fill = "OFF", "D9D9D9"
        elif h in r:
            txt, fill = "\n".join(f"Live {rng(s,e)}" for _, s, e in r[h]), COL[h]
        else:
            txt, fill = "Standby / store (no live)", "FFF2CC"
        c = ws.cell(ri, ci, txt); c.alignment = WRAP; c.border = BOX; c.fill = PatternFill("solid", fgColor=fill)
    ws.row_dimensions[ri].height = 32
ws.cell(11, 1, "OPTION B (suggestion)").font = B
ws.cell(12, 1, "With 3h sessions allowed, 2 hosts can cover the FULL 10am-10pm: Host A 10am-1pm + 4-7pm, Host B 1-4pm + 7-10pm (12 live-hours vs 10 today). "
        "Pikah + Shifa could run this daily, freeing Aina and Anggun as standby/sales. This is also the emergency pattern (sheet 9).")

# --- HQ emergency sheets
for week in ("A", "B"):
    ws = wb.create_sheet(f"{7 if week=='A' else 8} HQ Emergency {week}")
    ws.cell(1, 1, f"IF THIS HOST TAKES MC / EMERGENCY LEAVE (WEEK {week}) - who covers each session. "
            "'moves from X' = that host switches account at the same time and X pauses. OT = paid overtime.").font = B
    header(ws, 2, ["Absent host"] + DAYS, [12] + [40] * 7)
    for ri, h in enumerate(HQ_FT + ["HUSNA"], 3):
        ws.cell(ri, 1, h).font = B
        for ci, d in enumerate(DAYS, 2):
            lines_ = emergency(week, d, h)
            txt = "\n".join(lines_)
            c = ws.cell(ri, ci, txt); c.alignment = WRAP; c.border = BOX
            if "PAUSE (peak" in txt and "Time Planet" in txt:
                c.fill = PatternFill("solid", fgColor="FFC7CE")
        ws.row_dimensions[ri].height = 95
    r0 = 3 + len(HQ_FT) + 2
    ws.cell(r0, 1, "Karmen / Wani absent: Timezone Gallery pauses those hours (lowest priority). Ask the other one first if she can swap.").font = B
    ws.freeze_panes = "B3"

# --- Sunway emergency
ws = wb.create_sheet("9 Sunway Emergency")
ws.cell(1, 1, "SUNWAY: IF A HOST IS ABSENT. 3 hosts present = normal 5 lives | 2 present = 4 x 3h (10am-10pm, no OT) | 1 present = 1-4pm + 7-10pm").font = B
header(ws, 2, ["Absent host"] + DAYS, [12] + [30] * 7)
for ri, h in enumerate(SW_HOSTS, 3):
    ws.cell(ri, 1, h).font = B
    for ci, d in enumerate(DAYS, 2):
        if OFF[h] == d:
            txt = "(off day)"
        else:
            r = sunway_day(d, absent=h)
            validate(r, f"SWE-{d}-{h}")
            txt = "\n".join(f"{x}: " + ", ".join(rng(s, e) for _, s, e in v) for x, v in r.items())
            if not txt:
                txt = "No host - pause"
        c = ws.cell(ri, ci, txt); c.alignment = WRAP; c.border = BOX
    ws.row_dimensions[ri].height = 60
ws.cell(8, 1, "Two Sunway hosts absent on the same day: the last host does 1-4pm + 7-10pm; HQ adds an extra Time Planet TikTok push (vouchers/flash deal) to recover sales. "
        "Sunway cannot be covered from HQ because lives must be in-store.").alignment = WRAP

# --- SOP
ws = wb.create_sheet("10 Emergency SOP")
ws.column_dimensions["A"].width = 26; ws.column_dimensions["B"].width = 120
sop = [
    ("STEP 1 - Report", "Host CALLS (not only WhatsApp) the Live Supervisor as soon as she knows. Latest: 2h before her first live. "
     "Night shift (6pm onwards): by 3pm. MC photo to HR same day."),
    ("STEP 2 - Look up cover", "Supervisor opens sheet 7/8 (HQ, correct week) or 9 (Sunway), finds the absent host + today's day, and calls the cover host(s). Target: confirmed within 30 min."),
    ("STEP 3 - Announce", "Post in the live-team group: who is covering which slot, which account pauses. Update the live schedule in TikTok/Shopee if slots are pre-announced."),
    ("STEP 4 - Fallback order", "1) Host live on a lower-priority account at the same time switches over (that account pauses)  2) Host on shift with a spare live hour  "
     "3) OT: the host next to the gap extends her shift (max 1 extra session, 3h)  4) Part-timers: Husna (nights), Wani (Tue/Wed can do 2 shifts)  "
     "5) Pause the slot - only allowed for 7-10am and Timezone Gallery / Shopee daytime."),
    ("STEP 5 - Log", "Record date, absent host, reason, cover host, OT hours, account paused. Use for payroll and to spot repeated absences."),
    ("", ""),
    ("LEVEL 1", "1 host out: follow sheet 7/8/9. No customer-facing impact on TP TikTok peak hours."),
    ("LEVEL 2", "2+ HQ hosts out same day: pause Timezone Gallery fully; Shopee runs 5pm-12am only; every free HQ host goes to TP TikTok first, then Bilano Polo 8pm-2am. "
     "OT approved automatically for the night (6pm-2am)."),
    ("LEVEL 3", "3+ out or big sales day: Supervisor/manager steps in as host if trained; run TP TikTok and Bilano only."),
    ("Do NOT", "Do not loop a recorded video as a 'live' - TikTok can restrict or penalise the account for unoriginal live content. Better to pause and post short videos."),
    ("", ""),
    ("BIG SALES DAYS", "11.11 (in 11 days) and 12.12: no annual leave from 2 days before to 1 day after. Every full-timer does 2 sessions + 1 OT session (3h). "
     "Sunway uses the 4 x 3h pattern + OT. Book OT and transport for after-midnight shifts in advance."),
    ("READINESS (do this week)", "a) Cross-train: every HQ full-timer must be able to host TP TikTok + one more account (products, prices, vouchers, script, logins). "
     "Backup pairs: Ayuni<->Puteri<->Farisah (TP), Nani<->Ariesya (Bilano), Eisya<->Elyana (Shopee), Yasmin = all.  "
     "b) Keep a 'live kit' per account in the studio: run-sheet, product list, voucher codes, phone/stand/lighting.  "
     "c) Each host does 1 practice session per month on her backup account.  d) Keep Husna/Wani's extra availability updated every month."),
    ("OT & safety", "Pay OT according to the Employment Act and HR policy (normally 1.5x hourly rate on a working day, more on rest days and public holidays; max 104 OT hours/month - confirm with HR). "
     "Shifts that end at 12am-2am (Farisah, Nani, Husna, Elyana): give transport claim/Grab for safety."),
]
for i, (a, b) in enumerate(sop, 1):
    ws.cell(i, 1, a).font = B; ws.cell(i, 2, b).alignment = WRAP

# --- Live hours check
ws = wb.create_sheet("11 Live Hours Check")
header(ws, 1, ["Account", "Week"] + DAYS + ["Weekly total"], [26, 6] + [8] * 7 + [12])
row = 2
for a in ("TP", "BP", "SH", "TZ"):
    for week in ("A",):
        tot = 0; ws.cell(row, 1, ACC[a]); ws.cell(row, 2, week)
        for ci, d in enumerate(DAYS, 3):
            occ = validate(hq_day(week, d), "x")
            n = sum(1 for (acc, _hr) in occ if acc == a); tot += n
            ws.cell(row, ci, n)
        ws.cell(row, 10, tot); row += 1
tot = 0; ws.cell(row, 1, ACC["SW"]); ws.cell(row, 2, "-")
for ci, d in enumerate(DAYS, 3):
    n = sum(e - s for v in sunway_day(d).values() for _, s, e in v); tot += n; ws.cell(row, ci, n)
ws.cell(row, 10, tot)
row += 2
ws.cell(row, 1, "Host live hours per week (Week A)").font = B; row += 1
header(ws, row, ["Host", ""] + DAYS + ["Weekly total"]); row += 1
for h in HQ_FT + ["HUSNA", "KARMEN", "WANI"] + SW_HOSTS:
    ws.cell(row, 1, h); tot = 0
    for ci, d in enumerate(DAYS, 3):
        r = sunway_day(d) if h in SW_HOSTS else hq_day("A", d)
        n = live_hours(r, h); tot += n; ws.cell(row, ci, n if h in r else "OFF" if OFF[h] == d else 0)
    ws.cell(row, 10, tot); row += 1

# --- Confirm
ws = wb.create_sheet("12 To Confirm")
ws.column_dimensions["A"].width = 30; ws.column_dimensions["B"].width = 110
conf = [
    ("6th live account", "Your sheet lists 5 accounts (TP TikTok, TP Sunway TikTok, TP Shopee, Bilano Polo TikTok, Timezone Gallery TikTok). Which is the 6th, who hosts it and at what hours?"),
    ("Account priority at HQ", "Plan assumes TP TikTok > Bilano Polo > TP Shopee > Timezone Gallery. If Shopee sells more than Bilano, swap them in PRIORITY in build_roster.py."),
    ("Yasmin off day", "Proposed Wed -> Sun (see Summary). If it stays Wednesday: on Wednesdays Ariesya covers Ayuni's TP TikTok shift and Bilano runs only Nani's sessions."),
    ("Karmen slot", "Proposed 11am-3pm instead of 11am-1pm + 3-5pm (clash with Wani's Nov 3-5pm on Timezone Gallery)."),
    ("Wani December", "From December Wani does 10pm-12am: Timezone Gallery 10pm-12am. Yasmin's free-time Timezone slot becomes 5-8pm + 8-10pm. Update hq_day() monthly."),
    ("Peak hours", "Slot priorities assume TikTok peak 8pm-12am and lunch 12-2pm. Please check TikTok Shop / Shopee analytics GMV by hour; if 7-10am sells little, that slot can be dropped and moved to 12-2am."),
    ("CONTRACTS (HR sheet)", "Contract end dates in the HR sheet: AYUNI 30 Jun 2026, AINA 12 Sep 2026, PUTERI 30 Sep 2026, ARIESYA 30 Sep 2026 (already passed), "
     "PIKAH 31 Oct 2026 (today), ELYANA 31 Dec 2026. These are key hosts on both main accounts - please confirm renewals; if the HR sheet is just not updated, update it."),
]
for i, (a, b) in enumerate(conf, 1):
    ws.cell(i, 1, a).font = B; ws.cell(i, 2, b).alignment = WRAP

out = __file__.replace("build_roster.py", "Live_Host_Roster_Plan.xlsx")
wb.save(out)
print("saved", out)
if __name__ == "__main__":
    for d in DAYS:
        for h in HQ_FT + ["HUSNA"]:
            print(d, h, emergency("A", d, h))
