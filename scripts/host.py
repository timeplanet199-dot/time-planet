import pandas as pd, datetime as dt
from tt import parse
T,_=parse()
TP=T[T.room=='TIME PLANET'].copy()
B=pd.read_pickle('bpc_live.pkl')
TT_START=dt.date(2026,10,11)
SLOTS=[(7,10),(11,14),(14,17),(18,21),(21,24)]
def lab(a,b): return f'{a:02d}:00-{b%24:02d}:00'
def assign(r):
    ts=r.created; acct=r['Creator Handle']; h=ts.hour
    d=ts.date(); slot=None
    for a,b in SLOTS:
        if a<=h<b: slot=(d,a,b)
    late=False
    if slot is None and h<5:
        slot=(d-dt.timedelta(days=1),24,None); late=True
    if slot is None:
        return pd.Series([d,'Outside timetable shifts ('+f'{h:02d}:xx)','','Not assigned: outside shift times'])
    sd,a,b=slot
    sl='00:00-05:00 (after midnight)' if late else lab(a,b)
    if acct!='timeplanet':
        return pd.Series([sd,sl,'','Not assigned: account not in timetable'])
    if sd<TT_START:
        return pd.Series([sd,sl,'','Not assigned: no timetable before 11 Oct'])
    if late:
        m=TP[(TP.date==sd)&TP.start.isna()]
        if len(m): return pd.Series([sd,sl,m.host.iloc[0],'Assigned (Fri/Sat extra row, times not written)'])
        return pd.Series([sd,sl,'','Not assigned: after midnight, no shift'])
    m=TP[(TP.date==sd)&(TP.start==dt.time(a,0))]
    if len(m): return pd.Series([sd,sl,m.host.iloc[0],'Assigned'])
    return pd.Series([sd,sl,'','Not assigned: shift empty in timetable'])
B[['session_date','slot','host','match']]=B.apply(assign,axis=1)
B.to_pickle('bpc_host.pkl')
if __name__=='__main__':
    print(B.match.value_counts())
    x=B[B.session_date>=TT_START]
    print(x.match.value_counts()); print(x.groupby('host')[['units','pay_units','commission','pending_comm']].sum())
    print(x[x.match.str.startswith('Not')][['created','Creator Handle','slot','match']].to_string())
