# Where every script reads its input files. Download the Drive files listed in
# README.md into data/ with these names (or set TP_DATA to another folder).
import os
DATA = os.environ.get('TP_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
p = lambda *a: os.path.join(DATA, *a)

# Live host commission: TikTok Seller Center exports, Time Planet shop
ORDERS = [p('tiktok', 'TIME PLANET sept 2026 tiktok order.csv'),
          p('tiktok', 'TIME PLANET oct 2026 tiktok order.csv')]
TXN = [p('tiktok', 'TIME PLANET sept 2026 tiktok transaction.xlsx'),
       p('tiktok', 'TIME PLANET oct 2026 tiktok transaction.xlsx')]
TIMETABLE = p('Live Host Timetable Time Planet.xlsx')

# Restock: newest TPSB stock file (STOCK REPORT FILE folder)
STOCK = p('stock', 'TPSB 28-10.xlsx')
# BigSeller weekly Sales Report xlsx (TikTok + Shopee). Files are picked by the
# date range in their header, so any file name works.
SALES_DIR = p('bigseller')
# The 2 sales weeks used for the daily rate, oldest first (allbrand.py)
SALES_WEEKS = [('2026-10-11', '2026-10-17'), ('2026-10-18', '2026-10-24')]
