import pandas as pd, datetime as dt
from xw import write, F, col
from tt import parse
B=pd.read_pickle('bpc_host.pkl')
T,_=parse(); TP=T[(T.room=='TIME PLANET')&(T.date<=dt.date(2026,10,28))]
B['band']=B.rate.map({5:'<RM359',8:'RM359-449',20:'RM450+'})
B['ref_units']=B['Quantity'].where(B.state.isin(['Refunded/Cancelled','Cancelled']),0)
B['paid_TR']=B.line_TR.where(B.state=='Paid',0)
B['who']=B.host.where(B.host!='','Not assigned')
B['hostcol']=B.host.where(B.host!='','(' + B.match.str.replace('Not assigned: ','') + ')')
V=lambda x: x.v if isinstance(x,F) else x

# ---------- Host commission ----------
def grp(df):
    p=df[df.state=='Paid']
    u={r:int(p.loc[p.rate==r,'pay_units'].sum()) for r in (5,8,20)}
    s1=int(p.loc[p.settled<=pd.Timestamp('2026-10-20'),'commission'].sum())
    s2=int(p.loc[p.settled>=pd.Timestamp('2026-10-21'),'commission'].sum())
    return dict(orders=df['Order ID'].nunique(),sold=int(df.units.sum()),canc=int(df.ref_units.sum()),pend=int(df.pending_units.sum()),
                u=u,s1=s1,s2=s2,pc=int(df.pending_comm.sum()),shifts=df.groupby(['session_date','slot']).ngroups)
hdr=['Host','Scheduled TIME PLANET shifts 11-28 Oct','Shifts with BPC sales','BPC orders','BPC watches sold','Cancelled / refunded watches','Pending watches (not settled yet)',
     'Paid watches <RM359','Rate (RM)','Subtotal (RM)','Paid watches RM359-449','Rate (RM)','Subtotal (RM)','Paid watches RM450+','Rate (RM)','Subtotal (RM)',
     'Total paid watches','TOTAL COMMISSION PAID (RM)','of which settled up to 20 Oct','of which settled 21-28 Oct (period 21 Oct-20 Nov)','Pending commission if completed (RM)','Paid + pending (RM)']
order=[(h,B[B.host==h],int((TP.host==h).sum()),True) for h in sorted(B.loc[B.host!='','host'].unique())]
for h in sorted(set(TP.host)-set(B.host)):
    order.append((h,B.iloc[0:0],int((TP.host==h).sum()),True))
for reason in ['no timetable before 11 Oct','outside shift times','account not in timetable','shift empty in timetable']:
    sub=B[B.match=='Not assigned: '+reason]
    if len(sub): order.append(('Not assigned: '+reason,sub,'',False))
rows=[hdr]
for k,(name,df,sch,is_host) in enumerate(order):
    g=grp(df); R=k+2; c=lambda i:f'{col(i)}{R}'
    tot=g['u'][5]*5+g['u'][8]*8+g['u'][20]*20
    rows.append([name,sch,g['shifts'] if is_host else '',g['orders'],g['sold'],g['canc'],g['pend'],
        g['u'][5],5,F(f'{c(7)}*{c(8)}',g['u'][5]*5),g['u'][8],8,F(f'{c(10)}*{c(11)}',g['u'][8]*8),g['u'][20],20,F(f'{c(13)}*{c(14)}',g['u'][20]*20),
        F(f'{c(7)}+{c(10)}+{c(13)}',sum(g['u'].values())),F(f'{c(9)}+{c(12)}+{c(15)}',tot),g['s1'],g['s2'],g['pc'],F(f'{c(17)}+{c(20)}',tot+g['pc'])])
first,last=2,len(rows)
tot=['TOTAL']
for i in range(1,len(hdr)):
    if i in (8,11,14): tot.append(''); continue
    v=sum(V(x[i]) for x in rows[1:] if isinstance(V(x[i]),(int,float)))
    tot.append(F(f'SUM({col(i)}{first}:{col(i)}{last})',v))
rows.append(tot)
rows+=[[],['How to read: Subtotal = paid watches x rate. Total commission = sum of the three subtotals. Price band uses TikTok Income "Total Revenue" (price after seller discount, before platform voucher).'],
 ['Paid = settled in the TikTok Income report with Total Revenue > 0, returned watches removed. Pending = shipped/delivered but not settled yet; it becomes payable when it settles.'],
 ['Hosts are matched only from 11 Oct 2026 (first date in the Live Host Timetable). Rows "Not assigned" show the BPC live sales that no host could be matched to, and why.'],
 ['Only BPC (Bilano Polo) watches sold in TikTok LIVE orders of the Time Planet shop. Live session fee (RM10/session) is NOT included.']]
host_tab=rows

# ---------- Sessions ----------
g=B.groupby(['session_date','Creator Handle','slot','hostcol'])
s=g.agg(orders=('Order ID','nunique'),units=('units','sum'),paid=('pay_units','sum'),
        u5=('pay_units',lambda x:x[B.loc[x.index,'rate']==5].sum()),u8=('pay_units',lambda x:x[B.loc[x.index,'rate']==8].sum()),u20=('pay_units',lambda x:x[B.loc[x.index,'rate']==20].sum()),
        comm=('commission','sum'),pu=('pending_units','sum'),pc=('pending_comm','sum'),cu=('ref_units','sum'),tr=('line_TR','sum'),ptr=('paid_TR','sum')).reset_index()
s['k']=s.slot.str[:2].replace({'Ou':'99','00':'98'})
s=s.sort_values(['session_date','Creator Handle','k'])
sh=['Session date','Live account','Shift','Host (from Live Host Timetable)','BPC orders','BPC watches','Paid watches','  @RM5 (<RM359)','  @RM8 (RM359-449)','  @RM20 (RM450+)','Commission paid (RM)','Pending watches','Pending commission if completed (RM)','Cancelled/refunded watches','BPC live sales, all statuses (RM, Total Revenue basis)','BPC sales paid (RM, Total Revenue)']
srows=[sh]+[[x.session_date.strftime('%Y-%m-%d'),x['Creator Handle'],x.slot,x.hostcol,int(x.orders),int(x.units),int(x.paid),int(x.u5),int(x.u8),int(x.u20),int(x.comm),int(x.pu),int(x.pc),int(x.cu),float(x.tr),float(x.ptr)] for _,x in s.iterrows()]
srows.append(['TOTAL','','','',int(s.orders.sum()),int(s.units.sum()),int(s.paid.sum()),int(s.u5.sum()),int(s.u8.sum()),int(s.u20.sum()),int(s.comm.sum()),int(s.pu.sum()),int(s.pc.sum()),int(s.cu.sum()),float(s.tr.sum()),float(s.ptr.sum())])

# ---------- Period summary ----------
per=B[B.state=='Paid'].groupby(['period','who']).agg(w=('pay_units','sum'),c=('commission','sum')).reset_index()
prow=[['Commission period (settled date)','Host','Paid watches','Commission (RM)','Note']]+[[x.period,x.who,int(x.w),int(x.c),'Partial: data starts 1 Sep' if x.period.startswith('2026-08') else ('Partial: data ends 28 Oct' if x.period.startswith('2026-10-21') else 'Complete period')] for _,x in per.iterrows()]

# ---------- Order detail ----------
B=B.sort_values('created')
dh=['Order ID','Created time','Session date','Shift','Live account','Host','Host match','Seller SKU','Product name','Qty','Qty returned','Unit price after seller discount (RM)','Price band','Rate (RM/watch)','TikTok order status','TikTok substatus','Settled date','Order Total Revenue in Income report (RM)','Result','Paid watches','Commission (RM)','Pending commission (RM)','Commission period by settled date (21st-20th)']
drows=[dh]+[[x['Order ID'],x.created.strftime('%Y-%m-%d %H:%M:%S'),x.session_date.strftime('%Y-%m-%d'),x.slot,x['Creator Handle'],x.host,x.match,x['Seller SKU'],x['Product Name'],int(x.Quantity),int(x['Sku Quantity of return']),float(x.unit_price),x.band,int(x.rate),x['Order Status'],x['Order Substatus'],'' if pd.isna(x.settled) else x.settled.strftime('%Y-%m-%d'),'' if pd.isna(x.TR) else float(x.TR),x.state,int(x.pay_units),int(x.commission),int(x.pending_comm),x.period] for _,x in B.iterrows()]

notes=[['BPC live host commission: how this was calculated'],[''],
['Data used'],
['  TikTok order export Sept + Oct 2026 (sept/oct 2026 tiktok order.csv): orders created 1 Sep to 28 Oct 2026 (last order 28 Oct 18:41).'],
['  TikTok Income report Sept + Oct 2026 (sept/oct 2026 tiktok transaction.xlsx, sheet Order details): Total Revenue and settled date per order.'],
['  Live Host Timetable Time Planet (1).xlsx, TIME PLANET room. Tab names say OCT/NOV 2025, but the date cells are 1 Oct 2026 / 1 Nov 2026 and the weekdays match 2026 (11 Oct 2026 = Sunday), so it is read as 11 Oct - 30 Nov 2026.'],[''],
['Which orders count'],
['  Order Channel = LIVE (placed in the live room, rule Q8) and product name contains "Bilano" (Seller SKU PC-).'],[''],
['Matching orders to hosts'],
['  Live account timeplanet = TIME PLANET room (rule Q23). The order created time must fall inside a shift: 07:00-10:00, 11:00-14:00, 14:00-17:00, 18:00-21:00, 21:00-24:00.'],
['  The last shift is written "9:00 pm, 12:00 pm"; read as ending at midnight.'],
['  Husna has an extra row with no times on Fri/Sat nights (16, 17, 23, 24, 30, 31 Oct). Read as after midnight: orders 00:00-05:00 the next morning go to Husna. 2 BPC orders were matched this way.'],
['  Not assigned: orders before 11 Oct (no timetable), orders between shifts (e.g. 10:00-10:59, 17:00-17:59), live accounts not in the timetable (timeplanetsunway, timeplanetofficial), and shifts left empty in the timetable.'],[''],
['Price band = Total Revenue basis'],
['  Income report Total Revenue = Subtotal after seller discounts + refund (it does not subtract the platform voucher).'],
['  Per item: (SKU Subtotal Before Discount - SKU Seller Discount) / Qty. Summed per order, this matched the Income report exactly on all 5,406 orders found in both files.'],
['  Rates: below RM359 = RM5, RM359-449.99 = RM8 (answer to Q1), RM450+ = RM20 (Incentive SOP).'],[''],
['Result per order'],
['  Paid: settled with Total Revenue > 0. Commission = (Qty - Qty returned) x rate.'],
['  Refunded/Cancelled: settled with Total Revenue 0. Cancelled: cancelled/unpaid, never settled. No commission for either.'],
['  Pending: shipped / delivered but not settled yet. Becomes payable when it settles.'],
['  Commission period uses the settled date as the completion date (rule Q10), periods 21st-20th (rule Q21).'],
['  Not included: live session fee (RM10/session), Bonia/TX/Ladoun commission, returns after payment (deducted next month, rule Q12).'],
]
write('BPC_live_commission_Sep-Oct2026_hosts.xlsx',[
    ('Host commission',host_tab,[40,14,11,9,10,12,12,11,7,10,12,7,10,11,7,10,10,16,22,22,16,12]),
    ('Sessions',srows,[12,18,28,36,10,11,11,13,15,14,14,12,16,14,20,18]),
    ('Period summary',prow,[30,40,13,15,26]),
    ('Order detail',drows,[20,19,12,28,16,10,44,16,60,6,8,14,11,9,13,16,12,16,18,9,11,12,28]),
    ('Notes',notes,[150])])
for x in host_tab[:len(order)+2]:
    print([V(v) for v in x])
