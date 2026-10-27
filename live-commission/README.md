# Live Commission Tracker

This replaces handwritten lists of "orders sold during my live". It's free and
built on Google Sheets + Apps Script, like the fulfillment tracker.

It answers two questions automatically:

1. **Did this order come from this host's live?** The host taps **GO LIVE** /
   **END LIVE** on their phone, so every session has an exact start and end time.
   Orders are then matched to the host from the marketplace's own order export.
2. **Is the order safe to pay commission on?** Commission is paid only on orders
   the marketplace marks **Completed**. Pending orders wait for a later payout,
   cancelled or returned orders are never paid, and an order cancelled *after*
   it was paid is deducted from the host's next payout automatically.

## 1. How an order is matched to a host

Checked in this order, first match wins. The `Matched By` column shows which rule
was used for each order:

| # | Rule | How reliable |
|---|---|---|
| 1 | **Override**: you typed a host ID (or `NONE`) in `Override Host` | Your decision |
| 2 | **Voucher**: the order used a host's live-only voucher code | Strong. Works even if the buyer checks out after the live ends |
| 3 | **Live source + time**: the export says the order came from a live, and it was placed during the host's session | Strong |
| 4 | **Time only**: placed during the host's session, but the export doesn't say where it came from | Weaker. Normal shop orders placed during the live also count |

- "During the session" means between GO LIVE and END LIVE, plus 15 minutes for
  buyers who are still checking out (`GRACE_MINUTES`).
- If two hosts overlap on the same platform (a handover), the order goes to the
  host who started most recently. Overlaps are flagged on the dashboard.
- If a host forgets END LIVE, the session is cut off after 6 hours
  (`MAX_SESSION_HOURS`) and flagged. Type the real end time into the `Sessions`
  sheet, then run **Recalculate matching**.

### Make matching strong: give every host a live-only voucher
This is the most important thing you can do. In Shopee/TikTok/Lazada seller
centre, create a **seller voucher per host** (for example `LIVEAMY`, small
discount or free shipping) that is announced **only during their live**. Put the
code in the `Voucher Codes` column of `Hosts` (comma-separate several codes). Any
order using that code goes to that host with no doubt at all. This also handles
two hosts selling on the same shop account, which time matching can't.

If your platform's export has a column showing where the order came from (live,
video, product page…), add its header name to `CONFIG.COLUMNS.source`. Orders
marked as not live are then excluded even if they were placed during a session.
If you have neither vouchers nor a source column and don't want "time only"
orders counted, set `COUNT_TIME_ONLY: false`.

## 2. How cancellations are handled

Each order gets a **State** from the marketplace status (and the return/refund
column, if the export has one):

| State | When | Commission |
|---|---|---|
| `PENDING` | unpaid, to ship, shipping, delivered (still in return window) | Shown as *waiting*, not paid yet |
| `COMPLETED` | marketplace status is Completed | Paid in the next payout |
| `CANCELLED` | status or return/refund column mentions cancel/return/refund/failed/lost | Never paid |

Every time you import a newer export, the status of existing orders is updated
(orders are matched by order number, so importing overlapping exports is fine).
A pending order that later completes gets paid in the next payout. If an order
is cancelled or returned **after** it was paid, it shows in red on the
dashboard and is **deducted** from that host's next payout.

The rule is cautious: a partial refund or a rejected return request also counts
as cancelled. If you decide an order should still be paid, type `COMPLETED` in
its `Override State` cell (or `CANCELLED` / `PENDING` to force those).

## 3. Setup (about 15 minutes)

1. Create a new Google Sheet, for example "Live Commission".
2. **Extensions → Apps Script**. Delete the sample code, then create:
   - `Code.gs`
   - `Live.html` (File → New → HTML, name it `Live`)
   - `Dashboard.html` (name it `Dashboard`)
3. **Project Settings (gear icon)**: set your time zone. Also set the same time
   zone in the Sheet: **File → Settings**.
4. At the top of `Code.gs`, check `CONFIG`:
   - `PLATFORMS`: the platforms you go live on.
   - `DASHBOARD_PIN`: set a PIN so hosts can't open the money page.
   - `DATE_ORDER`: `'DMY'` if your export writes dates like 27/10/2026.
5. Pick the `setup` function, press **Run**, and approve the permissions. This
   creates the sheets.
6. In `Hosts`, fill in each host: ID (keep it short, like `H01`), name,
   commission % (5 means 5%), their live voucher code(s), and Active (`FALSE`
   hides them from the host page without losing their history).
7. **Deploy → New deployment → Web app**. Execute as *Me*; access *Anyone with
   the link*. Reload the Sheet: a **Live Commission** menu appears.
   **Live Commission → Show web app links** gives you the two links:
   - **Host page**: send to hosts. They pick their name and platform once, then
     only tap GO LIVE / END LIVE.
   - **Dashboard**: for you and accounts.

After changing the code: **Deploy → Manage deployments → Edit → New version**,
so the links keep working.

## 4. Importing orders

Export orders from the seller centre (all orders, or at least the days with
lives), then:

1. Open the `Import` sheet and click A1.
2. **CSV file**: **File → Import → Upload**, choose *Replace current sheet*, and
   **untick "Convert text to numbers, dates, and formulas"**.
   **Excel file**: open it, select all, copy, then paste into `Import` with
   **Ctrl+Shift+V** (paste values only).
   Both keep long order numbers (TikTok's are 18 digits) exactly as they are. If
   a number gets rounded anyway, the import stops and tells you.
3. **Live Commission → Import orders from Import sheet…** and type the platform.
4. The message shows how many orders were new or updated, how they were matched,
   and **which export column was used for each field**. On the first import,
   check that list. If a column says *(not found)* or the wrong one is used, add
   the exact header from your export to `CONFIG.COLUMNS`. Amounts: by default
   the product subtotal (excluding shipping) is used and product rows of the same
   order are added up. If your amount column is a per-order total repeated on
   every row, set `AMOUNT_PER_ITEM_ROW: false`.

The `Import` sheet is cleared after a successful import. Re-import fresh exports
regularly, e.g. weekly, so statuses keep moving from pending to completed or
cancelled.

**Recalculate matching** re-runs the matching for every unpaid order. Use it
after you fix a session time, add a voucher code, change a commission % or type
an override.

## 5. Paying commission (monthly)

1. Import the latest exports of all platforms first, so statuses are current.
2. **Live Commission → Create payout…** and enter the cutoff date (default: last
   day of last month).
3. It pays every **completed, not yet paid** order placed up to that date, and
   deducts any paid order that was cancelled since. Each paid order is stamped
   with the payout ID, so **it can never be paid twice**.
4. You get a row per host in `Payouts` and a new sheet **"Payout P…"** listing
   every order behind every amount, with a total per host. Send that sheet to
   accounts in place of the handwritten list. Hosts can check every order.
5. Orders that weren't completed yet stay unpaid and are picked up by a later
   payout once completed. The payout message tells you how many are still
   waiting.

## 6. Using the dashboard

- **Per host** (pick a month): sessions, live hours, orders, sales, sales per live
  hour, commission payable now, waiting, already paid, and **cancel %**. A high
  cancel % (red at 20%+) can mean fake or pressured orders. Since those are never
  paid, there's nothing to gain from them, but it's worth a talk. Click a host to
  see their individual orders.
- **Live sessions**: orders and sales per session. Once a week, compare a few
  sessions with the platform's own live statistics (Shopee Live / TikTok LIVE
  dashboards show orders per stream). If the numbers are far apart, check
  whether hosts press GO LIVE / END LIVE on time.
- Flags: sessions where END LIVE wasn't pressed, overlapping sessions, and paid
  orders that were cancelled afterwards.

## 7. Rules to agree with hosts (put them in writing)

- Commission = `Commission %` × product subtotal (after discounts, excluding
  shipping) of **completed** orders from their live.
- Paid monthly for orders placed up to the end of the previous month that are
  completed by payout day. Later completions go into the following month.
- Cancelled or returned orders earn nothing. If already paid, they are deducted
  next month.
- No GO LIVE / END LIVE means no time-matched orders. Only voucher orders count
  for that session.
- Use only your own voucher code, and only during your live.

## Sheets reference

| Sheet | Columns | Who edits |
|---|---|---|
| Hosts | ID, Name, Commission %, Voucher Codes, Active | You |
| Sessions | Session ID, Host ID, Host Name, Platform, Start, End, Note | Host page; you fix times |
| Import | (paste area) | You, before each import |
| Orders | Platform … Updated, incl. **Override Host** and **Override State** | Script; you only type overrides |
| Payouts | Payout ID, Created, Cutoff, Host, Orders Paid, Sales, Commission, Deducted, Net | Script |
