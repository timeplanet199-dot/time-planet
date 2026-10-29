# Time Planet working scripts

These are the commission, restock and campaign scripts from the 26–29 Oct 2026 session. They were copied from
[TimePlanet_handover_scripts_29Oct2026](https://drive.google.com/drive/folders/1zI8QgkwN9IVZQ_RfIfOzCdx9_Q9ZxZ04),
and the paths that pointed to the old PC now point to a local `data/` folder (see `paths.py`).
The method and the rules behind them are in the handover doc:
[Time Planet - Handover, workflow, progress and SOP (29 Oct 2026)](https://docs.google.com/document/d/1t4kiC1YAa39I10IHR-fxNy0uYJPBaA3fwFi2x4w5sCA/edit).

Needs Python 3 with pandas, openpyxl and matplotlib (`pip install pandas openpyxl matplotlib`).
`xl.py` and `xw.py` are small xlsx readers/writers that the scripts use. No tokens or passwords are stored here.

## 1. Put the input files in `data/`

`data/` is git-ignored: business data stays on Drive. Download each file and save it under the name shown.
(In a Claude cloud session: download with the Google Drive connector, then
`python3 unpack.py <saved download> "<destination>"`.)

| Save as (inside `data/`) | Drive file |
|---|---|
| `tiktok/TIME PLANET sept 2026 tiktok order.csv` | [Sept order export](https://drive.google.com/file/d/16KEq-_ZgfTv32KoQ9Vk4tKJ5NS9ZYBjw/view) |
| `tiktok/TIME PLANET oct 2026 tiktok order.csv` | [Oct order export](https://drive.google.com/file/d/19ODn0hmajJ0gBBuOiN_pA_YIGfF6ga6w/view) |
| `tiktok/TIME PLANET sept 2026 tiktok transaction.xlsx` | [Sept income report](https://drive.google.com/file/d/1p_DUj8e1-AqFsbM1sVV1bzj7RkAS0qXg/view) |
| `tiktok/TIME PLANET oct 2026 tiktok transaction.xlsx` | [Oct income report](https://drive.google.com/file/d/1LODsE68u0lrGGZa-96enkoxKlIsjpD5B/view) |
| `Live Host Timetable Time Planet.xlsx` | [Timetable xlsx copy](https://drive.google.com/file/d/1Uw1N9cMSfPxYek60T5AGvQYUUJoZnjPW/view), or download the [live sheet](https://docs.google.com/spreadsheets/d/1XUqYtMl9cIKYMzU6rg9sGMQrzcsNOURFAcO6A_wnyxo/edit) as xlsx |
| `stock/TPSB 28-10.xlsx` | [TPSB 28/10](https://drive.google.com/file/d/1zfQwGDo_cnFYVpiC7h9g7axsyjiCMxuc/view); use the newest TPSB file in [STOCK REPORT FILE](https://drive.google.com/drive/folders/1ePcVVTswJ_n520Avw1EwRpUjOVsga44M) |
| `bigseller/*.xlsx` (any name) | BigSeller weekly Sales Reports, TikTok ([big seller data](https://drive.google.com/drive/folders/1tdwYVsuQuVRD8qHKei0CJzLNQz5HY22m)) and Shopee ([Shopee](https://drive.google.com/drive/folders/1vSfwEKhJJrid3O3UUQNva8TcdoUUYK58)) |

For a new month or a new stock date, change the file names or the `SALES_WEEKS` dates in `paths.py`. That is the only file that needs editing.

## 2. Run

Run every command from inside `scripts/`.

Live host commission (handover section 5.5): `python3 alllive.py`, then `python3 build3.py` → `Live_host_commission_Sep-Oct2026.xlsx`.
(`comm.py` → `host.py` → `build.py`/`build2.py` is the older BPC-only chain, kept for reference.)

Restock (handover section 6.5):
- Bonia, 77 tiered SKUs: `python3 restock.py`, then `python3 tg_table.py` (Telegram image).
- All brands: `python3 allbrand.py`, then `python3 allplan.py`, then `python3 tg_all.py`.

Campaign multiplier (rough, own method, low confidence): `python3 agg.py`, then `python3 uplift.py`.

## 3. Checked on 29 Oct 2026, against the handover numbers

- `alllive.py` on the Sept + Oct exports gives the same results as the handover:
  - BPC live: 615 watches, 432 paid, RM2,979 paid, RM307 pending.
  - Total Revenue matches on all 5,406 orders, once the refund column is added back.
  - timeplanetsunway: 1,366 Bonia rows marked "account not in timetable".
  - Host matching was **not** re-run, because the timetable was not downloaded here. Only its file path changed (`tt.py`).
- `restock.py` on TPSB 28/10 gives 0 mismatches against the Restock Monitor on 77 SKUs: order 499, move 97, 50 urgent. `tg_table.py` renders the image.
- `allbrand.py` was tested on synthetic weekly files. It picks the two `SALES_WEEKS` per platform, ignores other weeks, and its totals add up. It has not yet been re-run on the real BigSeller files.

## 4. Known limits (not fixed, to keep the scripts as they were)

- `restock.py` takes Bonia sales and tiers from `sheet26.csv`, a snapshot of the Restock Monitor (sales 1–24 Oct). A new stock file updates stock only. For the 2–4 Nov run, refresh the sales columns too.
- Some labels are fixed text and need editing by hand:
  - titles and file names say "28 Oct" / "Sep-Oct2026";
  - `tg_table.py` says "about RM 206,809 at cost";
  - `build3.py` counts timetable shifts up to 28 Oct.
- Sending to Telegram is not scripted. Follow handover section 7: @timeplanet_assist_bot only, with the token read from the "access" doc. Never save the token in a file.
