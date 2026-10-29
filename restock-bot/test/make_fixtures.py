# Builds test inputs for test_logic.js and runs the Python scripts on the same
# inputs, so the JS port can be compared with them. Needs scripts/data/stock/TPSB 28-10.xlsx.
# Run from the repo root: python3 restock-bot/test/make_fixtures.py <work dir>
import csv, json, os, random, subprocess, sys
sys.path.insert(0, 'scripts')
from xl import read
from xw import write
W = os.path.abspath(sys.argv[1]); S = os.path.abspath('scripts')
os.makedirs(W + '/data/bigseller', exist_ok=True); os.makedirs(W + '/data/stock', exist_ok=True)
STOCK = S + '/data/stock/TPSB 28-10.xlsx'
os.system(f'cp "{STOCK}" "{W}/data/stock/TPSB 28-10.xlsx"')
disp = lambda rows: [[('' if v is None else (str(int(v)) if isinstance(v, float) and v == int(v) else str(v))) for v in r] for r in rows]
H = ['BigSeller Store Name', 'SKU Name', 'Product Name', 'Valid Product Sales Quantity']
def sales(a, b, store, items):
    return [['Sales Report', f'{a} ~ {b}' if a != b else f'Time:{a}'], H] + [[store, s, 'x', q] for s, q in items]

# 1) Bonia 77: sales so that (d+e)/14 and (c+d+e)/24 equal the Restock Monitor's
B = list(csv.DictReader(open(S + '/sheet26.csv')))
bonia = [sales('2026-10-01', '2026-10-10', 'Time Planet Tiktok', [(r['sku'], float(r['c'])) for r in B]),
         sales('2026-10-11', '2026-10-17', 'Time Planet Tiktok', [(r['sku'], float(r['d'])) for r in B]),
         sales('2026-10-18', '2026-10-24', 'Time Planet Tiktok', [(r['sku'], float(r['e'])) for r in B])]

# 2) other brands: random stock codes written the ways sales codes differ from stock codes
random.seed(7)
stock_rows = read(STOCK)['Page 1']
b77 = {r['sku'] for r in B}
codes = [r[2].strip() for r in stock_rows[2:] if len(r) > 2 and r[2] and r[2] != 'Brand Total' and r[2].strip() not in b77]
items = []
for c in random.sample(codes, 600):
    v = random.random()
    s = c + '-TP' if v < 0.3 else (c[:-3] if c.endswith('UDF') and v < 0.6 else (c + '-1A' if v < 0.7 else c))
    items.append(s)
items += ['UNKNOWN-%d' % i for i in range(20)] + ['BNB99999-0001']
weeks = [('2026-10-11', '2026-10-17'), ('2026-10-18', '2026-10-24')]
other = []
for a, b in weeks:
    for store in ('Time Planet Tiktok', 'Shopee Time Planet'):
        rows = sales(a, b, store, [(s, float(random.choice([0, 0, 1, 1, 2, 3, 5, 8, 13]))) for s in items])
        other.append(rows)
        write(f'{W}/data/bigseller/{store[:6]}_{a}.xlsx', [('Sheet1', rows, None)])

# Python results on the same inputs
env = dict(os.environ, TP_DATA=W + '/data')
for script in ('restock.py', 'allbrand.py', 'allplan.py'):
    subprocess.run(['python3', script], cwd=S, env=env, check=True, stdout=subprocess.DEVNULL)
for f in ('restock28.json', 'allbrand.json', 'allplan.json'):
    os.replace(f'{S}/{f}', f'{W}/{f}')
os.remove(f'{S}/dead.json')
json.dump({'stock': disp(stock_rows), 'bonia': [disp(r) for r in bonia], 'other': [disp(r) for r in other]},
          open(W + '/fixtures.json', 'w'))
print('fixtures written to', W)
