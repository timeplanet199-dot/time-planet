// Restock calculation. Pure functions: no Drive, Sheets or Telegram calls, so
// test/test_logic.js can run them in Node against the Python scripts.
// Ported from scripts/restock.py (the 77 tiered Bonia SKUs) and scripts/allbrand.py
// + allplan.py (every other SKU), with the overstock rule of the Stock Analysis
// sheet (handover section 6.2).

// Bonia Restock Monitor rules (restock.py)
var KEEP = {'Grow': 14, 'Sold-out best seller': 14, 'Steady': 10, 'Cut back': 5, 'Stop': 0};
var Z = {'Grow': 1.04, 'Sold-out best seller': 1.04, 'Steady': 0.44, 'Cut back': -0.15};
var TREND = {'Cut back': 0.8};
var BONIA_LEAD = 7, BONIA_CYCLE = 3, MIN_LINE = 2, LEAVE = 2, OVER_WEEKS = 8;
// All-brand rules (allplan.py): lead and order cycle in days, others Steady
var LEAD = {'BPC': 75}, CYCLE = {'BONI': 3};
var DEF_LEAD = 7, DEF_CYCLE = 7, DEF_KEEP = 10, DEF_Z = 0.44;
var BRAND_NAMES = {'BONI': 'Bonia', 'BPC': 'Bilano Polo', 'CASI': 'Casio', 'CASG': 'G-Shock', 'CASB': 'Baby-G',
  'FOSS': 'Fossil', 'SEIK': 'Seiko', 'TECH': 'Techmarine', 'SMAR': 'TX smart', 'SKEC': 'Skechers', 'LADO': 'Ladoun'};
var PRI = {'Urgent': 0, 'Soon': 1, 'Later': 2, '': 3};
var DAY = 86400000;

function num(x) {
  if (x === null || x === undefined || x === '') return 0;
  var v = parseFloat(String(x).replace(/,/g, ''));
  return isNaN(v) ? 0 : v;
}
function norm(s) { return String(s).trim().toUpperCase().replace(/-TP$/, '').replace(/\s/g, ''); }
function r9(x) { return Math.round(x * 1e9) / 1e9; }
function ceil9(x) { return Math.ceil(r9(x)); }
// Day number (days since 1970-01-01) from 'YYYY-MM-DD'
function dayNum(s) { var p = s.split('-'); return Date.UTC(+p[0], +p[1] - 1, +p[2]) / DAY; }
function dayStr(n) { return new Date(n * DAY).toISOString().slice(0, 10); }

// TPSB stock file ("Stock Balance Quantity Listing vs Location"), first sheet as rows
function parseStock(rows) {
  var stock = new Map(), brand = null;
  for (var i = 2; i < rows.length; i++) {
    var r = rows[i].slice();
    while (r.length < 13) r.push(null);
    if (r[1]) brand = r[1];
    if (!r[2] || r[2] === 'Brand Total' || brand === 'Grand Total') continue;
    var shops = 0;
    for (var j = 7; j < 12; j++) shops += num(r[j]);
    stock.set(norm(r[2]), {code: String(r[2]).trim(), brand: brand, desc: r[3], eco: num(r[5]), hq: num(r[6]),
      shops: shops, total: num(r[12])});
  }
  return stock;
}

// BigSeller "Sales Report" (daily "Time:YYYY-MM-DD" or weekly "YYYY-MM-DD ~ YYYY-MM-DD"), rows of the first sheet.
// Returns {plat, a, b, q: Map(normalised SKU -> valid quantity)} or null if it is not a sales report.
function parseSales(rows) {
  if (!rows.length || rows[0][0] !== 'Sales Report') return null;
  var ds = String(rows[0][1]).match(/\d{4}-\d{2}-\d{2}/g);
  if (!ds || ds.length > 2) return null;
  var h = rows[1], si = h.indexOf('BigSeller Store Name'), ki = h.indexOf('SKU Name'),
      qi = h.indexOf('Valid Product Sales Quantity');
  if (si < 0 || ki < 0 || qi < 0) return null;
  var plat = 'Shopee', q = new Map();
  for (var i = 2; i < rows.length; i++) {
    var r = rows[i];
    if (String(r[si] || '').toLowerCase().indexOf('iktok') >= 0) plat = 'TikTok';
    if (r[ki]) { var s = norm(r[ki]); q.set(s, (q.get(s) || 0) + num(r[qi])); }
  }
  return {plat: plat, a: dayNum(ds[0]), b: dayNum(ds[ds.length - 1]), q: q};
}

// Online sales over the 24 days ending `end` (a day number), per platform.
// Weekly files are preferred; a file overlapping days already taken is skipped
// (no double counting) and files ending after `end` are ignored. A file only partly
// inside the window counts pro rata by days (an approximation, noted in coverage).
function salesRates(files, end) {
  var start = end - 23, w14 = end - 13, plats = {};
  files.forEach(function (f) { if (f && f.b <= end && f.b >= start) (plats[f.plat] = plats[f.plat] || []).push(f); });
  var out = {u14: {}, u24: {}, cov14: {}, cov24: {}, files: {}};
  Object.keys(plats).forEach(function (p) {
    var fs = plats[p].slice().sort(function (x, y) { return (y.b - y.a) - (x.b - x.a) || x.a - y.a; });
    var taken = {}, u14 = new Map(), u24 = new Map(), n = 0;
    fs.forEach(function (f) {
      var lo = Math.max(f.a, start), d;
      for (d = lo; d <= f.b; d++) if (taken[d]) return;
      for (d = lo; d <= f.b; d++) taken[d] = 1;
      var len = f.b - f.a + 1, n24 = f.b - lo + 1, n14 = Math.max(0, f.b - Math.max(f.a, w14) + 1);
      f.q.forEach(function (qty, s) {
        if (n24) u24.set(s, (u24.get(s) || 0) + (n24 === len ? qty : qty * n24 / len));
        if (n14) u14.set(s, (u14.get(s) || 0) + (n14 === len ? qty : qty * n14 / len));
      });
      n++;
    });
    var c14 = 0, c24 = 0;
    for (var d = start; d <= end; d++) if (taken[d]) { c24++; if (d >= w14) c14++; }
    out.u14[p] = u14; out.u24[p] = u24; out.cov14[p] = c14; out.cov24[p] = c24; out.files[p] = n;
  });
  return out;
}

// Daily rate from per-platform unit totals: units / days covered, summed over platforms.
// When every platform covers the same days this is one division, as in the Python scripts.
function rate(units, cov) {
  var ps = Object.keys(cov).filter(function (p) { return cov[p] > 0; });
  if (!ps.length) return 0;
  var same = ps.every(function (p) { return cov[p] === cov[ps[0]]; });
  if (same) return ps.reduce(function (t, p) { return t + (units[p] || 0); }, 0) / cov[ps[0]];
  return ps.reduce(function (t, p) { return t + (units[p] || 0) / cov[p]; }, 0);
}

// Sales codes that differ from the stock code, confirmed by the user (handover 6.2)
var ALIASES = [[/^LA-7225SRG-/, 'LD-L7225RG']];

// Sales code -> stock key (allbrand.py match(), plus ALIASES)
function matchCode(s, stock) {
  if (stock.has(s)) return s;
  for (var a = 0; a < ALIASES.length; a++) if (ALIASES[a][0].test(s) && stock.has(ALIASES[a][1])) return ALIASES[a][1];
  if (s.indexOf('BNB') === 0) return null;
  var sufs = ['UDF', 'DF', 'D'];
  for (var i = 0; i < sufs.length; i++) if (stock.has(s + sufs[i])) return s + sufs[i];
  var c = [];
  stock.forEach(function (_, k) { if (k.indexOf(s) === 0 && k.length - s.length <= 4) c.push(k); });
  if (c.length === 1) return c[0];
  var t = s.replace(/-[0-9A-Z]{1,3}$/, '');
  if (t !== s && stock.has(t)) return t;
  return null;
}

// One of the 77 tiered Bonia SKUs (restock.py plan())
function planBonia(sku, tier, f14, f24, eco, outlet) {
  var f = tier === 'Sold-out best seller' ? f24 : f14;
  var g = KEEP[tier], h = g === 0 ? 0 : Math.max(MIN_LINE, ceil9(f * g));
  var status = tier === 'Stop' ? 'Do not restock' : (eco <= h ? 'RESTOCK' : 'OK');
  var left = f ? Math.floor(eco / f) : null;
  // No sales in the window: restock.py has no case for this; treat as Later
  var pri = status !== 'RESTOCK' ? '' : (left === null ? 'Later' : left <= 3 ? 'Urgent' : left <= 7 ? 'Soon' : 'Later');
  var C = f * (TREND[tier] || 1), E = C * (BONIA_LEAD + BONIA_CYCLE);
  var G = tier === 'Stop' ? 0 : Math.max(0, ceil9(Z[tier] * Math.sqrt(E)));
  var H = tier === 'Stop' ? 0 : ceil9(E + G);
  var K = Math.max(0, H - eco), M = Math.min(K, Math.max(0, outlet - LEAVE)), N = K - M;
  var Q = C ? (eco + M + N) / (C * 7) : null, act;
  if (tier === 'Stop') act = (Q || 0) > OVER_WEEKS ? 'Clear stock: discount or bundle' : 'Sell through, do not reorder';
  else act = (Q || 0) > OVER_WEEKS ? 'Overstocked: skip orders' : (N > 0 ? 'Order from supplier' : (M > 0 ? 'Transfer from outlet' : 'No action'));
  return {code: sku, brand: 'BONI', tier: tier, daily: f, line: h, status: status, left: left, pri: pri,
    target: H, xfer: M, order: N, weeks: Q, action: act, eco: eco, out: outlet};
}

// Any other SKU with online sales (allplan.py), overstock only when nothing needs
// ordering or moving and stock lasts more than MAX(8, cover/7) weeks
function planOther(s, d) {
  var lead = LEAD[s.brand] || DEF_LEAD, cyc = CYCLE[s.brand] || DEF_CYCLE;
  var line = Math.max(MIN_LINE, ceil9(d * Math.max(DEF_KEEP, lead)));
  var eco = s.eco, out = s.hq + s.shops;
  var status = eco <= line ? 'RESTOCK' : 'OK', left = Math.floor(eco / d);
  var pri = status !== 'RESTOCK' ? '' : (left <= 3 ? 'Urgent' : left <= 7 ? 'Soon' : 'Later');
  var T = d * (lead + cyc), U = Math.max(0, ceil9(DEF_Z * Math.sqrt(T))), V = ceil9(T + U);
  var X = Math.max(0, V - eco), Y = Math.min(X, Math.max(0, out - LEAVE)), Zq = X - Y;
  var weeks = (eco + Y + Zq) / (d * 7);
  var act = Zq > 0 ? 'Order from supplier' : Y > 0 ? 'Transfer from outlet' :
    weeks > Math.max(OVER_WEEKS, (lead + cyc) / 7) ? 'Overstocked: skip orders' : 'No action';
  return {code: s.code, brand: s.brand, tier: 'Steady', daily: d, line: line, status: status, left: left, pri: pri,
    target: V, xfer: Y, order: Zq, weeks: weeks, action: act, eco: eco, out: out, missing: !!s.missing};
}

// Full plan: stock rows + parsed sales files + window end day -> rows and checks
function buildPlan(stockRows, salesFiles, end) {
  var stock = parseStock(stockRows), sr = salesRates(salesFiles, end);
  var plats = Object.keys(sr.cov14), bonia77 = {}, rows = [];
  var get = function (m, s) { var u = {}; plats.forEach(function (p) { u[p] = m[p].get(s) || 0; }); return u; };

  BONIA_TIERS.forEach(function (t) {
    var k = norm(t[0]), x = stock.get(k);
    bonia77[k] = 1;
    var r = planBonia(t[0], t[1], rate(get(sr.u14, k), sr.cov14), rate(get(sr.u24, k), sr.cov24),
      x ? x.eco : 0, x ? x.hq + x.shops : 0);
    r.missing = !x;
    rows.push(r);
  });

  // allbrand.py: sales codes -> stock keys, units per platform
  var agg = new Map(), total = 0, matched = 0, unmatched = [];
  var codes = new Set();
  plats.forEach(function (p) { sr.u14[p].forEach(function (_, s) { codes.add(s); }); });
  codes.forEach(function (s) {
    var u = get(sr.u14, s), units = plats.reduce(function (t, p) { return t + u[p]; }, 0);
    total += units;
    var m = matchCode(s, stock);
    if (!m && s.indexOf('BNB') === 0) {
      stock.set(s, {code: s, brand: 'BONI', desc: 'BONIA ' + s, eco: 0, hq: 0, shops: 0, total: 0, missing: true});
      m = s;
    }
    if (!m) { if (units > 0) unmatched.push([units, s]); return; }
    matched += units;
    var a = agg.get(m) || {};
    plats.forEach(function (p) { a[p] = (a[p] || 0) + u[p]; });
    agg.set(m, a);
  });
  agg.forEach(function (u, k) {
    var s = stock.get(k);
    if (bonia77[norm(s.code)]) return;
    var d = rate(u, sr.cov14);
    if (d > 0) rows.push(planOther(s, d));
  });
  rows.sort(function (x, y) { return PRI[x.pri] - PRI[y.pri] || y.daily - x.daily; });
  unmatched.sort(function (x, y) { return y[0] - x[0]; });
  return {rows: rows, cov14: sr.cov14, cov24: sr.cov24, files: sr.files, start14: end - 13, end: end,
    units: total, matched: matched, unmatched: unmatched};
}

function brandName(b) { return BRAND_NAMES[b] || b || '?'; }
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function pad(s, n, right) { s = String(s); return right ? (s.length >= n ? s : ' '.repeat(n - s.length) + s) : (s + ' '.repeat(Math.max(0, n - s.length))); }
function fmt(n) { return Math.round(n).toLocaleString('en-US'); }
function dm(day) { var s = dayStr(day); return +s.slice(8) + '/' + +s.slice(5, 7); }

// Telegram HTML message. meta: {today (day number), stockTitle, stockDay, sheetUrl}
function formatReport(plan, meta) {
  var rows = plan.rows, by = {}, order = 0, move = 0, urgent = 0, cost = 0, noCost = 0;
  rows.forEach(function (r) {
    var b = by[r.brand] = by[r.brand] || {order: 0, move: 0, urgent: 0};
    b.order += r.order; b.move += r.xfer; order += r.order; move += r.xfer;
    if (r.pri === 'Urgent') { b.urgent++; urgent++; }
    if (r.brand === 'BONI' && r.order > 0) { if (UNIT_COST[r.code] !== undefined) cost += r.order * UNIT_COST[r.code]; else noCost++; }
  });
  var L = [];
  L.push('<b>Restock report ' + dm(meta.today) + '</b>');
  L.push('Stock: ' + esc(meta.stockTitle) + ' | Online sales ' + dm(plan.start14) + '-' + dm(plan.end) + ' (' +
    Object.keys(plan.cov14).sort().map(function (p) { return p + ' ' + plan.cov14[p] + '/14 days'; }).join(', ') + ')');
  L.push('');
  L.push('<b>Order ' + fmt(order) + ' | Move ' + fmt(move) + ' to online | ' + urgent + ' SKUs urgent</b>');
  if (cost) L.push('Bonia order ~RM ' + fmt(cost) + ' at cost' + (noCost ? ' (' + noCost + ' SKUs without cost)' : ''));
  L.push('');
  var brands = Object.keys(by).filter(function (b) { return by[b].order || by[b].move || by[b].urgent; })
    .sort(function (x, y) { return by[y].order - by[x].order; });
  var t = [pad('Brand', 12) + pad('Order', 6, 1) + pad('Move', 6, 1) + pad('Urgent', 7, 1)];
  var line = function (name, o, m, u) { t.push(pad(name, 12) + pad(fmt(o), 6, 1) + pad(fmt(m), 6, 1) + pad(u, 7, 1)); };
  brands.slice(0, 10).forEach(function (b) { line(brandName(b), by[b].order, by[b].move, by[b].urgent); });
  var rest = brands.slice(10);
  if (rest.length) line('Others (' + rest.length + ')', rest.reduce(function (x, b) { return x + by[b].order; }, 0),
    rest.reduce(function (x, b) { return x + by[b].move; }, 0), rest.reduce(function (x, b) { return x + by[b].urgent; }, 0));
  L.push('<pre>' + esc(t.join('\n')) + '</pre>');

  // Reminder 1: order the urgent SKUs
  var top = rows.filter(function (r) { return r.pri === 'Urgent' && r.order > 0; })
    .sort(function (x, y) { return y.order - x.order || y.daily - x.daily; });
  if (top.length) {
    L.push('<b>Reminder: order these urgent SKUs</b> (top ' + Math.min(20, top.length) + ' of ' + top.length + ')');
    var u = [pad('SKU', 16) + pad('Online', 7, 1) + pad('/day', 5, 1) + pad('Move', 5, 1) + pad('Order', 6, 1)];
    top.slice(0, 20).forEach(function (r) {
      u.push(pad(r.code + (r.missing ? '*' : ''), 16).slice(0, 16) + pad(fmt(r.eco), 7, 1) + pad(r.daily.toFixed(1), 5, 1) +
        pad(r.xfer ? fmt(r.xfer) : '', 5, 1) + pad(fmt(r.order), 6, 1));
    });
    L.push('<pre>' + esc(u.join('\n')) + '</pre>');
  }

  // Reminder 2: today's stock report missing
  if (meta.stockDay !== meta.today) {
    L.push('<b>Reminder: stock report for ' + dm(meta.today) + ' is not in STOCK REPORT FILE yet.</b> ' +
      'Stock manager, please upload TPSB ' + dm(meta.today) + '. This report uses ' + esc(meta.stockTitle) + '.');
  }
  var low = Object.keys(plan.cov14).filter(function (p) { return plan.cov14[p] < 14; });
  if (low.length || !Object.keys(plan.cov14).length) {
    L.push('Check: sales files missing for some days (' + (low.join(', ') || 'TikTok, Shopee') + '); daily rates use the days found.');
  }
  L.push('Not counted: stock already on order (open POs), outlet walk-in sales. * = not in stock file, counted as 0.');
  if (plan.units) L.push('Sales codes matched to stock: ' + Math.round(100 * plan.matched / plan.units) + '% of units.');
  if (meta.sheetUrl) L.push('<a href="' + meta.sheetUrl + '">Stock Analysis sheet</a>');
  return L.join('\n');
}

if (typeof module !== 'undefined') module.exports = {parseStock: parseStock, parseSales: parseSales, salesRates: salesRates,
  matchCode: matchCode, planBonia: planBonia, planOther: planOther, buildPlan: buildPlan, formatReport: formatReport,
  dayNum: dayNum, norm: norm};
