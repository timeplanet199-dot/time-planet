# Time Planet: Project Handoff

Compiled on 2026-10-27. Covers all four Claude Code chats in the
`timeplanet199-dot/time-planet` repo so far. Use it to pick up the work on another
computer.

---

## 0. Read this first

- **You don't need git.** The Google Drive folder **Time Planet** has a full copy
  of every project's files, one subfolder per project, plus `CHAT_LOG.md` with
  the full conversations. See section 5 for how to continue from Drive.
- **The repo has no `main` branch yet.** Each chat pushed its project to its own
  branch, and each branch contains only that one project. Nothing has been merged.
- **The chats aren't tied to this computer.** They're cloud sessions, so you can
  reopen any of them at [claude.ai/code](https://claude.ai/code) on any computer
  where you're signed in. The links are in the table below. They only open for
  the account that created them (timeplanet199@gmail.com). On another account,
  use `CHAT_LOG.md` from Drive instead.
- **None of the four systems has been used with real data yet.** Each one was
  tested with sample or simulated data only.

| # | Project | Branch | Folder / files | Built with | Chat |
|---|---|---|---|---|---|
| 1 | Packing fulfillment tracker + process playbook | `claude/nifty-feynman-q3ml2o` | `fulfillment-tracker/` | Google Sheets + Apps Script | [session](https://claude.ai/code/session_01VZo3vxbgG7pBNtKtyAoaNE) |
| 2 | KOL (influencer) tracker | `claude/gifted-keller-rbvn4o` | `index.html`, `README.md` (repo root) | Single HTML file, browser storage | [session](https://claude.ai/code/session_01VZo3vyJ3ds64JPznDYosH7) |
| 3 | Live streamer timetable + auto monitor | `claude/vibrant-tesla-arxlvg` | repo root (`app.py`, `monitor.py`, …) | Python / Flask / SQLite | [session](https://claude.ai/code/session_01VZo3vwjp8ePZoh76jYtj8R) |
| 4 | Live host commission tracker | `claude/amazing-hawking-0okoy2` | `live-commission/` (also includes a copy of #1) | Google Sheets + Apps Script | [session](https://claude.ai/code/session_01VZo3vwgrXV7c53uWWE4dzE) |

`claude/ecstatic-bardeen-ff6enj` holds this handoff file and a copy of #1.

---

## 1. Fulfillment tracker + process playbook

**Your request:**
> now i have 6 person to make my packaging fulfillment, once i have order, i have
> to print label, find the products, and stick with lable, after that will pass to
> another person to package it and write warranty card. i couldnt track which of
> them doesnt perform or dint work in the fulfilment flow. and i only able to make
> 300 fulfilment per day on from 6 person. i need a best tracking method and
> optimize the process.

**What was built** (`fulfillment-tracker/`: `Code.gs`, `Index.html`, `Dashboard.html`, `README.md`)

- Rule: **each person scans the order barcode when they FINISH their step.** There
  are two stations: *Pick & Label* and *Pack & Warranty*.
- Hardware: a USB or Bluetooth barcode scanner per station (about USD 15–25). It
  types into a web page on any PC, tablet or phone, and works with the existing
  courier label barcode.
- Every scan saves the time, order, station and person to a `Log` sheet. Staff are
  listed in a `Staff` sheet.
- The dashboard (`?page=dashboard`, refreshes every minute) shows:
  - orders per person per station, orders per hour, and median seconds per order
  - idle gaps over 10 minutes, and scans per hour per person
  - **stuck orders**: picked but not packed after 60 minutes
  - **skipped steps**: packed but never scanned at picking
  - red highlights for no scans, speed under 75% of the team average, or more
    than 60 idle minutes
- Duplicate scans are blocked. Fast scans are queued, so no scan is lost.

**Process playbook** (in the README): the team runs at about 6 orders per person
per hour today, against a typical 15–30 for a well-run small team. The plan:

1. Batch (wave) picking with a pick list totalled by product, and grouping of
   single-item orders. This alone often doubles output.
2. Stop handwriting warranty cards: print them automatically, or use a QR
   e-warranty.
3. Shelf location codes, and best sellers placed next to the packing table.
4. Balance stations using the dashboard data, for example 2 pickers, 3 packers
   and 1 floater.
5. Prepare materials before the rush, and standardise box sizes.
6. Set targets from your best workers' times, with a weekly leaderboard and bonus.

Suggested 4-week rollout: in week 1 only start scanning, to get a baseline. Add
the process changes in weeks 2 and 3, and set targets and the bonus in week 4.

**Status:** the logic was tested with a mocked Sheet in Node. **It has not been
run in a real Google Sheet yet.**

**Setup summary:** create a Sheet → Extensions → Apps Script → paste the 3 files →
set the time zone → run `setup` → enter the 6 real names in `Staff` → Deploy as a
web app → open the URL on each station. The full steps are in
`fulfillment-tracker/README.md`.

**Next steps:**
- [ ] Deploy it in a real Sheet, buy the scanners, and run week 1 as a baseline.
- [ ] After week 1, set per-station targets from the data.

---

## 2. KOL tracker

**Your request:**
> i need a system where i can track the process of my engaged KOL on the
> progress, discussion details and content fulfilment

**What was built** (`index.html`, a single file: open it in any browser, nothing to install)

- **Pipeline:** a drag-and-drop board with the stages Prospect → Contacted →
  Negotiating → Contracted → In Production → Content Review → Published →
  Completed (or Dropped).
- **Discussion log per KOL:** channel, summary, what was agreed (deliverables,
  rates, dates, usage rights), and a next action with a due date. The Follow-ups
  page lists every open action, with overdue ones in red.
- **Content deliverables:** type, platform, quantity, due date, status (Not
  Started → Brief Sent → Draft Submitted → Revision → Approved → Published),
  draft and live links, and views, likes, comments and shares. Each KOL has a
  fulfilment bar, such as "2/3 published".
- **Dashboard:** fulfilment %, overdue items, open follow-ups, committed fees,
  total views, KOLs by stage, and upcoming deadlines.
- **Export/Import** as JSON for backup, plus CSV downloads.
- Three "Sample: …" KOLs load the first time you open it. Delete them when
  you're ready.

**Status:** tested in a headless browser. Two startup bugs were fixed and the
full flow works.

**Limitation:** data is saved only in that browser on that computer. Clearing
browser data deletes it, and teammates can't see it.
**To move your data to another computer:** use Export on the old one and Import
on the new one.

**Next steps:**
- [ ] Decide whether the team needs to share it. Claude offered to turn it into a
      hosted page with a shared database, so everyone sees and edits the same
      records.

---

## 3. Live streamer timetable + automatic monitor

**Your request:**
> i need a preper flow and system that i can arrange my live streamer on their
> timetable, i have to make sure their performance on live too but its too time
> wasting to look on screen to make sure the live streamer make the live stream
> properly.

**What was built** (a Python/Flask web app with SQLite; files at the root of its branch)

- **Streamers:** name, platform and handle, with a "Test live check" button.
- **Timetable:** weekly repeating slots plus one-off shifts. It warns about
  overlaps, and overnight shifts work.
- **Monitor (every 2 minutes):** checks whether each running shift's channel is
  live, and records live time and peak viewers.
- **Alerts** via Telegram, Discord or a webhook, sent only when something is wrong:
  - not live 5 minutes after the start
  - no show 20 minutes after the start
  - went live late
  - offline on 2 checks in a row (a single blip is ignored)
  - ended more than 10 minutes early
  - missed the whole shift
  - can't verify (the platform check keeps failing)
- **Report:** attendance % and punctuality % per streamer for any date range,
  with CSV export. Each shift has a minute-by-minute check log for disputes.
- **Personal link per streamer** (`/c/<code>`, no login): shows their own shifts,
  and has an "I'm LIVE now" button for platforms that can't be checked
  automatically.
- **Platforms:**
  - Twitch: official API (needs a free developer key)
  - YouTube: public live page, or the official API if you add a key
  - TikTok: reads the public live page. **This hasn't been tested against real
    TikTok.**
  - Manual check-in (Shopee, Lazada, Facebook and others): trust-based, so
    spot-check these streamers.
- The default time zone is `Asia/Kuala_Lumpur`. Change it with `TP_TIMEZONE` in
  `.env`.

**Status:** all 8 tests pass and every page loads with demo data. It has only
been run on demo data.

**Setup summary:**
```bash
git checkout claude/vibrant-tesla-arxlvg
pip install -r requirements.txt
cp .env.example .env        # set TP_ADMIN_PASSWORD, TP_SECRET_KEY, Telegram bot token + chat id
set -a; . ./.env; set +a
python app.py               # http://localhost:5000
# demo: TP_DATABASE=demo.db python seed_demo.py && TP_DATABASE=demo.db python app.py
```
It must run on an **always-on machine or a small server** (VPS, Render or
Railway), because it only checks streams while it's running.

**Open question from that chat (not answered yet):** *Which platforms do your
streamers mainly use?* If it's TikTok or Shopee, Claude offered to test and
strengthen that check next.

**Next steps:**
- [ ] Answer the platform question above.
- [ ] Create the Telegram bot and choose where to host the app.
- [ ] Add the real streamers, and use "Test live check" on each one.

---

## 4. Live host commission tracker

**Your request:**
> on live streamer commission, i dint have any effective way to track whether the
> sale is come from the live that he or she hosting ornot. the current were hand
> writing and submit to account on those order that being sold during their live
> session. and i have to make sure the order doesnt cancelled by customers before
> paying the comission

**What was built** (`live-commission/`: `Code.gs`, `Live.html`, `Dashboard.html`, `README.md`)

- **Host page:** hosts tap **GO LIVE** and **END LIVE** on their phone, so every
  session has exact times.
- **Import:** you paste the Shopee/TikTok/Lazada order export into the `Import`
  sheet, then use the menu: Live Commission → Import orders.
- **Matching order → host**, first match wins:
  1. Manual override
  2. **Host's live-only voucher code** (strongest)
  3. Order marked as coming from a live, placed during the session
  4. Placed during the session only (weaker)

  The session window includes 15 minutes of grace after END LIVE. Sessions with
  no END LIVE are cut off after 6 hours and flagged.
- **Cancellation safety:**
  - Orders are tracked as PENDING, COMPLETED or CANCELLED. Each newer import
    updates their status.
  - Commission is paid **only on COMPLETED orders**.
  - Each paid order is stamped with the payout ID, so it can never be paid twice.
  - If an order is cancelled after it was paid, it is **deducted from the next
    payout**.
- **Payout:** the menu option Create payout pays everything up to a cutoff date.
  It creates a "Payout P…" sheet listing every order per host. Send that sheet to
  accounts instead of the handwritten list.
- **Dashboard (protected by a PIN):** per host per month, it shows:
  - live hours and sales
  - commission payable now, waiting and already paid
  - cancel % (red at 20% or more)
  - flags for missed END LIVE, overlapping sessions, and paid orders cancelled
    afterwards
- The README includes suggested commission rules to agree with hosts in writing.

**Status:** tested against a simulated Sheet (matching, cancellations, payouts and
deductions), and both pages were rendered in a browser. One UI bug was fixed. **It
has not been run in a real Google Sheet yet.**

**Before relying on it:**
- [ ] **Check the column names on the first import.** The export column headings
      were guessed. The import message lists which column was used for each field.
      If any says *(not found)*, add your export's exact heading to
      `CONFIG.COLUMNS` in `Code.gs`.
- [ ] **Create a live-only voucher code per host** (for example `LIVEAMY`) in the
      seller centre. Without one, matching is by time only, so normal shop orders
      placed during a live also count for the host.
- [ ] Set `DASHBOARD_PIN`, `PLATFORMS` and `DATE_ORDER` (`'DMY'` for dates like
      27/10/2026) in `CONFIG`.

---

## 5. How to continue on another computer

**Option A: from Google Drive (no git needed)**

The Drive folder **Time Planet** (in My Drive of timeplanet199@gmail.com) contains:
```
Time Planet/
├── HANDOFF.md                 ← this file
├── CHAT_LOG.md                ← the full conversations so far
├── 1-fulfillment-tracker/     Code.gs, Index.html, Dashboard.html, README.md
├── 2-kol-tracker/             index.html, README.md
├── 3-streamer-monitor/        app.py, monitor.py, … + templates/, static/, tests/
└── 4-live-commission/         Code.gs, Live.html, Dashboard.html, README.md
```
- **Another Google account:** first share the folder with that account (in Drive,
  right-click the folder → Share), or download it (right-click → Download, which
  gives you a .zip) and upload it to the other account's Drive.
- **#1 and #4 (Apps Script):** open each file in Drive and copy its contents into
  the Google Sheet's Apps Script editor. Follow that folder's `README.md`.
- **#2 (KOL tracker):** download `index.html` and double-click it to open it in a
  browser.
- **#3 (Streamer monitor):** download the whole `3-streamer-monitor` folder and
  follow its `README.md` (Python is needed). Two files start with a dot
  (`.env.example` and `.gitignore`), so they may be hidden in your file browser.
- **To continue with Claude:** start a new chat, upload `HANDOFF.md`,
  `CHAT_LOG.md` and the project folder you're working on, then say something
  like *"Read HANDOFF.md and continue project #3."* In a Claude Code session on
  that computer, put the files in the working folder instead of uploading them.

**Option B: continue in the cloud (same account only)**
Open [claude.ai/code](https://claude.ai/code), signed in as timeplanet199@gmail.com.
Open the session for the project from the table in section 0, or start a new
session on `timeplanet199-dot/time-planet`. Then say something like:
*"Read HANDOFF.md on branch claude/ecstatic-bardeen-ff6enj and continue project #3."*

**Option C: work locally with git**
```bash
git clone https://github.com/timeplanet199-dot/time-planet.git
cd time-planet
git fetch --all
git branch -r                                      # lists the branches above
git checkout claude/nifty-feynman-q3ml2o           # #1 Fulfillment
git checkout claude/gifted-keller-rbvn4o           # #2 KOL tracker
git checkout claude/vibrant-tesla-arxlvg           # #3 Streamer monitor
git checkout claude/amazing-hawking-0okoy2         # #4 Live commission (+ #1)
git checkout claude/ecstatic-bardeen-ff6enj        # this handoff file (+ #1)
```
The Apps Script projects (#1 and #4) don't run from the repo. Copy their files
into a Google Sheet's Apps Script editor, as described in their READMEs.

---

## 6. Suggested housekeeping (not done yet)

- **Combine everything into one `main` branch, with one folder per project**
  (`fulfillment-tracker/`, `live-commission/`, `kol-tracker/`,
  `streamer-monitor/`). Right now the KOL tracker and the streamer monitor both
  put a `README.md` at the repo root, so merging their branches as they are would
  conflict.
- Projects #3 and #4 both record live sessions. Later, the streamer monitor's
  verified live times could replace manual GO LIVE / END LIVE taps in the
  commission tracker.
