// Renders the restock report image (PNG) from summarize() output on stdin.
// Usage: node render.js <out.png> < summary.json
// Light theme, Inter, status colours from the dataviz palette (critical / serious /
// warning), each with an icon or label so colour never carries meaning alone.
const fs = require('fs');
const {chromium} = require('playwright');

const S = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = process.argv[2];
const esc = (x) => String(x).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const n = (x) => Math.round(x).toLocaleString('en-US');
const compact = (x) => x >= 1e6 ? (x / 1e6).toFixed(1) + 'M' : x >= 1e4 ? Math.round(x / 1e3) + 'k' : n(x);
const day = new Date(S.date + 'T00:00:00Z').toLocaleDateString('en-GB', {weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'});
const cov = Object.keys(S.cov14).sort().map((p) => `${p} ${S.cov14[p]}/14 days`).join(' · ');

const status = (a) => a.eco <= 0 ? '<span class="pill crit">● Out</span>'
  : a.left < 1 ? '<span class="pill ser">▲ Under 1 day</span>'
  : a.left <= 3 ? `<span class="pill ser">▲ ${a.left} day${a.left === 1 ? '' : 's'}</span>` : `${a.left} days`;
const top = S.actions.slice(0, 12);
const rows = top.map((a) => `<tr>
  <td class="sku">${esc(a.code)}${a.missing ? '<sup>*</sup>' : ''}<div class="brand">${esc(a.brand)}</div></td>
  <td class="num">${n(a.eco)}</td><td class="num">${a.daily.toFixed(1)}</td><td>${status(a)}</td>
  <td class="num">${a.move ? n(a.move) : '<span class="dash">–</span>'}</td>
  <td class="num strong">${a.order ? n(a.order) : '<span class="dash">–</span>'}</td></tr>`).join('');
const brands = S.brands.slice(0, 7);
const rest = S.brands.slice(7);
if (rest.length) brands.push({name: `Others (${rest.length})`, order: rest.reduce((t, b) => t + b.order, 0),
  move: rest.reduce((t, b) => t + b.move, 0), urgent: rest.reduce((t, b) => t + b.urgent, 0)});
const brandRows = brands.map((b) => `<tr><td>${esc(b.name)}</td><td class="num strong">${n(b.order)}</td>
  <td class="num">${n(b.move)}</td><td class="num">${b.urgent}</td></tr>`).join('');
const icon = {critical: '<span class="ico crit">●</span>', serious: '<span class="ico ser">▲</span>', info: '<span class="ico info">◆</span>'};
const attention = S.attention.map((a) => `<li>${icon[a.level] || ''}<span>${esc(a.text)}</span></li>`).join('');
const warnings = S.warnings.length ? `<div class="warn"><div class="wt">⚠ Data check</div><ul>${S.warnings.map((w) => `<li>${esc(w)}</li>`).join('')}</ul></div>` : '';

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
:root{--surface:#fcfcfb;--plane:#f4f3ef;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;
  --crit:#d03b3b;--ser:#ec835a;--warn:#fab219;--accent:#2a78d6}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--plane);font-family:Inter,sans-serif;color:var(--ink);width:760px;padding:20px}
.card{background:var(--surface);border:1px solid rgba(11,11,11,.08);border-radius:14px;padding:22px 24px;margin-bottom:14px}
h1{font-size:24px;font-weight:700;letter-spacing:-.01em}
.sub{color:var(--ink2);font-size:13.5px;margin-top:4px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:18px}
.tile{border:1px solid var(--grid);border-radius:10px;padding:12px 14px}
.tile .l{font-size:12.5px;color:var(--ink2)}
.tile .v{font-size:30px;font-weight:650;margin-top:2px;letter-spacing:-.02em}
.tile .s{font-size:12px;color:var(--muted);margin-top:2px}
.tile.crit{border-color:rgba(208,59,59,.35);background:rgba(208,59,59,.05)}
h2{font-size:15px;font-weight:650;margin-bottom:10px}
ul{list-style:none}
.att li{display:flex;gap:10px;font-size:14.5px;line-height:1.45;padding:6px 0}
.att li+li{border-top:1px solid var(--grid)}
.ico{flex:none;font-size:12px;line-height:21px}
.ico.crit{color:var(--crit)}.ico.ser{color:var(--ser)}.ico.info{color:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{text-align:left;font-size:11.5px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;
  padding:0 8px 8px;border-bottom:1px solid var(--grid)}
th.num,td.num{text-align:right;font-variant-numeric:tabular-nums}
td{padding:8px;border-bottom:1px solid var(--grid);vertical-align:middle}
tr:last-child td{border-bottom:none}
td.sku{font-weight:600;font-size:13.5px}
.brand{font-weight:400;font-size:11.5px;color:var(--muted);margin-top:1px}
.strong{font-weight:650}
.dash{color:var(--muted)}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:2px 8px;border-radius:999px;white-space:nowrap}
.pill.crit{color:#fff;background:var(--crit)}
.pill.ser{color:var(--ink);background:rgba(236,131,90,.28)}
.more{font-size:12.5px;color:var(--muted);margin-top:10px}
.warn{background:rgba(250,178,25,.14);border:1px solid rgba(250,178,25,.55);border-radius:10px;padding:12px 14px}
.warn .wt{font-weight:650;font-size:13.5px;margin-bottom:4px}
.warn li{font-size:13px;line-height:1.45;color:var(--ink);padding:2px 0}
.foot{font-size:11.5px;color:var(--muted);line-height:1.5;padding:0 4px}
</style></head><body>
<div class="card">
  <h1>Restock report · ${esc(day)}</h1>
  <div class="sub">Stock ${esc(S.stockTitle)} · Online sales ${esc(S.salesFrom)}–${esc(S.salesTo)} (${esc(cov)})</div>
  <div class="tiles">
    <div class="tile crit"><div class="l">Urgent SKUs</div><div class="v">${n(S.totals.urgent)}</div><div class="s">${n(S.totals.out)} out of stock online</div></div>
    <div class="tile"><div class="l">Move to online</div><div class="v">${n(S.totals.move)}</div><div class="s">units from outlets/HQ</div></div>
    <div class="tile"><div class="l">Order from suppliers</div><div class="v">${n(S.totals.order)}</div><div class="s">${S.totals.cost ? 'Bonia ≈ RM ' + compact(S.totals.cost) + ' at cost' : 'units'}</div></div>
  </div>
</div>
${attention ? `<div class="card att"><h2>What needs your attention</h2><ul>${attention}</ul></div>` : ''}
<div class="card">
  <h2>Act now: urgent SKUs, fastest sellers first</h2>
  <table><thead><tr><th>SKU</th><th class="num">Online</th><th class="num">Sells/day</th><th>Stock lasts</th><th class="num">Move</th><th class="num">Order</th></tr></thead>
  <tbody>${rows}</tbody></table>
  ${S.actions.length > top.length ? `<div class="more">+ ${S.actions.length - top.length} more urgent SKUs in the Stock Analysis sheet.</div>` : ''}
</div>
<div class="card">
  <h2>By brand</h2>
  <table><thead><tr><th>Brand</th><th class="num">Order</th><th class="num">Move</th><th class="num">Urgent SKUs</th></tr></thead>
  <tbody>${brandRows}</tbody></table>
</div>
${warnings ? `<div class="card" style="padding:14px">${warnings}</div>` : ''}
<div class="foot">Online stock = ECO. Move = outlets/HQ to online, keeping 2 in each source. Order = what is still short after moving.
Not counted: stock already on order (open POs) and outlet walk-in sales.${S.matchedPct !== null ? ` Sales matched to stock codes: ${S.matchedPct}% of units.` : ''}
${S.actions.some((a) => a.missing) ? ' * = not in the stock file, counted as 0.' : ''}</div>
</body></html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({viewport: {width: 800, height: 600}, deviceScaleFactor: 2});
  await page.setContent(html, {waitUntil: 'load'});
  await page.locator('body').screenshot({path: out});
  await browser.close();
  console.log(out);
})();
