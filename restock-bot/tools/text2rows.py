# Turns the Google Drive connector's text version of a BigSeller Sales Report
# (read_file_content) back into rows. The text has no line breaks: rows of 22
# comma-separated fields follow each other, each ending with the Image URL and
# a space. Usage: python3 text2rows.py <saved read_file_content .txt> -> JSON rows on stdout
import json, re, sys
NCOL = 22

def rows(text):
    t = re.sub(r'\\(.)', r'\1', text)               # undo markdown escapes (\_ \[ \])
    t = re.sub(r'^\S+ (?=Sales Report)', '', t)      # sheet name prefix, e.g. "sheet1 "
    out, row, i, n = [], [], 0, len(t)
    while i < n:
        last = len(row) == NCOL - 1
        if t[i] == '"':                              # quoted field, "" is a quote
            j, buf = i + 1, []
            while True:
                k = t.index('"', j)
                buf.append(t[j:k])
                if k + 1 < n and t[k + 1] == '"': buf.append('"'); j = k + 2
                else: i = k + 1; break
            f = ''.join(buf)
        elif last and t.startswith('Image URL', i) and not out[1:]:   # header's last column has a space
            f, i = 'Image URL', i + len('Image URL')
        else:
            stop = re.compile(r'[ ]' if last else r',').search(t, i)
            k = stop.start() if stop else n
            f, i = t[i:k], k
        row.append(f)
        if last:
            out.append(row); row = []
            if i < n and t[i] == ' ': i += 1
        else:
            if i < n and t[i] != ',': raise ValueError('bad field end at %d: %r' % (i, t[i:i + 40]))
            i += 1
    if row: out.append(row + [''] * (NCOL - len(row)))
    if len(out) < 2 or out[0][0] != 'Sales Report' or out[1][-1] != 'Image URL':
        raise ValueError('not a BigSeller Sales Report text')
    return out

if __name__ == '__main__':
    print(json.dumps(rows(json.load(open(sys.argv[1]))['fileContent'])))
