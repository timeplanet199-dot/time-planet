import pandas as pd, datetime as dt
from xw import write, F, col
from tt import parse
A=pd.read_pickle('all_live.pkl')
T,_=parse(); TP=T[(T.room=='TIME PLANET')&(T.date<=dt.date(2026,10,28))]
V=lambda x: x.v if isinstance(x,F) else x
REASONS=['no timetable before 11 Oct','outside shift times','after midnight, no shift','shift empty in timetable','account not in timetable','other live account (not TIME PLANET room)']
HOSTS=sorted(set(TP.host)|set(A.loc[A.host!='','host']))
A['hostcol']=A.host.where(A.host!='','('+A.match.str.replace('Not assigned: ','')+')')

def total_row(rows,skip=()):
    first,last=2,len(rows); tot=['TOTAL']
    for i in range(1,len(rows[0])):
        if i in skip: tot.append(''); continue
        vals=[V(x[i]) for x in rows[1:] if i<len(x)]
        nums=[v for v in vals if isinstance(v,(int,float))]
        tot.append(F(f'SUM({col(i)}{first}:{col(i)}{last})',sum(nums)) if nums else '')
    return tot

def groups(df):
    out=[(h,df[df.host==h],True) for h in HOSTS]
    out+=[('Not assigned: '+r,df[df.match=='Not assigned: '+r],False) for r in REASONS if (df.match=='Not assigned: '+r).any()]
    return out

# ---------- BPC by host ----------
Bp=A[A.brand=='BPC']
hdr=['Host','Scheduled TIME PLANET shifts 11-28 Oct','Shifts with BPC sales','BPC orders','BPC watches sold','Cancelled / refunded watches','Pending watches (not settled yet)',
     'Paid watches <RM359','Rate (RM)','Subtotal (RM)','Paid watches RM359-449','Rate (RM)','Subtotal (RM)','Paid watches RM450+','Rate (RM)','Subtotal (RM)',
     'Total paid watches','BPC COMMISSION PAID (RM)','of which settled up to 20 Oct','of which settled 21-28 Oct (period 21 Oct-20 Nov)','Pending commission if completed (RM)','Paid + pending (RM)']
bpc=[hdr]
for name,df,is_host in groups(Bp):
    p=df[df.state=='Paid']; u={r:int(p.loc[p.rate==r,'pay_units'].sum()) for r in (5,8,20)}
    tot=u[5]*5+u[8]*8+u[20]*20; pc=int(df.pending_comm.sum()); R=len(bpc)+1; c=lambda i:f'{col(i)}{R}'
    bpc.append([name,int((TP.host==name).sum()) if is_host else '',df.groupby(['session_date','slot']).ngroups if is_host else '',df['Order ID'].nunique(),int(df.units.sum()),int(df.ref_units.sum()),int(df.pending_units.sum()),
        u[5],5,F(f'{c(7)}*{c(8)}',u[5]*5),u[8],8,F(f'{c(10)}*{c(11)}',u[8]*8),u[20],20,F(f'{c(13)}*{c(14)}',u[20]*20),
        F(f'{c(7)}+{c(10)}+{c(13)}',sum(u.values())),F(f'{c(9)}+{c(12)}+{c(15)}',tot),
        int(p.loc[p.settled<=pd.Timestamp('2026-10-20'),'commission'].sum()),int(p.loc[p.settled>=pd.Timestamp('2026-10-21'),'commission'].sum()),pc,F(f'{c(17)}+{c(20)}',tot+pc)])
bpc.append(total_row(bpc,skip=(8,11,14)))
bpc+=[[],['Subtotal = paid watches x rate. Price band uses TikTok Income "Total Revenue" (price after seller discount, before platform voucher): below RM359 = RM5, RM359-449.99 = RM8, RM450+ = RM20.'],
      ['Paid = settled in the TikTok Income report with Total Revenue > 0, returned watches removed. Pending = shipped/delivered, not settled yet.']]

# ---------- Bonia by host ----------
bpc_paid=A[(A.brand=='BPC')&(A.host!='')&(A.state=='Paid')].groupby(['host','period']).pay_units.sum()
Bo=A[A.brand=='Bonia']
bh=['Host','Commission period (settled date)','Paid BPC watches in this period (unlock count)','Short of 80 (RM2 tier)','Short of 150 (RM4 tier)','Bonia rate unlocked (RM/watch)',
    'Bonia orders','Bonia watches sold','Cancelled / refunded watches','Paid Bonia watches','BONIA COMMISSION PAID (RM)']
bon=[bh]
def bonia_row(name,per,df,is_host):
    n=int(bpc_paid.get((name,per),0)) if is_host else ''
    R=len(bon)+1; c=lambda i:f'{col(i)}{R}'
    rate=(4 if n>=150 else 2 if n>=80 else 0) if is_host else 0
    paid=int(df[df.state=='Paid'].pay_units.sum())
    bon.append([name,per,n,F(f'MAX(0,80-{c(2)})',max(0,80-n)) if is_host else '',F(f'MAX(0,150-{c(2)})',max(0,150-n)) if is_host else '',
                F(f'IF({c(2)}>=150,4,IF({c(2)}>=80,2,0))',rate) if is_host else 0,
                df['Order ID'].nunique(),int(df.units.sum()),int(df.ref_units.sum()),paid,F(f'{c(9)}*{c(5)}',paid*rate)])
for name,df,is_host in groups(Bo):
    pdf=df[df.state=='Paid']
    pers=sorted(set(pdf.period))
    if is_host:
        pers=sorted(set(pers)|{p for (h,p) in bpc_paid.index if h==name})
        for per in pers:
            bonia_row(name,per,pdf[pdf.period==per],True)
        rest=df[df.state!='Paid']
        if len(rest):
            R=len(bon)+1
            bon.append([name,'Not settled / cancelled (no commission yet)','','','','',rest['Order ID'].nunique(),int(rest.units.sum()),int(rest.ref_units.sum()),0,0])
        if not len(df) and not pers:
            bon.append([name,'(no Bonia live sales)','','','','',0,0,0,0,0])
    else:
        bonia_row(name,'all',df,False)
bon.append(total_row(bon,skip=(1,2,3,4,5)))
bon+=[[],['Rule (Incentive SOP, Brand B: Bonia Performance Unlocking Tier): base rate RM0 (answer to Q3). If the host sells 80+ Bilano Polo watches in the month, every Bonia watch that month pays RM2; 150+ pays RM4 (retroactive).'],
      ['"Month" is taken as the commission period 21st-20th by settled date (rule Q21), and the unlock count uses PAID BPC watches only (completed orders, rule Q14). The SOP says "calendar month"; tell me if it should be 1st-end instead.'],
      ['Hosts are only known from 11 Oct, so the 21 Sep-20 Oct counts are partial for every host. No host reaches 80 in either period, so the Bonia rate is RM0 for all.'],
      ['Not assigned rows have no host, so no unlock tier can apply (rate 0).']]

# ---------- Ladoun by host ----------
Ld=A[A.brand=='Ladoun']
lh=['Host','Ladoun orders','Ladoun watches sold','Cancelled / refunded watches','Pending watches','Paid Ladoun watches','Rate (RM)','LADOUN COMMISSION PAID (RM)']
lad=[lh]
for name,df,is_host in groups(Ld) if len(Ld) else [(h,Ld,True) for h in HOSTS]:
    R=len(lad)+1; c=lambda i:f'{col(i)}{R}'; paid=int(df.pay_units.sum())
    lad.append([name,df['Order ID'].nunique(),int(df.units.sum()),int(df.ref_units.sum()),int(df.pending_units.sum()),paid,2,F(f'{c(5)}*{c(6)}',paid*2)])
lad.append(total_row(lad,skip=(6,)))
lad+=[[],['Rule: flat RM2 per Ladoun watch sold in a live (your instruction, same as Q7).'],
      ['No Ladoun orders exist in the Time Planet TikTok shop export (0 rows in Sept-Oct). Ladoun lives run on the Time Zone TikTok shop (Q23), and the LADOUN WATCHES room in the timetable is empty for Oct-Nov.'],
      ['To fill this tab: the Time Zone TikTok order export + Income report for the same months, and the Ladoun room timetable.']]

# ---------- Host commission (all brands) ----------
def paid_comm(df): return int(df.commission.sum())
sm=[['Host','BPC commission paid (RM)','Bonia commission paid (RM)','Ladoun commission paid (RM)','TOTAL COMMISSION PAID (RM)','BPC pending (RM)','Ladoun pending (RM)','Bonia pending (RM)','Total pending if completed (RM)','Paid + pending (RM)']]
for name,_,is_host in groups(A):
    df=A[A.host==name] if is_host else A[A.match==name]
    b,bo,l=[paid_comm(df[df.brand==x]) for x in ('BPC','Bonia','Ladoun')]
    pb,pl,pbo=[int(df[df.brand==x].pending_comm.sum()) for x in ('BPC','Ladoun','Bonia')]
    R=len(sm)+1; c=lambda i:f'{col(i)}{R}'
    sm.append([name,b,bo,l,F(f'{c(1)}+{c(2)}+{c(3)}',b+bo+l),pb,pl,pbo,F(f'{c(5)}+{c(6)}+{c(7)}',pb+pl+pbo),F(f'{c(4)}+{c(8)}',b+bo+l+pb+pl+pbo)])
sm.append(total_row(sm))
sm+=[[],['Details: see tabs "BPC by host", "Bonia by host" and "Ladoun by host". Orders: TikTok LIVE orders of the Time Planet shop, 1 Sep - 28 Oct 2026.'],
     ['Hosts come from the Live Host Timetable (TIME PLANET room), which starts 11 Oct 2026. Sales that could not be matched to a host are listed as "Not assigned" with the reason.'],
     ['Not included: live session fee (RM10/session), TX commission, returns after payment (deducted next month, rule Q12).']]

# ---------- Sessions ----------
def pu(b): return lambda x:x[A.loc[x.index,'brand']==b].sum()
g=A.groupby(['session_date','Creator Handle','slot','hostcol'])
s=g.agg(bpc_w=('units',pu('BPC')),bpc_p=('pay_units',pu('BPC')),bpc_c=('commission',pu('BPC')),bpc_pc=('pending_comm',pu('BPC')),
        bo_w=('units',pu('Bonia')),bo_p=('pay_units',pu('Bonia')),bo_c=('commission',pu('Bonia')),
        ld_w=('units',pu('Ladoun')),ld_p=('pay_units',pu('Ladoun')),ld_c=('commission',pu('Ladoun'))).reset_index()
s['k']=s.slot.str[:2].replace({'Ou':'99','00':'98'}); s=s.sort_values(['session_date','Creator Handle','k'])
sh=['Session date','Live account','Shift','Host (from Live Host Timetable)','BPC watches sold','BPC paid watches','BPC commission paid (RM)','BPC pending (RM)','Bonia watches sold','Bonia paid watches','Bonia commission paid (RM)','Ladoun watches sold','Ladoun paid watches','Ladoun commission paid (RM)','Total commission paid (RM)']
srows=[sh]
for _,x in s.iterrows():
    R=len(srows)+1
    srows.append([x.session_date.strftime('%Y-%m-%d'),x['Creator Handle'],x.slot,x.hostcol,int(x.bpc_w),int(x.bpc_p),int(x.bpc_c),int(x.bpc_pc),int(x.bo_w),int(x.bo_p),int(x.bo_c),int(x.ld_w),int(x.ld_p),int(x.ld_c),F(f'G{R}+K{R}+N{R}',int(x.bpc_c+x.bo_c+x.ld_c))])
srows.append(total_row(srows,skip=(1,2,3)))

# ---------- Period summary ----------
per=A[A.state=='Paid'].groupby(['period','brand','who']).agg(w=('pay_units','sum'),c=('commission','sum')).reset_index()
prow=[['Commission period (settled date)','Brand','Host','Paid watches','Commission (RM)','Note']]+[[x.period,x.brand,x.who,int(x.w),int(x.c),'Partial: data starts 1 Sep' if x.period.startswith('2026-08') else ('Partial: data ends 28 Oct' if x.period.startswith('2026-10-21') else 'Complete period')] for _,x in per.iterrows()]

# ---------- Order detail ----------
A=A.sort_values('created')
dh=['Order ID','Created time','Session date','Shift','Live account','Host','Host match','Brand','Seller SKU','Product name','Qty','Qty returned','Unit price after seller discount (RM)','Band / tier','Rate (RM/watch)','TikTok order status','TikTok substatus','Settled date','Order Total Revenue in Income report (RM)','Result','Paid watches','Commission (RM)','Pending commission (RM)','Commission period by settled date (21st-20th)']
drows=[dh]+[[x['Order ID'],x.created.strftime('%Y-%m-%d %H:%M:%S'),x.session_date.strftime('%Y-%m-%d'),x.slot,x['Creator Handle'],x.host,x.match,x.brand,x['Seller SKU'],x['Product Name'],int(x.Quantity),int(x['Sku Quantity of return']),float(x.unit_price),x.band,int(x.rate),x['Order Status'],x['Order Substatus'],'' if pd.isna(x.settled) else x.settled.strftime('%Y-%m-%d'),'' if pd.isna(x.TR) else float(x.TR),x.state,int(x.pay_units),int(x.commission),int(x.pending_comm),x.period] for _,x in A.iterrows()]

notes=[['Live host commission (BPC, Bonia, Ladoun): how this was calculated'],[''],
['Data used'],
['  TikTok order export Sept + Oct 2026 (sept/oct 2026 tiktok order.csv), Time Planet shop: orders created 1 Sep to 28 Oct 2026 (last order 28 Oct 18:41).'],
['  TikTok Income report Sept + Oct 2026 (sept/oct 2026 tiktok transaction.xlsx, sheet Order details): Total Revenue and settled date per order.'],
['  Live Host Timetable Time Planet (1).xlsx, TIME PLANET room. Tab names say OCT/NOV 2025, but the date cells are 1 Oct 2026 / 1 Nov 2026 and the weekdays match 2026, so it is read as 11 Oct - 30 Nov 2026.'],[''],
['Which orders count'],
['  Order Channel = LIVE (placed in the live room, rule Q8). Brand from product name: "Bilano" = BPC (Seller SKU PC-), "Bonia" = Bonia (Seller SKU BNB), "Ladoun" = Ladoun (none found).'],[''],
['Matching orders to hosts'],
['  Live account timeplanet = TIME PLANET room (rule Q23). Order created time must fall inside a shift: 07:00-10:00, 11:00-14:00, 14:00-17:00, 18:00-21:00, 21:00-24:00.'],
['  The last shift is written "9:00 pm, 12:00 pm"; read as ending at midnight.'],
['  Husna has an extra row with no times on Fri/Sat nights (16, 17, 23, 24, 30, 31 Oct). Read as after midnight: orders 00:00-05:00 the next morning go to Husna.'],
['  Not assigned: orders before 11 Oct, orders between shifts, accounts not in the timetable (timeplanetsunway, timeplanetofficial), affiliate creators going live with our products, and empty shifts.'],[''],
['Rates'],
['  BPC: price band on Total Revenue basis (after seller discount, before platform voucher). Below RM359 = RM5, RM359-449.99 = RM8 (Q1), RM450+ = RM20.'],
['  Bonia: RM0 base (Q3). Unlocks RM2 (80+ paid BPC watches) or RM4 (150+) for all Bonia watches of that host in the same period. Period = 21st-20th by settled date.'],
['  Ladoun: flat RM2 per watch sold in a live.'],[''],
['Result per order'],
['  Paid: settled with Total Revenue > 0. Commission = (Qty - Qty returned) x rate.'],
['  Refunded/Cancelled or Cancelled: no commission. Pending: shipped/delivered, not settled yet; becomes payable when it settles.'],
['  Not included: live session fee (RM10/session), TX commission, returns after payment (deducted next month, rule Q12).'],
]
write('Live_host_commission_Sep-Oct2026.xlsx',[
    ('Host commission',sm,[44,14,14,14,16,12,12,12,16,14]),
    ('BPC by host',bpc,[44,14,11,9,10,12,12,11,7,10,12,7,10,11,7,10,10,16,18,22,16,12]),
    ('Bonia by host',bon,[44,30,16,12,12,14,10,12,14,12,16]),
    ('Ladoun by host',lad,[44,10,12,14,10,12,9,16]),
    ('Sessions',srows,[12,18,28,36,10,10,12,10,10,10,12,10,10,12,14]),
    ('Period summary',prow,[28,8,44,12,15,26]),
    ('Order detail',drows,[20,19,12,28,16,10,44,8,16,60,6,8,14,11,9,13,16,12,16,18,9,11,12,28]),
    ('Notes',notes,[150])])
for t,rows in [('SUMMARY',sm),('BONIA',bon)]:
    print('==',t)
    for x in rows: print([V(v) for v in x][:11])
