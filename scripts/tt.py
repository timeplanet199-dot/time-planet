import datetime as dt, pandas as pd
from xl import read
from paths import TIMETABLE as F
ROOMS={'TIME PLANET','BILANO POLO','TIME PLANET SHOPEE','TIME ZONE MALAYSIA','TIME ZONE GALLERY','TIME PLANET OFFICIAL','LADOUN WATCHES'}
def fx(f): 
    m=round(f*24*60); return dt.time(m//60%24,m%60)
def parse():
    d=read(F); out=[]
    for sh in ['OCT 2025','NOV 2025']:
        rows=d[sh]; base=dt.date(1899,12,30)+dt.timedelta(days=int(rows[0][7]))
        room=None; days=None
        for r in rows:
            r=list(r)+[None]*40
            if isinstance(r[0],str) and r[0].strip() in ROOMS: room=r[0].strip(); days=None; continue
            if r[0] is None and isinstance(r[2],float) and r[1] is None and days is None:
                days={i:int(r[i]) for i in range(2,40) if isinstance(r[i],float)}; continue
            if room and days and (isinstance(r[0],float) or (r[0] is None and r[1] is None and any(isinstance(r[i],str) for i in days))):
                st=fx(r[0]) if isinstance(r[0],float) else None; en=fx(r[1]) if isinstance(r[1],float) else None
                for i,dd in days.items():
                    h=r[i]
                    if isinstance(h,str) and h.strip() and 'off' not in h.lower() and h.strip()!='NO SLOT':
                        try: day=base.replace(day=dd)
                        except ValueError: continue
                        out.append(dict(room=room,date=day,start=st,end=en,host=h.strip().title(),sheet=sh))
    return pd.DataFrame(out),base
if __name__=='__main__':
    t,b=parse()
    print(t.sheet.value_counts()); print(t.groupby(['room','start','end'],dropna=False).size())
    print(t.date.min(),t.date.max()); print(t.host.value_counts())
    tp=t[t.room=='TIME PLANET']; print(tp[tp.start.isna()])
    print(pd.Timestamp(dt.date(2026,10,11)).day_name(), pd.Timestamp(dt.date(2026,11,1)).day_name())
