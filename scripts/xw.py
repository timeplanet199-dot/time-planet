import zipfile
from xml.sax.saxutils import escape
class F:
    def __init__(s,f,v): s.f=f; s.v=v
def col(i):
    s=''
    i+=1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s
def cell(r,c,v,style=0):
    ref=f'{col(c)}{r+1}'
    if isinstance(v,F): return f'<c r="{ref}" s="{style}"><f>{escape(v.f)}</f><v>{v.v}</v></c>'
    if v is None or v=='' : return ''
    if isinstance(v,bool): v=str(v)
    if isinstance(v,(int,float)):
        if v!=v: return ''
        return f'<c r="{ref}" s="{style}"><v>{v}</v></c>'
    return f'<c r="{ref}" t="inlineStr" s="{style}"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'
def write(path,sheets):
    """sheets: list of (name, rows, widths)"""
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    n=len(sheets)
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'+''.join(f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(n))+'</Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    z.writestr('xl/workbook.xml','<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{escape(s[0])}" sheetId="{i+1}" r:id="rId{i+1}"/>' for i,s in enumerate(sheets))+'</sheets></workbook>')
    z.writestr('xl/_rels/workbook.xml.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i+1}.xml"/>' for i in range(n))+f'<Relationship Id="rId{n+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    z.writestr('xl/styles.xml','<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00"/></numFmts><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="4"><xf/><xf fontId="1" applyFont="1"/><xf numFmtId="164" applyNumberFormat="1"/><xf fillId="2" applyFill="1"/></cellXfs></styleSheet>')
    for i,(name,rows,widths) in enumerate(sheets):
        cols='<cols>'+''.join(f'<col min="{j+1}" max="{j+1}" width="{w}" customWidth="1"/>' for j,w in enumerate(widths))+'</cols>' if widths else ''
        body=''.join(f'<row r="{r+1}">'+''.join(cell(r,c,v if not isinstance(v,tuple) else v[0], 1 if r==0 and name!='Notes' else (v[1] if isinstance(v,tuple) else (2 if isinstance(v,float) else 0))) for c,v in enumerate(row))+'</row>' for r,row in enumerate(rows))
        z.writestr(f'xl/worksheets/sheet{i+1}.xml',f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>{cols}<sheetData>{body}</sheetData></worksheet>')
    z.close()
