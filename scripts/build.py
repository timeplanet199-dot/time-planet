import pandas as pd
from xw import write
B=pd.read_pickle('bpc_live.pkl')
B['band']=B.rate.map({5:'<RM359',8:'RM359-449',20:'RM450+'})
B['ref_units']=B['Quantity'].where(B.state.isin(['Refunded/Cancelled','Cancelled']),0)
B['paid_TR']=B.line_TR.where(B.state=='Paid',0)
g=B.groupby(['session_date','Creator Handle','slot'])
s=g.agg(orders=('Order ID','nunique'),units=('units','sum'),paid=('pay_units','sum'),
        u5=('pay_units',lambda x:x[B.loc[x.index,'rate']==5].sum()),u8=('pay_units',lambda x:x[B.loc[x.index,'rate']==8].sum()),u20=('pay_units',lambda x:x[B.loc[x.index,'rate']==20].sum()),
        comm=('commission','sum'),pu=('pending_units','sum'),pc=('pending_comm','sum'),cu=('ref_units','sum'),tr=('line_TR','sum'),ptr=('paid_TR','sum')).reset_index()
hdr=['Session date','Live account','Time slot (assumed)','Host (fill from timetable)','BPC orders','BPC watches','Paid watches','  @RM5 (<RM359)','  @RM8 (RM359-449)','  @RM20 (RM450+)','Commission paid (RM)','Pending watches','Pending commission if completed (RM)','Cancelled/refunded watches','BPC live sales, all statuses (RM, Total Revenue basis)','BPC sales paid (RM, Total Revenue)']
rows=[hdr]+[[r.session_date.strftime('%Y-%m-%d'),r['Creator Handle'],r.slot,('',3),int(r.orders),int(r.units),int(r.paid),int(r.u5),int(r.u8),int(r.u20),int(r.comm),int(r.pu),int(r.pc),int(r.cu),float(r.tr),float(r.ptr)] for _,r in s.iterrows()]
rows.append(['TOTAL','','','',int(s.orders.sum()),int(s.units.sum()),int(s.paid.sum()),int(s.u5.sum()),int(s.u8.sum()),int(s.u20.sum()),int(s.comm.sum()),int(s.pu.sum()),int(s.pc.sum()),int(s.cu.sum()),float(s.tr.sum()),float(s.ptr.sum())])
B=B.sort_values('created')
dh=['Order ID','Created time','Session date','Time slot (assumed)','Live account','Seller SKU','Product name','Qty','Qty returned','Unit price after seller discount (RM)','Price band','Rate (RM/watch)','TikTok order status','TikTok substatus','Settled date','Order Total Revenue in Income report (RM)','Result','Paid watches','Commission (RM)','Pending commission (RM)','Commission period by settled date (21st-20th)']
drows=[dh]+[[r['Order ID'],r.created.strftime('%Y-%m-%d %H:%M:%S'),r.session_date.strftime('%Y-%m-%d'),r.slot,r['Creator Handle'],r['Seller SKU'],r['Product Name'],int(r.Quantity),int(r['Sku Quantity of return']),float(r.unit_price),r.band,int(r.rate),r['Order Status'],r['Order Substatus'],'' if pd.isna(r.settled) else r.settled.strftime('%Y-%m-%d'),'' if pd.isna(r.TR) else float(r.TR),r.state,int(r.pay_units),int(r.commission),int(r.pending_comm),r.period] for _,r in B.iterrows()]
per=B[B.state=='Paid'].groupby(['period','Creator Handle']).agg(watches=('pay_units','sum'),comm=('commission','sum')).reset_index()
prow=[['Commission period (settled date)','Live account','Paid watches','Commission (RM)','Note']]+[[r.period,r['Creator Handle'],int(r.watches),int(r.comm),'Partial: data starts 1 Sep' if r.period.startswith('2026-08') else ('Partial: data ends 28 Oct' if r.period.startswith('2026-10-21') else 'Complete period')] for _,r in per.iterrows()]
notes=[['BPC live host commission: how this was calculated'],[''],
['Data used'],
['  TikTok order export Sept + Oct 2026 (sept 2026 tiktok order.csv, oct 2026 tiktok order.csv): 8,101 item rows, orders created 1 Sep to 28 Oct 2026.'],
['  TikTok Income report Sept + Oct 2026 (sept/oct 2026 tiktok transaction.xlsx, sheet Order details): Total Revenue and settled date per order.'],[''],
['Which orders count'],
['  Order Channel = LIVE in the TikTok order export (orders placed in the live room, rule Q8). The Creator Handle column gives the live account.'],
['  Product name contains "Bilano" (all have Seller SKU starting PC-). Excluded: free-gift Polo bracelets (not for sale) and 1 row "Polo Smart Watch PC-S13B" (not sold in a live, and unclear whether it is BPC).'],[''],
['Price band = Total Revenue basis'],
['  Checked: Income report Total Revenue = Subtotal after seller discounts + refund. It does not subtract the platform voucher.'],
['  Per item: (SKU Subtotal Before Discount - SKU Seller Discount) / Qty from the order export. Summed per order, this matched the Income report exactly on all 5,406 orders found in both files.'],
['  Rates: below RM359 = RM5, RM359-449.99 = RM8 (your answer to Q1), RM450+ = RM20 (Incentive SOP).'],[''],
['Result per order'],
['  Paid: settled in the Income report with Total Revenue > 0. Commission = (Qty - Qty returned) x rate.'],
['  Refunded/Cancelled: settled with Total Revenue 0 (refunded after payment, incl. 4 orders marked Completed then fully returned). No commission.'],
['  Cancelled: cancelled or unpaid, not in the Income report. No commission.'],
['  Pending: shipped / in transit / delivered but not yet settled. Shown separately; becomes payable once settled.'],[''],
['Assumptions to replace (low confidence)'],
['  Time slots are my guess, based on the Oct 2025 Live Host Timetable (7-10am, 11am-2pm, 2-5pm, 6-9pm, 9pm-12am). TikTok exports have no session ID.'],
['  Orders 00:00-04:59 are counted in the previous day\'s night slot. Orders 10:xx and 17:xx are put in the earlier slot.'],
['  Host names are blank: the timetable on Drive only covers Oct-Nov 2025. With the Sept-Oct 2026 timetable the Host column can be filled and the slots corrected.'],
['  BigSeller: the files in big seller data are summary Sales Reports with no order IDs, so status comes from TikTok\'s own order export + Income report instead.'],
['  Commission period uses the Income report settled date as the completion date (rule Q10), with periods 21st-20th (rule Q21).'],
]
write('BPC_live_commission_Sep-Oct2026.xlsx',[('Sessions',rows,[12,18,18,22,10,11,11,13,15,14,14,12,16,14,20,18]),('Period summary',prow,[30,18,13,15,26]),('Order detail',drows,[20,19,12,18,18,16,60,6,8,14,11,9,13,16,12,16,18,9,11,12,28]),('Notes',notes,[140])])
print(len(s),'sessions',s.comm.sum(),s.pc.sum()); print(per.to_string())
print(s.groupby('Creator Handle')[['units','paid','comm','pc']].sum())
