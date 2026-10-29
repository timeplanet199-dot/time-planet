import pandas as pd
from xl import read
from paths import ORDERS as ORD, TXN
def orders():
    d=pd.concat([pd.read_csv(f,dtype=str) for f in ORD],ignore_index=True)
    d=d.apply(lambda c:c.str.strip())
    for c in ['Quantity','Sku Quantity of return','SKU Unit Original Price','SKU Subtotal Before Discount','SKU Platform Discount','SKU Seller Discount','SKU Subtotal After Discount']:
        d[c]=pd.to_numeric(d[c]).fillna(0)
    d['created']=pd.to_datetime(d['Created Time'],format='%d/%m/%Y %H:%M:%S')
    d['bpc']=d['Product Name'].str.contains('bilano',case=False)
    return d
def txns():
    fr=[]
    for f in TXN:
        rows=read(f)['Order details']; h=rows[0]
        fr.append(pd.DataFrame([r+[None]*(len(h)-len(r)) for r in rows[1:]],columns=[str(x) for x in h]))
    t=pd.concat(fr,ignore_index=True)
    for c in t.columns[5:48]:
        t[c]=pd.to_numeric(t[c],errors='coerce')
    return t
