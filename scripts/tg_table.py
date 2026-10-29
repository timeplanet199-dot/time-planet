import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

res = json.load(open('restock28.json'))
miss = {r['sku'] for r in res if not r['in_file']}
pri = {'Urgent': 0, 'Soon': 1, 'Later': 2, '': 3}
act = [r for r in res if r['tier'] != 'Stop' and (r['order'] or r['transfer'])]
act.sort(key=lambda r: (pri[r['priority']], -r['daily']))


def reason(r):
    s = 'Out of stock online' if r['eco'] == 0 else f"{int(r['eco'])} left online (~{r['days_left']} days)"
    if r['sku'] in miss:
        s += ' *'
    return s


rows = [[r['priority'], r['sku'], r['tier'].replace('Sold-out best seller', 'Sold-out'), int(r['eco']),
         f"{r['daily']:.1f}", int(r['transfer']) or '', int(r['order']) or '', reason(r)] for r in act]
stop = [r for r in res if r['tier'] == 'Stop']
for r in stop:
    rows.append(['Stop', r['sku'], 'Stop', int(r['eco']), f"{r['daily']:.1f}", '', '',
                 'Clear: discount or bundle' if r['action'].startswith('Clear') else 'Do not reorder'])

hdr = ['Priority', 'SKU', 'Tier', 'Online', 'Sells/day', 'Move', 'Order', 'Reason']
colw = [0.08, 0.16, 0.09, 0.07, 0.08, 0.06, 0.07, 0.30]
fig_h = 1.6 + 0.208 * (len(rows) + 1) + 1.4
fig = plt.figure(figsize=(11, fig_h), dpi=130)
fig.patch.set_facecolor('white')
tot_o = int(sum(r['order'] for r in res)); tot_m = int(sum(r['transfer'] for r in res))
urg = sum(r['priority'] == 'Urgent' for r in res)
fig.text(0.02, 1 - 0.45 / fig_h, 'Bonia restock - stock 28 Oct 2026', fontsize=17, weight='bold', color='#1F3864')
fig.text(0.02, 1 - 0.85 / fig_h, f'Order {tot_o} from Bonia (about RM 206,809 at cost)  |  Move {tot_m} from outlets  |  {urg} of 77 SKUs urgent',
         fontsize=11, color='#C00000', weight='bold')
ax = fig.add_axes([0.02, 1.4 / fig_h, 0.96, 1 - 2.6 / fig_h])
ax.axis('off')
t = ax.table(cellText=rows, colLabels=hdr, colWidths=colw, loc='upper left', cellLoc='left')
t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1, 1.25)
colors = {'Urgent': '#F4CCCC', 'Soon': '#FCE5CD', 'Later': '#FFF2CC', 'Stop': '#D9D9D9'}
for (i, j), c in t.get_celld().items():
    c.set_edgecolor('#BFBFBF')
    if i == 0:
        c.set_facecolor('#1F3864'); c.get_text().set_color('white'); c.get_text().set_weight('bold')
    else:
        p = rows[i - 1][0]
        c.set_facecolor(colors.get(p, 'white') if j == 0 else ('#F7F9FC' if i % 2 == 0 else 'white'))
        if j in (5, 6) and rows[i - 1][j] != '':
            c.get_text().set_weight('bold')
notes = ['Check before ordering: 1) stock already on order is NOT counted - subtract open POs or you buy twice.',
         '2) Sales rate from 11-24 Oct.  * = not in 28/10 stock file, counted as 0.  3) 11.11 not included: order campaign stock by ~4 Nov.',
         '4) 350 other Bonia SKUs (900 units) have no tier and are not checked.   Full workings: see the Google Sheet link.']
for k, n in enumerate(notes):
    fig.text(0.02, (1.1 - 0.32 * k) / fig_h, n, fontsize=9, color='#404040')
fig.savefig('bonia_restock_28oct.png', bbox_inches='tight', facecolor='white')
print(len(rows), 'rows')
