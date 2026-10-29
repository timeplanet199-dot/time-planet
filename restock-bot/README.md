# Restock bot: daily 8pm report in the Time Planet operation group

A Google Apps Script that runs every day at 8pm Malaysia time. Each run, it:
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

## Setup (once, about 10 minutes, signed in as timeplanet199@gmail.com)

1. Go to [script.google.com](https://script.google.com) → **New project**. Name it "Time Planet restock bot".
2. Click **Project Settings** (gear icon):
   - tick **Show "appsscript.json" manifest file in editor**;
   - set the time zone to **(GMT+08:00) Kuala Lumpur**.
3. In the **Editor**:
   - replace `appsscript.json` with this folder's `appsscript.json`;
   - rename `Code.gs` if needed and paste this folder's `Code.gs` into it;
   - add two more script files, `Logic` and `Data`, and paste `Logic.gs` and `Data.gs` into them.
4. **Project Settings → Script properties → Add script property**:
   - name `TG_TOKEN`;
   - value: the **Stock manager** token from the
     ["access" doc](https://docs.google.com/document/d/1o6kk_61Au53DkF2_FI3e-M3OVw0Of2gqrtej7OgFOyQ/edit).

   Never paste the token into the code or a chat.
5. In Telegram, add the Stock manager bot to the **Time Planet operation group** and send any message in the group.
6. In the Editor, pick `findChats` in the function list and click **Run**:
   - Google asks for permission. Click Advanced → "Go to Time Planet restock bot", then Allow.
   - The log should say `Saved TG_CHAT_ID = -100…`. If it lists several groups instead, add `TG_CHAT_ID` by hand in
     Script properties.
7. Run `previewReport` and read the report in the log. Nothing is sent.
8. Run `setup`. This creates the daily trigger. Apps Script runs it between 8:00 and 8:15pm.
9. Optional: run `dailyRestockReport` once to post a report to the group now.

If a run fails, the bot posts "Restock report failed" with the reason. You can see past runs under **Executions**.

## Updating

- **Code changes:** edit the files here, then paste them into the Apps Script project again.
- **Tiers or unit costs:** edit `scripts/sheet26.csv` or `scripts/unitcost.json`, then run
  `python3 restock-bot/tools/make_data.py` from the repo root and paste the new `Data.gs`.
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
