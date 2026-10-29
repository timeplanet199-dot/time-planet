import json, math, sys
from xl import read
from paths import STOCK
import csv
ROWS=list(csv.DictReader(open('sheet26.csv',encoding='utf-8')))
KEEP={'Grow':14,'Sold-out best seller':14,'Steady':10,'Cut back':5,'Stop':0}
Z={'Grow':1.04,'Sold-out best seller':1.04,'Steady':0.44,'Cut back':-0.15}
TREND={'Grow':1,'Sold-out best seller':1,'Steady':1,'Cut back':0.8}
LEAD,CYCLE,MINT,LEAVE,OVERW=7,3,2,2,8

def stock28():
    rows=read(STOCK)['Page 1']
    hdr=rows[0]; out={}
    for r in rows[2:]:
        r=list(r)+[None]*13
        code=r[2]
        if not code or code=='Brand Total': continue
        n=lambda i: float(str(r[i]).replace(',','')) if r[i] not in (None,'') else 0
        out[code.strip()]=dict(eco=n(5),outlet=sum(n(i) for i in range(6,12)),hq=n(6),shops=sum(n(i) for i in range(7,12)))
    return hdr,out

def plan(sku,tier,c,d,e,eco,outlet):
    f=sum((c,d,e))/24 if tier=='Sold-out best seller' else (d+e)/14
    g=KEEP[tier]; h=0 if g==0 else max(MINT,math.ceil(round(f*g,9)))
    status='Do not restock' if tier=='Stop' else ('RESTOCK' if eco<=h else 'OK')
    left=math.floor(eco/f) if f else None
    pri='' if status!='RESTOCK' else ('Urgent' if left<=3 else 'Soon' if left<=7 else 'Later')
    C=f*TREND.get(tier,1); D=LEAD+CYCLE; E=C*D
    G=0 if tier=='Stop' else max(0,math.ceil(round(Z[tier]*math.sqrt(E),9)))
    H=0 if tier=='Stop' else math.ceil(round(E+G,9))
    K=max(0,H-eco); M=min(K,max(0,outlet-LEAVE)); N=K-M
    Q=(eco+M+N)/(C*7) if C else None
    if tier=='Stop': act='Clear stock: discount or bundle' if (Q or 0)>OVERW else 'Sell through, do not reorder'
    else: act='Overstocked: skip orders' if (Q or 0)>OVERW else ('Order from supplier' if N>0 else ('Transfer from outlet' if M>0 else 'No action'))
    return dict(sku=sku,tier=tier,daily=f,keep=g,threshold=h,eco=eco,outlet=outlet,status=status,days_left=left,priority=pri,
                cover_sales=E,safety=G,target=H,shortfall=K,transfer=M,order=N,weeks=Q,action=act,c=c,d=d,e=e)

if __name__=='__main__':
    # 1) reproduce the sheet with its own 26 Oct stock
    bad=0
    for s in ROWS:
        p=plan(s['sku'],s['tier'],float(s['c']),float(s['d']),float(s['e']),float(s['eco']),float(s['outlet']))
        want=(s['status'],s['priority'],int(s['order']),int(s['xfer']),s['action'])
        got=(p['status'],p['priority'],p['order'],p['transfer'],p['action'])
        if want!=got: bad+=1; print('MISMATCH',s['sku'],want,got)
    print('rows',len(ROWS),'mismatches',bad)
    # 2) rerun with 28 Oct stock
    hdr,st=stock28()
    print('stock header',hdr)
    res=[]
    for s in ROWS:
        x=st.get(s['sku'],dict(eco=0,outlet=0,hq=0,shops=0))
        p=plan(s['sku'],s['tier'],float(s['c']),float(s['d']),float(s['e']),x['eco'],x['outlet']); p['in_file']=s['sku'] in st
        p['eco26']=float(s['eco']); p['outlet26']=float(s['outlet']); res.append(p)
    json.dump(res,open('restock28.json','w'),indent=0)
    print('in file',sum(r['in_file'] for r in res))
    from collections import Counter
    print(Counter(r['action'] for r in res)); print(Counter(r['priority'] for r in res if r['priority']))
    print('order units',sum(r['order'] for r in res),'transfer units',sum(r['transfer'] for r in res))
    for r in sorted(res,key=lambda r:({'Urgent':0,'Soon':1,'Later':2,'':3}[r['priority']],-r['daily'])):
        if r['action']!='No action': print(f"{r['sku']:16}{r['tier'][:8]:9}{r['daily']:.2f}/d thr{r['threshold']:3} eco{r['eco26']:3.0f}->{r['eco']:3.0f} out{r['outlet']:3.0f} left{r['days_left']} {r['priority']:6} T{r['target']} xfer{r['transfer']} ord{r['order']} {r['action']}")
