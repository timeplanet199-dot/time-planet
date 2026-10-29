import zipfile,re,sys
import xml.etree.ElementTree as ET
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def colidx(ref):
    c=re.match(r'[A-Z]+',ref).group(); n=0
    for ch in c: n=n*26+ord(ch)-64
    return n-1
def read(path):
    z=zipfile.ZipFile(path)
    ss=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS):
            ss.append(''.join(t.text or '' for t in si.iter('{%s}t'%NS['m'])))
    wbx=ET.fromstring(z.read('xl/workbook.xml'))
    names=[s.get('name') for s in wbx.find('m:sheets',NS)]
    out={}
    sheets=sorted([n for n in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml',n)],key=lambda s:int(re.findall(r'\d+',s)[0]))
    for nm,sp in zip(names,sheets):
        rows=[]
        for r in ET.fromstring(z.read(sp)).iter('{%s}row'%NS['m']):
            row={}
            for c in r.findall('m:c',NS):
                v=c.find('m:v',NS); t=c.get('t')
                if t=='inlineStr':
                    val=''.join(x.text or '' for x in c.iter('{%s}t'%NS['m']))
                elif v is None: continue
                elif t=='s': val=ss[int(v.text)]
                else:
                    val=v.text
                    try: val=float(val)
                    except: pass
                row[colidx(c.get('r'))]=val
            if row:
                m=max(row); rows.append([row.get(i) for i in range(m+1)])
        out[nm]=rows
    return out
if __name__=='__main__':
    d=read(sys.argv[1])
    for k,v in d.items():
        print('##',k,len(v))
        for r in v[:int(sys.argv[2]) if len(sys.argv)>2 else 6]: print(r)
