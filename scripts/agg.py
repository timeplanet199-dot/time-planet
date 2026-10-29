import glob,re,json,datetime as dt,collections
from xl import read
import os
from paths import SALES_DIR
recs=[]
for f in glob.glob(os.path.join(SALES_DIR,"*.xlsx")):
    try: d=read(f)
    except Exception as e: continue
    rows=list(d.values())[0]
    if not rows or rows[0][0]!='Sales Report': continue
    ds=re.findall(r'\d{4}-\d{2}-\d{2}',str(rows[0][1])); ds=ds if len(ds)==2 else ds*2
    a,b=[dt.date.fromisoformat(x) for x in ds]
    h=rows[1]; ix={k:h.index(k) for k in ['BigSeller Store Name','Valid Orders','Valid Product Sales Quantity','Valid Product Sales','Total Orders','SKU Name','Product Name']}
    stores=collections.Counter(); vo=vq=vs=to=0; bon=0
    for r in rows[2:]:
        r=r+[None]*(len(h)-len(r))
        s=r[ix['BigSeller Store Name']]
        if not s: continue
        stores[s]+=1
        v=float(r[ix['Valid Orders']] or 0); vo+=v
        q=float(r[ix['Valid Product Sales Quantity']] or 0); vq+=q
        vs+=float(str(r[ix['Valid Product Sales']] or 0).replace(',',''))
        to+=float(r[ix['Total Orders']] or 0)
        if 'BONIA' in str(r[ix['Product Name']]).upper() or str(r[ix['SKU Name']]).startswith('BN'): bon+=q
    plat='TikTok' if any('iktok' in s.lower() for s in stores) else 'Shopee' if any('hopee' in s.lower() for s in stores) else ','.join(stores)
    recs.append(dict(f=f[-12:],plat=plat,a=str(a),b=str(b),days=(b-a).days+1,vo=vo,vq=vq,vs=round(vs),to=to,bon=bon,stores=sorted(stores)))
json.dump(recs,open('weeks.json','w'),indent=0)
recs.sort(key=lambda r:(r['plat'],r['a']))
seen=set()
for r in recs:
    k=(r['plat'],r['a'],r['b']); dup='DUP' if k in seen else ''; seen.add(k)
    print(f"{r['plat']:7}{r['a']}..{r['b']} {r['days']}d orders={r['vo']:6.0f} perday={r['vo']/r['days']:6.1f} qty={r['vq']:6.0f} bonia={r['bon']:4.0f} RM{r['vs']:>8} {dup}")
