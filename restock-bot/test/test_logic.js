// Compares the Apps Script restock logic (Logic.gs) with the Python scripts.
// Usage: python3 restock-bot/test/make_fixtures.py <dir> && node restock-bot/test/test_logic.js <dir>
const fs = require('fs'), path = require('path'), vm = require('vm');
const dir = process.argv[2], here = path.join(__dirname, '..');
const ctx = vm.createContext({console});
vm.runInContext(fs.readFileSync(path.join(here, 'Data.gs'), 'utf8') + '\n' +
  fs.readFileSync(path.join(here, 'Logic.gs'), 'utf8'), ctx);
const L = (expr) => vm.runInContext(expr, ctx);
const fx = JSON.parse(fs.readFileSync(path.join(dir, 'fixtures.json'), 'utf8'));
ctx.fx = fx;
let bad = 0;
const check = (name, a, b) => { if (JSON.stringify(a) !== JSON.stringify(b)) { bad++; if (bad <= 15) console.log('MISMATCH', name, a, b); } };

// 1) Bonia 77 vs restock.py (stock 28 Oct, Monitor sales)
const py77 = JSON.parse(fs.readFileSync(path.join(dir, 'restock28.json'), 'utf8'));
const plan1 = L(`buildPlan(fx.stock, fx.bonia.map(parseSales), dayNum('2026-10-24'))`);
const js77 = new Map(plan1.rows.map(r => [r.code, r]));
py77.forEach(p => {
  const j = js77.get(p.sku);
  check(p.sku, [j.status, j.pri, j.order, j.xfer, j.action, j.missing],
               [p.status, p.priority, p.order, p.transfer, p.action, !p.in_file]);
});
console.log('Bonia 77 checked:', py77.length, '| order Python', py77.reduce((t, p) => t + p.order, 0),
  'JS', [...js77.values()].reduce((t, r) => t + r.order, 0));

// 2) other brands vs allbrand.py + allplan.py (synthetic sales, 2 weeks x 2 platforms)
const pyAll = JSON.parse(fs.readFileSync(path.join(dir, 'allplan.json'), 'utf8'));
const pyAgg = JSON.parse(fs.readFileSync(path.join(dir, 'allbrand.json'), 'utf8'));
const plan2 = L(`buildPlan(fx.stock, fx.other.map(parseSales), dayNum('2026-10-24'))`);
const b77 = new Set(L('BONIA_TIERS').map(t => t[0]));
const jsOther = new Map(plan2.rows.filter(r => !(r.brand === 'BONI' && b77.has(r.code))).map(r => [r.code, r]));
check('row count', jsOther.size, pyAll.length);
pyAll.forEach(p => {
  const j = jsOther.get(p.code);
  if (!j) { bad++; console.log('missing in JS', p.code); return; }
  check(p.code, [j.line, j.status, j.left, j.pri, j.target, j.xfer, j.order, +j.daily.toFixed(9)],
                [p.line, p.status, p.left, p.pri, p.target, p.xfer, p.order, +p.daily.toFixed(9)]);
});
const pyTotal = Object.values(pyAgg.agg).reduce((t, v) => t + v[0] + v[1], 0);
check('matched units', plan2.matched, pyTotal);
check('unmatched', plan2.unmatched.length, pyAgg.unmatched.length);
console.log('Other brands checked:', pyAll.length, 'rows | matched units', plan2.matched, '/', plan2.units);

// 3) choosing sales files: weekly preferred, no double counting, gaps and future weeks
const day = (s) => L(`dayNum('${s}')`);
const f = (plat, a, b, qty) => ({plat, a: day(a), b: day(b), q: new Map([['X', qty]])});
const sr = L('salesRates')([
  f('TikTok', '2026-10-18', '2026-10-24', 70),   // weekly, taken
  f('TikTok', '2026-10-20', '2026-10-20', 99),   // daily inside the weekly: skipped
  f('TikTok', '2026-10-25', '2026-10-25', 5),    // daily after it: taken
  f('TikTok', '2026-10-25', '2026-10-31', 999),  // week ending after the window: ignored
  f('TikTok', '2026-10-01', '2026-10-07', 70),   // partly before the 24-day window (3-26 Oct): 5 of 7 days
  f('Shopee', '2026-10-26', '2026-10-26', 3)], day('2026-10-26'));
check('u14 TikTok', sr.u14.TikTok.get('X'), 75);
check('cov14', [sr.cov14.TikTok, sr.cov14.Shopee], [8, 1]);
check('u24 TikTok pro rata', sr.u24.TikTok.get('X'), 125);
check('cov24 TikTok', sr.cov24.TikTok, 13);
check('rate mixed coverage', L('rate')({TikTok: 75, Shopee: 3}, sr.cov14), 75 / 8 + 3);
console.log('Sales file selection checked');

// 4) the message renders and fits Telegram
const msg = L(`formatReport(buildPlan(fx.stock, fx.bonia.map(parseSales).concat(fx.other.map(parseSales)), dayNum('2026-10-24')),
  {today: dayNum('2026-10-25'), stockTitle: 'TPSB 28/10', stockDay: dayNum('2026-10-28'), sheetUrl: 'https://example.com'})`);
console.log('message length', msg.length);
fs.writeFileSync(path.join(dir, 'message.html'), msg);
console.log(bad ? `FAILED: ${bad} mismatches` : 'ALL MATCH');
process.exit(bad ? 1 : 0);
