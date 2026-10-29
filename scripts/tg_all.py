import json, collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

bon = json.load(open('restock28.json'))
allp = json.load(open('allplan.json'))
NAMES = {'BONI': 'Bonia', 'BPC': 'Bilano Polo', 'CASI': 'Casio', 'CASG': 'G-Shock', 'CASB': 'Baby-G', 'FOSS': 'Fossil',
         'SEIK': 'Seiko', 'TECH': 'Techmarine', 'SMAR': 'TX smart', 'SKEC': 'Skechers'}
items = [dict(code=r['sku'], brand='BONI', pri=r['priority'], eco=r['eco'], daily=r['daily'], xfer=r['transfer'],
              order=r['order'], over=r['action'].startswith(('Clear', 'Overstocked'))) for r in bon]
items += [dict(code=r['code'], brand=r['brand'], pri=r['pri'], eco=r['eco'], daily=r['daily'], xfer=r['xfer'],
               order=r['order'], over=r['action'].startswith('Overstocked')) for r in allp]
agg = collections.OrderedDict((b, [0, 0, 0, 0, 0]) for b in NAMES)
for it in items:
    a = agg[it['brand']]; a[0] += 1; a[1] += it['pri'] == 'Urgent'; a[2] += it['order']; a[3] += it['xfer']; a[4] += it['over']
lead = {'BPC': 75}
brows = [[NAMES[b], v[0], v[1], int(v[2]), int(v[3]), v[4], lead.get(b, 7)] for b, v in agg.items()]
tot = [sum(r[i] for r in brows) for i in range(1, 6)]
brows.append(['TOTAL'] + tot + [''])
top = sorted([i for i in items if i['order'] > 0 and i['pri'] == 'Urgent'], key=lambda i: -i['order'])[:20]
trows = [[i['code'], NAMES[i['brand']], int(i['eco']), f"{i['daily']:.1f}", int(i['xfer']) or '', int(i['order'])] for i in top]

H = 2.2 + 0.27 * (len(brows) + 1) + 0.9 + 0.27 * (len(trows) + 1) + 1.6
fig = plt.figure(figsize=(10, H), dpi=140); fig.patch.set_facecolor('white')
y = lambda inch: 1 - inch / H
fig.text(0.03, y(0.45), 'Stock restock - all brands, stock 28 Oct 2026', fontsize=16, weight='bold', color='#1F3864')
fig.text(0.03, y(0.85), f'Order {tot[2]:,} from suppliers  |  Move {tot[3]:,} from outlets/HQ to online  |  {tot[1]} SKUs urgent',
         fontsize=11, weight='bold', color='#C00000')


def draw(top_in, rows, hdr, widths, title):
    fig.text(0.03, y(top_in), title, fontsize=11.5, weight='bold', color='#1F3864')
    h = 0.27 * (len(rows) + 1)
    ax = fig.add_axes([0.03, y(top_in + 0.15 + h), 0.94, h / H]); ax.axis('off')
    t = ax.table(cellText=rows, colLabels=hdr, colWidths=widths, loc='upper left', cellLoc='center', bbox=[0, 0, 1, 1])
    t.auto_set_font_size(False); t.set_fontsize(9)
    for (i, j), c in t.get_celld().items():
        c.set_edgecolor('#BFBFBF')
        if i == 0:
            c.set_facecolor('#1F3864'); c.get_text().set_color('white'); c.get_text().set_weight('bold')
        else:
            c.set_facecolor('#F2F5FA' if i % 2 == 0 else 'white')
            if rows[i - 1][0] == 'TOTAL':
                c.set_facecolor('#DDE7F3'); c.get_text().set_weight('bold')
    return top_in + 0.15 + h


nxt = draw(1.35, brows, ['Brand', 'SKUs', 'Urgent', 'Order', 'Move to online', 'Overstocked', 'Lead time (days)'],
           [0.2, 0.1, 0.1, 0.12, 0.16, 0.14, 0.18], 'By brand')
for (i, j), c in fig.axes[-1].tables[0].get_celld().items():
    if i > 0 and j in (3,): c.get_text().set_weight('bold')
nxt = draw(nxt + 0.45, trows, ['SKU', 'Brand', 'Online now', 'Sells/day', 'Move', 'Order'],
           [0.28, 0.18, 0.13, 0.13, 0.12, 0.12], 'Top 20 urgent orders')
for (i, j), c in fig.axes[-1].tables[0].get_celld().items():
    if i > 0 and j == 5: c.get_text().set_weight('bold'); c.set_facecolor('#F4CCCC')
notes = ['Check first: 1) stock already on order is NOT counted. 2) BPC needs ~82 days of cover (75-day delivery).',
         '3) Online sales only (11-24 Oct). 4) Ladoun LA-7225 sells 3.4/day with 0 online stock: move LD-L7225RG from HQ.',
         '5) No unit cost for brands other than Bonia.   Full workings: Google Sheet link in caption.']
for k, n in enumerate(notes):
    fig.text(0.03, y(nxt + 0.45 + 0.3 * k), n, fontsize=9, color='#404040')
fig.savefig('restock_all_28oct.png', facecolor='white')
print(brows[-1], len(trows))
