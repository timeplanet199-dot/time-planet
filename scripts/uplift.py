import json,datetime as dt,statistics as st
R=json.load(open('weeks.json'))
for r in R: r['A']=dt.date.fromisoformat(r['a']); r['B']=dt.date.fromisoformat(r['b'])
def days(r): return [r['A']+dt.timedelta(i) for i in range(r['days'])]
def is_dd(d): return d.month==d.day
def clean(r): return r['days']>=5 and not any(is_dd(d) or d.day>=25 for d in days(r))
camps=[dt.date(2025,11,11),dt.date(2025,12,12)]+[dt.date(2026,m,m) for m in range(1,11)]
out={}
for plat in ['TikTok','Shopee']:
    P=sorted([r for r in R if r['plat']==plat and r['days']>1],key=lambda r:r['A'])
    print('==',plat)
    for c in camps:
        w=[r for r in P if r['A']<=c<=r['B']]
        if not w: continue
        w=w[0]
        prev=[r for r in P if r['B']<w['A'] and clean(r)][-2:]
        nxt=[r for r in P if r['A']>w['B'] and clean(r)][:2]
        bl=prev+nxt
        for key in ['vo','bon']:
            bases=[r[key]/r['days'] for r in bl]
            if len(bases)<2: continue
            b=st.median(bases)
            E=(w[key]-w['days']*b)/b
            lo=(w[key]-w['days']*max(bases))/max(bases); hi=(w[key]-w['days']*min(bases))/min(bases)
            out.setdefault((plat,key),[]).append((c,E,lo,hi))
            print(f"{c} {key:3} week {w['a']}..{w['b']} ({w['days']}d) total={w[key]:5.0f} base/day={b:6.1f} [{min(bases):.1f}-{max(bases):.1f}] n={len(bases)} extra_days={E:5.1f} range[{lo:5.1f},{hi:5.1f}]")
print('== Bonia, TikTok+Shopee combined: extra units / combined base per day')
import statistics as st
vals=[]
for (c,Et,lt,ht),(c2,Es,ls,hs) in zip(out[('TikTok','bon')],out[('Shopee','bon')]):
    assert c==c2
    # recover bases from printed logic
    pass
