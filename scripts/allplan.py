import json, csv, math, collections
D = json.load(open('allbrand.json'))
agg, how, stock = D['agg'], D['how'], D['stock']
bonia77 = {r['sku'] for r in csv.DictReader(open('sheet26.csv'))}
LEAD = {'BPC': 75}; CYCLE = {'BONI': 3}
DEF_LEAD, DEF_CYCLE, KEEP, Z, MINL, LEAVE, WINDOW = 7, 7, 10, 0.44, 2, 2, 14

rows = []
for k, (a, b) in agg.items():
    s = stock[k]
    if s['code'] in bonia77 or a + b <= 0: continue
    lead = LEAD.get(s['brand'], DEF_LEAD); cyc = CYCLE.get(s['brand'], DEF_CYCLE)
    d = (a + b) / WINDOW
    line = max(MINL, math.ceil(round(d * max(KEEP, lead), 9)))
    eco, out = s['eco'], s['hq'] + s['shops']
    status = 'RESTOCK' if eco <= line else 'OK'
    left = math.floor(eco / d)
    pri = '' if status != 'RESTOCK' else ('Urgent' if left <= 3 else 'Soon' if left <= 7 else 'Later')
    T = d * (lead + cyc); U = max(0, math.ceil(round(Z * math.sqrt(T), 9))); V = math.ceil(round(T + U, 9))
    X = max(0, V - eco); Y = min(X, max(0, out - LEAVE)); Zq = X - Y
    weeks = (eco + Y + Zq) / (d * 7)
    act = 'Overstocked: skip orders' if weeks > 8 else ('Order from supplier' if Zq > 0 else ('Transfer from outlet' if Y > 0 else 'No action'))
    rows.append(dict(code=s['code'], brand=s['brand'], desc=(s['desc'] or '')[:45], w1=a, w2=b, eco=eco, out=out,
                     match='; '.join(how[k]), daily=d, line=line, status=status, left=left, pri=pri, lead=lead, cyc=cyc,
                     target=V, xfer=Y, order=Zq, weeks=weeks, action=act))
rows.sort(key=lambda r: ({'Urgent': 0, 'Soon': 1, 'Later': 2, '': 3}[r['pri']], -r['daily']))
json.dump(rows, open('allplan.json', 'w'))
c = collections.Counter
print('rows', len(rows), c(r['brand'] for r in rows).most_common())
print('actions', c(r['action'] for r in rows)); print('priority', c(r['pri'] for r in rows))
for b in sorted({r['brand'] for r in rows}):
    rr = [r for r in rows if r['brand'] == b]
    print(b, 'order', sum(r['order'] for r in rr), 'move', sum(r['xfer'] for r in rr), 'urgent', sum(r['pri'] == 'Urgent' for r in rr))
# no online sales in window, by brand
sold = {k for k, (a, b) in agg.items() if a + b > 0}
dead = collections.defaultdict(lambda: [0, 0, 0])
for k, s in stock.items():
    if k in sold or s.get('missing') or s['total'] <= 0: continue
    x = dead[s['brand']]; x[0] += 1; x[1] += s['total']; x[2] += s['eco']
dl = sorted(dead.items(), key=lambda x: -x[1][1])
json.dump(dl, open('dead.json', 'w'))
print('no online sales 11-24 Oct: SKUs', sum(v[0] for _, v in dl), 'units', sum(v[1] for _, v in dl), 'ECO', sum(v[2] for _, v in dl))
print(dl[:12])
