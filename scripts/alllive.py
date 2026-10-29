import pandas as pd, datetime as dt
from load import orders, txns
from tt import parse

T,_=parse()
TP=T[T.room=='TIME PLANET']
TT_START=dt.date(2026,10,11)
SLOTS=[(7,10),(11,14),(14,17),(18,21),(21,24)]
HOUSE={'timeplanet','timeplanetsunway','timeplanetofficial'}

def brand(name):
    n=name.lower()
    if 'bilano' in n: return 'BPC'
    if 'bonia' in n: return 'Bonia'
    if 'ladoun' in n: return 'Ladoun'
    return None

def period(s):
    if pd.isna(s): return ''
    a=s.replace(day=21) if s.day>=21 else (s.replace(day=1)-pd.Timedelta(days=1)).replace(day=21)
    b=(a+pd.Timedelta(days=32)).replace(day=20)
    return f"{a:%Y-%m-%d} to {b:%Y-%m-%d}"

def assign(ts,acct):
    h=ts.hour; d=ts.date()
    slot=next(((d,a,b) for a,b in SLOTS if a<=h<b),None)
    late=False
    if slot is None and h<5:
        slot=(d-dt.timedelta(days=1),24,None); late=True
    if slot is None:
        return d,f'Outside timetable shifts ({h:02d}:xx)','','Not assigned: outside shift times'
    sd,a,b=slot
    sl='00:00-05:00 (after midnight)' if late else f'{a:02d}:00-{b%24:02d}:00'
    if acct!='timeplanet':
        why='other live account (not TIME PLANET room)' if acct not in HOUSE else 'account not in timetable'
        return sd,sl,'','Not assigned: '+why
    if sd<TT_START:
        return sd,sl,'','Not assigned: no timetable before 11 Oct'
    if late:
        m=TP[(TP.date==sd)&TP.start.isna()]
        if len(m): return sd,sl,m.host.iloc[0],'Assigned (Fri/Sat extra row, times not written)'
        return sd,sl,'','Not assigned: after midnight, no shift'
    m=TP[(TP.date==sd)&(TP.start==dt.time(a,0))]
    if len(m): return sd,sl,m.host.iloc[0],'Assigned'
    return sd,sl,'','Not assigned: shift empty in timetable'

def build():
    d=orders(); t=txns()
    o=t[t['Transaction type']=='Order'].copy()
    o['settled']=pd.to_datetime(o['Order settled time'],format='%Y/%m/%d')
    d=d.join(o.groupby('Order/Adjustment ID').agg(TR=('Total Revenue','sum'),settled=('settled','max')),on='Order ID')
    d['brand']=d['Product Name'].apply(brand)
    A=d[(d['Order Channel']=='LIVE')&d.brand.notna()].copy()
    A[['session_date','slot','host','match']]=pd.DataFrame([assign(ts,ac) for ts,ac in zip(A.created,A['Creator Handle'].fillna(''))],index=A.index)
    A['units']=A['Quantity']
    A['line_TR']=A['SKU Subtotal Before Discount']-A['SKU Seller Discount']
    A['unit_price']=A.line_TR/A.Quantity
    def state(r):
        if pd.isna(r.TR): return 'Cancelled' if r['Order Status'] in ('Cancelled','Unpaid') else 'Pending'
        return 'Paid' if r.TR>0.01 else 'Refunded/Cancelled'
    A['state']=A.apply(state,axis=1)
    A['pay_units']=(A.Quantity-A['Sku Quantity of return']).clip(lower=0).where(A.state=='Paid',0)
    A['pending_units']=A.Quantity.where(A.state=='Pending',0)
    A['ref_units']=A.Quantity.where(A.state.isin(['Refunded/Cancelled','Cancelled']),0)
    A['period']=A.settled.apply(period)
    A['who']=A.host.where(A.host!='',A.match)
    # BPC: fixed price bands
    bp=A.brand=='BPC'
    A['band']=''
    A.loc[bp,'band']=A.loc[bp,'unit_price'].apply(lambda p:'<RM359' if p<359 else ('RM359-449' if p<450 else 'RM450+'))
    A['rate']=0.0
    A.loc[bp,'rate']=A.loc[bp,'band'].map({'<RM359':5,'RM359-449':8,'RM450+':20})
    A.loc[A.brand=='Ladoun','rate']=2
    A.loc[A.brand=='Ladoun','band']='flat'
    # Bonia: rate unlocked by the host's paid BPC watches in the same commission period
    bpc_paid=A[bp&(A.host!='')].groupby(['host','period']).pay_units.sum()
    def bonia_rate(r):
        if r.host=='': return 0
        n=bpc_paid.get((r.host,r.period),0)
        return 4 if n>=150 else (2 if n>=80 else 0)
    bo=A.brand=='Bonia'
    A.loc[bo,'rate']=A[bo].apply(bonia_rate,axis=1)
    A.loc[bo,'band']='unlock tier'
    A['commission']=A.pay_units*A.rate
    # pending: BPC/Ladoun at their rate; Bonia at the tier the host has unlocked so far
    A['pending_comm']=A.pending_units*A.rate
    return A,bpc_paid

if __name__=='__main__':
    A,bp=build()
    A.to_pickle('all_live.pkl')
    print(A.brand.value_counts()); print(pd.crosstab(A.match,A.brand))
    print(bp)
    print(A.groupby(['brand','who'])[['units','pay_units','commission']].sum())
