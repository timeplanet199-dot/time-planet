import pandas as pd, datetime as dt
from load import *
d=orders(); t=txns()
o=t[t['Transaction type']=='Order'].copy()
o['settled']=pd.to_datetime(o['Order settled time'],format='%Y/%m/%d')
agg=o.groupby('Order/Adjustment ID').agg(TR=('Total Revenue','sum'),settled=('settled','max'))
d=d.join(agg,on='Order ID')
B=d[(d['Order Channel']=='LIVE')&d.bpc].copy()

def slot(ts):
    h=ts.hour; day=ts.normalize()
    if h<5: return day-pd.Timedelta(days=1),'S5 21:00-24:00+'
    if h<11: return day,'S1 07:00-11:00'
    if h<14: return day,'S2 11:00-14:00'
    if h<18: return day,'S3 14:00-18:00'
    if h<21: return day,'S4 18:00-21:00'
    return day,'S5 21:00-24:00+'
B[['session_date','slot']]=B['created'].apply(lambda x:pd.Series(slot(x)))
B['units']=B['Quantity']
B['line_TR']=B['SKU Subtotal Before Discount']-B['SKU Seller Discount']
B['unit_price']=B['line_TR']/B['Quantity']
def rate(p): return 5 if p<359 else (8 if p<450 else 20)
B['rate']=B['unit_price'].apply(rate)
def state(r):
    if pd.isna(r.TR): return 'Cancelled' if r['Order Status'] in ('Cancelled','Unpaid') else 'Pending'
    return 'Paid' if r.TR>0.01 else 'Refunded/Cancelled'
B['state']=B.apply(state,axis=1)
B['pay_units']=(B['Quantity']-B['Sku Quantity of return']).clip(lower=0).where(B.state=='Paid',0)
B['commission']=B.pay_units*B.rate
B['pending_units']=B['Quantity'].where(B.state=='Pending',0)
B['pending_comm']=B.pending_units*B.rate
B['period']=B['settled'].apply(lambda s: '' if pd.isna(s) else (f"{(s.replace(day=1)-pd.Timedelta(days=1)).strftime('%Y-%m') if s.day<=20 else s.strftime('%Y-%m')}-21 to "+ (s.strftime('%Y-%m') if s.day<=20 else (s.replace(day=1)+pd.Timedelta(days=32)).strftime('%Y-%m'))+"-20"))
B.to_pickle('bpc_live.pkl')
if __name__=='__main__':
    print(B.state.value_counts()); print(B.groupby('rate')[['units','pay_units']].sum())
    print(B[B.pay_units<B.units][['Order Status','state','Quantity','Sku Quantity of return','TR']].value_counts().head(10))
    s=B.groupby(['session_date','Creator Handle','slot']).agg(orders=('Order ID','nunique'),units=('units','sum'),paid_units=('pay_units','sum'),TR=('line_TR','sum'),commission=('commission','sum'),pending=('pending_comm','sum')).reset_index()
    print(len(s),'sessions'); print(s.head(12).to_string()); print(s[['units','paid_units','commission','pending']].sum())
    print(B.period.value_counts())
