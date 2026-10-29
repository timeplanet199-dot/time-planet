import re, json, csv, math, collections
from xl import read
from paths import STOCK, SALES_DIR, SALES_WEEKS
num = lambda x: float(str(x).replace(',', '')) if x not in (None, '') else 0.0
norm = lambda s: re.sub(r'\s', '', re.sub(r'-TP$', '', str(s).strip().upper()))

# stock 28 Oct, all brands
rows = read(STOCK)['Page 1']
stock, brand = {}, None
for r in rows[2:]:
    r = list(r) + [None] * 13
    if r[1]: brand = r[1]
    if not r[2] or r[2] == 'Brand Total' or brand == 'Grand Total': continue
    stock[norm(r[2])] = dict(code=r[2].strip(), brand=brand, desc=r[3], eco=num(r[5]), hq=num(r[6]), shops=sum(num(r[i]) for i in range(7, 12)), total=num(r[12]))

# sales 11-24 Oct, TikTok + Shopee, by week
import glob, os
files = {}
for f in glob.glob(os.path.join(SALES_DIR, '*.xlsx')):
    try: v = list(read(f).values())[0]
    except Exception: continue
    if not v or v[0][0] != 'Sales Report': continue
    ds = re.findall(r'\d{4}-\d{2}-\d{2}', str(v[0][1]))
    wk = {w: i for i, w in enumerate(SALES_WEEKS)}.get(tuple(ds))
    if wk is None: continue
    si = v[1].index('BigSeller Store Name')
    plat = 'TikTok' if any('iktok' in str(r[si]).lower() for r in v[2:] if len(r) > si) else 'Shopee'
    files[(plat, wk)] = f
assert len(files) == 4, files
sales = collections.defaultdict(lambda: [0.0, 0.0])
names = {}
for (plat, wk), f in files.items():
    v = list(read(f).values())[0]
    h = v[1]; i = h.index('SKU Name'); q = h.index('Valid Product Sales Quantity'); p = h.index('Product Name')
    for r in v[2:]:
        r = r + [None] * (len(h) - len(r))
        if r[i]:
            s = norm(r[i]); sales[s][wk] += num(r[q]); names.setdefault(s, str(r[p])[:60])

def match(s):
    if s in stock: return s, 'exact'
    if s.startswith('BNB'): return None, 'not found in stock file'
    for suf in ('UDF', 'DF', 'D'):
        if s + suf in stock: return s + suf, 'stock code adds suffix (e.g. UDF)'
    c = [k for k in stock if k.startswith(s) and len(k) - len(s) <= 4]
    if len(c) == 1: return c[0], 'stock code adds suffix (e.g. UDF)'
    t = re.sub(r'-[0-9A-Z]{1,3}$', '', s)
    if t != s and t in stock: return t, 'sales code has extra dial/colour suffix'
    return None, 'not found in stock file'

agg = collections.defaultdict(lambda: [0.0, 0.0]); how = {}; unmatched = []
for s, (a, b) in sales.items():
    m, why = match(s)
    if m:
        agg[m][0] += a; agg[m][1] += b; how.setdefault(m, set()).add(why)
    elif s.startswith('BNB'):
        stock[s] = dict(code=s, brand='BONI', desc='BONIA ' + s, eco=0.0, hq=0.0, shops=0.0, total=0.0, missing=True)
        agg[s][0] += a; agg[s][1] += b; how.setdefault(s, set()).add('not in stock file, counted as 0 stock')
    elif a + b > 0:
        unmatched.append((a + b, s, names[s]))
tot = sum(a + b for a, b in sales.values()); mt = sum(a + b for a, b in agg.values())
print('sales units', SALES_WEEKS[0][0], 'to', SALES_WEEKS[-1][1], tot, 'matched', mt, f'{mt / tot:.0%}')
bys = collections.Counter()
for k, (a, b) in agg.items(): bys[stock[k]['brand']] += a + b
print('matched units by brand', bys.most_common(15))
unmatched.sort(reverse=True)
print('top unmatched', unmatched[:15], 'unmatched units', sum(u[0] for u in unmatched))
json.dump(dict(agg={k: v for k, v in agg.items()}, how={k: sorted(v) for k, v in how.items()}, unmatched=unmatched, stock=stock), open('allbrand.json', 'w'))
