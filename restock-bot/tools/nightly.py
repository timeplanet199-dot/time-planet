# Nightly restock report for the Time Planet Operation group, run by the
# scheduled Claude session (see restock-bot/README.md, "Nightly Claude run").
# Inputs are the Google Drive connector outputs that were saved to files:
#   --stock   download_file_content of the newest TPSB file (JSON with base64 content)
#   --sales   read_file_content of BigSeller Sales Report files (JSON with fileContent)
# The Stock manager bot token comes from the environment variable TG_TOKEN.
# Usage: python3 restock-bot/tools/nightly.py --stock F --stock-title "TPSB 29/10.xlsx" --sales F1 F2 ... [--skipped "..."] [--send]
import argparse, base64, datetime, json, os, re, subprocess, sys, tempfile, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, os.path.join(ROOT, 'scripts')]
from text2rows import rows as text_rows
from xl import read

GROUP = '-5365161027'   # Time Planet Operation
SHEET = 'https://docs.google.com/spreadsheets/d/1cc-NC3740UwtJ3JnrOHYe94p09382vAZrUvkxTIs3-w/edit'
MYT = datetime.timezone(datetime.timedelta(hours=8))

def disp(rs):
    return [[('' if v is None else (str(int(v)) if isinstance(v, float) and v == int(v) else str(v))) for v in r] for r in rs]

def title_day(title, today):
    m = re.search(r'(\d{1,2})[/\-.](\d{1,2})', title)
    d = datetime.date(today.year, int(m.group(2)), int(m.group(1)))
    return d if d <= today + datetime.timedelta(days=1) else d.replace(year=today.year - 1)

def send(token, text):
    while text:
        cut = len(text) if len(text) <= 4000 else text.rindex('\n', 0, 4000)
        data = urllib.parse.urlencode({'chat_id': GROUP, 'text': text[:cut], 'parse_mode': 'HTML',
                                       'disable_web_page_preview': 'true'}).encode()
        r = json.load(urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', data=data, timeout=30))
        if not r.get('ok'): raise RuntimeError('Telegram: %s' % r.get('description'))
        print('sent message', r['result']['message_id'])
        text = text[cut:].lstrip('\n')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stock', required=True); ap.add_argument('--stock-title', required=True)
    ap.add_argument('--sales', nargs='*', default=[]); ap.add_argument('--skipped', default='')
    ap.add_argument('--today'); ap.add_argument('--send', action='store_true')
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.datetime.now(MYT).date()

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        f.write(base64.b64decode(json.load(open(a.stock))['content']))
    stock = disp(list(read(f.name).values())[0])
    files, bad = [], []
    for p in a.sales:
        d = json.load(open(p))
        try: files.append(text_rows(d['fileContent']))
        except Exception as e: bad.append('%s (%s)' % (d.get('title', p), e))
    inp = {'stock': stock, 'files': files, 'end': str(today - datetime.timedelta(days=1)), 'today': str(today),
           'stockTitle': re.sub(r'\.xlsx$', '', a.stock_title, flags=re.I), 'stockDay': str(title_day(a.stock_title, today)),
           'sheetUrl': SHEET}
    res = json.loads(subprocess.run(['node', os.path.join(HERE, 'report.js')], input=json.dumps(inp),
                                    capture_output=True, text=True, check=True).stdout)
    html = res['html']
    skipped = [s for s in [a.skipped] + bad if s]
    if skipped:
        html += '\nSales files not loaded today: ' + '; '.join(skipped).replace('&', '&amp;').replace('<', '&lt;')
    print(json.dumps(res['summary']))
    print(html)
    if a.send:
        token = os.environ.get('TG_TOKEN')
        if not token: raise SystemExit('TG_TOKEN is not set')
        send(token, html)

if __name__ == '__main__':
    main()
