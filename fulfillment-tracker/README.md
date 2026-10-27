# Fulfillment Tracker + Process Playbook

A free tracking system for a small packing team, built on Google Sheets and Apps
Script, plus a step-by-step plan to raise output from 300 orders/day.

## 1. How the tracking works

**Rule: every person scans the order barcode when they FINISH their step.**

| Station | Who does it | Scan when |
|---|---|---|
| Pick & Label | prints label, finds products, sticks label | label is on the products, handed to packing |
| Pack & Warranty | packs, warranty card, seals | parcel is sealed and on the "ready to ship" pile |

Every scan saves *time + order + station + person*. From that the dashboard shows:

- **Orders per person per station**, and orders per hour.
- **Median seconds per order**: true working speed, without breaks.
- **Idle breaks**: every gap of more than 10 minutes between one person's scans.
- **Scans per hour** for each person, so you can see who slows down after lunch.
- **Stuck orders**: picked but not packed after 60 minutes, and who picked them.
- **Skipped steps**: an order packed that was never scanned at picking, which means
  someone isn't scanning or an order went missing.
- **Duplicates blocked**: the same order can't be counted twice at one station, so
  nobody can inflate their numbers.

Hardware: one **USB or Bluetooth barcode scanner** per station (about USD 15–25
each). It types like a keyboard into a PC, tablet or phone, so the scan page
works with any of them. The marketplace/courier label already has a barcode, so
you don't need to print anything new.

## 2. Setup (about 15 minutes)

1. Create a new Google Sheet, for example "Fulfillment Tracker".
2. **Extensions → Apps Script**. Delete the sample code, then create three files
   and paste in this folder's contents:
   - `Code.gs`
   - `Index.html` (File → New → HTML, name it `Index`)
   - `Dashboard.html` (name it `Dashboard`)
3. **Project Settings (gear icon)**: set the time zone to your local time zone.
4. In the editor, pick the `setup` function and press **Run**. Approve the
   permissions. This creates the `Staff` and `Log` sheets.
5. In the `Staff` sheet, put your 6 workers' real names (keep the IDs). To remove
   someone, set `Active` to FALSE.
6. **Deploy → New deployment → Web app**. Execute as: *Me*. Who has access:
   *Anyone with the link* (or "Anyone in your organisation" if you use Workspace).
   Copy the URL.
7. Open the URL on each station's device. Each person picks their name and their
   station once (it's remembered), then just scans.
8. Dashboard: the same URL with `?page=dashboard` at the end, or the link at the
   bottom of the scan page. It refreshes every minute.

If you change the code later, use **Deploy → Manage deployments → Edit → New
version** so the same URL keeps working.

The raw data stays in the `Log` sheet, so you can also build pivot tables there,
for example orders per person per week. When it passes about 100,000 rows, move
old months to another sheet so it stays fast.

## 3. How to use the numbers

- **Daily, 5 minutes before closing:** open the dashboard. Anyone in red (no
  scans, under 75% of the team's average speed, more than 60 idle minutes, or
  skipped steps) gets a short, private talk the next morning. Ask what blocked
  them before assuming laziness; often it's stock that can't be found or a
  printer queue.
- **Weekly:** post a simple leaderboard (orders per person). A small bonus for
  everyone above target works better than punishment.
- **Set targets from your own data:** after one week, use the median
  seconds/order of your best two people as the standard. Example: 90 sec/order
  at packing works out to 40 orders/hour.
- **Rotate stations weekly** for a while, so you can compare people on the same
  job. Picking and packing speeds aren't comparable with each other.

## 4. Optimising the process: from 300/day toward 600+/day

Right now: 300 orders ÷ 6 people ÷ ~8 h ≈ **6 orders per person per hour**, about
10 minutes of labour per order. A well-run small-parcel team usually reaches 15–30
orders per person per hour, so there's a lot of room. In order of impact:

### a. Stop picking one order at a time: use batch (wave) picking
- Print labels in **waves of 30–50 orders**, not one by one.
- Print a **pick list summed by product** for the wave (most marketplace/seller
  centres and tools like BigSeller, Ginee, ShipStation or Shopify can export it):
  "SKU A × 14, SKU B × 9…".
- One picker collects all items for the wave in one trip into a crate. A second
  person sorts the crate into orders and sticks the labels.
- **Single-item orders** (usually 50–70% of orders) don't need sorting at all.
  Put all "1 × SKU A" orders together, grab 14 of SKU A and stick 14 labels. This
  alone often doubles output.

### b. Make products quick to find
- Give every shelf a **location code** (A1, A2, B1…) and put the location on the
  pick list.
- Put the **top 20% best sellers closest to the packing table**. They are usually
  about 80% of picks.
- One SKU per bin, with a clear label and photo. No mixed bins.

### c. Remove handwriting from the warranty card
Handwriting each card is probably your slowest step. Options, best first:
1. **Print the warranty card automatically** with the order number, date and
   product (mail-merge from the order export, or print a 2nd small label and stick
   it on a pre-printed card).
2. Or use a **QR code e-warranty**: the card is pre-printed and the customer scans
   it to register with their order number. No writing at all, and you also
   collect customer contacts.
3. Or at minimum use a **date stamp + order sticker**, never full handwriting.

### d. Balance the line using the dashboard
Measure seconds/order per station for one week, then put people where the
bottleneck is. For example, if packing takes 2× as long as picking:
**2 pickers/labellers → 3 packers → 1 floater** (restocks, prepares boxes, handles
problem orders, does the final scan-out). Re-check weekly. The "stuck orders" list
tells you immediately when packing is falling behind.

### e. Prepare everything before the rush
- Fold boxes, cut bubble wrap and pre-stack warranty cards and flyers **in the
  quiet hour** (or by the floater).
- Every packing table gets the same layout: boxes on the left, tape and filler in
  front, finished parcels on the right. Nothing needs walking for.
- Standardise box sizes: 3–4 sizes that cover 90% of orders, each with a fixed
  "which product goes in which box" chart on the wall.

### f. Cut errors (errors cost more than speed)
- The scan system already blocks double scans and flags skipped steps.
- Next level: scan the **product barcode** against the order at packing
  (scan-to-verify), which most order management tools support.

### Suggested 4-week rollout
| Week | Do |
|---|---|
| 1 | Install tracker, everyone scans, **no changes to the process yet**: get a baseline |
| 2 | Batch picking + single-item grouping + shelf locations |
| 3 | Printed or QR warranty cards, pre-prepared materials, rebalance stations from data |
| 4 | Set per-station targets from week 2–3 data, start weekly leaderboard / bonus |

Compare the dashboard each week against week 1 so you know which change actually helped.
