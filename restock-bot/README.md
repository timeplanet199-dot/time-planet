# Restock bot: daily 8pm report in the Time Planet operation group

A Google Apps Script (one file, `dist/RestockBot.gs`) that runs every day at 8pm Malaysia time. Each run, it:
1. Takes the newest **TPSB dd/mm** stock file from
   [STOCK REPORT FILE](https://drive.google.com/drive/folders/1ePcVVTswJ_n520Avw1EwRpUjOVsga44M).
2. Takes the BigSeller daily (`dd/mm TIKTOK`, `dd/mm SHOPEE`) and weekly (`TIKTOK OCT26 WEEK 3` …) sales reports from
   [big seller data](https://drive.google.com/drive/folders/1tdwYVsuQuVRD8qHKei0CJzLNQz5HY22m) and
   [Shopee](https://drive.google.com/drive/folders/1vSfwEKhJJrid3O3UUQNva8TcdoUUYK58).
3. Works out the restock plan with the same rules as `scripts/restock.py` (the 77 tiered Bonia SKUs) and
   `scripts/allplan.py` (all other SKUs). See the handover doc, sections 6.1–6.2.
4. The **Stock manager** bot posts it to the group:
   - totals, and order / move / urgent counts per brand;
   - **Reminder 1:** the top 20 urgent SKUs to order;
   - **Reminder 2:** if today's TPSB stock file is not on Drive yet, it asks the stock manager to upload it and says
     which older file the report used.

Sales window: the 14 days up to yesterday (24 days for the "Sold-out best seller" tier). Weekly files are used first
and daily files fill the rest; no day is counted twice. If days are missing, the report says so and the daily rates
use only the days found.

## Setup (once, about 3 minutes, on a computer, signed in as timeplanet199@gmail.com)

1. In Telegram, add the **Stock manager** bot to the **Time Planet operation group**, then send any message in the group.
2. Open [script.google.com](https://script.google.com) and click **New project**.
3. Delete the sample code. Open [dist/RestockBot.gs](https://github.com/timeplanet199-dot/time-planet/blob/claude/amazing-knuth-twg7ei/restock-bot/dist/RestockBot.gs),
   click **Copy raw file** (top right of the code), paste it into the editor and press **Save** (Ctrl+S).
4. In the function list at the top of the editor, pick **start**, then click **Run**:
   - Google asks for permission once. Click Review permissions, choose the account, then Advanced → "Go to … (unsafe)", then Allow.
     It is your own script.
   - `start` finds the group, posts today's report there and turns on the daily 8pm run (8:00–8:15pm).

There is no token to paste. The script reads the Stock manager token from the
["access" doc](https://docs.google.com/document/d/1o6kk_61Au53DkF2_FI3e-M3OVw0Of2gqrtej7OgFOyQ/edit) each run. Keep the
token on the line after "Stock manager" in that doc.

If `start` says the group was not found, send another message in the group and run `start` again.
If a nightly run fails, the bot posts "Restock report failed" with the reason. Past runs are under **Executions**.
To check the report without sending it, run `previewReport` and open the log.

## Updating

The source is split into `Code.gs` (Drive, Telegram, trigger), `Logic.gs` (calculation) and `Data.gs` (generated).
After any change, rebuild the single file with `python3 restock-bot/tools/build.py` and paste `dist/RestockBot.gs` again.
- **Tiers or unit costs:** edit `scripts/sheet26.csv` or `scripts/unitcost.json`, then run
  `python3 restock-bot/tools/make_data.py` before the build.
- **Rule values** (lead times, days to keep, …): they are at the top of `Logic.gs`.

## Test

`Logic.gs` holds the calculation only, so it runs in Node. The test compares it with the Python scripts on the same
inputs. It needs `scripts/data/stock/TPSB 28-10.xlsx`:

```bash
python3 restock-bot/test/make_fixtures.py /tmp/restock-test
```

```bash
node restock-bot/test/test_logic.js /tmp/restock-test
```

```bash
node restock-bot/test/test_appscript.js /tmp/restock-test
```

`test_appscript.js` runs `dist/RestockBot.gs` with fake Drive, Sheets and Telegram services. It covers `start()`, the
token read from the access doc, the trigger, both reminders, temp-sheet clean-up and the cache.

Last result (29 Oct 2026):
- Bonia 77: identical to `restock.py` (order 499).
- 598 other SKUs: identical to `allplan.py`.
- Code matching: identical to `allbrand.py`.

## Known limits

- **Not counted:**
  - stock already on order (open POs);
  - outlet walk-in sales;
  - the 11.11 campaign uplift.

  The report says so.
- **Overstock rule:** for brands other than the 77 Bonia SKUs, it follows the Stock Analysis sheet (handover 6.2), not
  `allplan.py`'s plain 8-week rule. Order and move quantities are the same either way.
- **Tiered Bonia SKU with no sales in 14 days but low stock:** shown as "Later". `restock.py` has no case for this.

## Nightly Claude run (what runs now)

A scheduled Claude task, "Daily restock report 8pm", runs every day at 7:39pm Malaysia time, so the report lands before 8pm.
- It fetches the newest TPSB file and the BigSeller reports with the Google Drive connector.
- It runs `tools/nightly.py`, which posts the report to **Time Planet Operation** as the Stock manager bot.

The report is an image:
- headline numbers;
- "What needs your attention";
- the top 12 urgent SKUs, fastest sellers first;
- a brand table;
- a data check.

It's rendered by `tools/render.js` (Playwright) and sent with a short caption. If rendering fails, the text version is sent.

The task needs the **Google Drive connector** attached in the claude.ai routines UI. It reads the token from the access doc
each run and passes it only as `TG_TOKEN`.

Preview without sending:

```bash
python3 restock-bot/tools/nightly.py --stock <download .txt> --stock-title "TPSB dd/mm.xlsx" --sales <read_file_content .txt files>
```
