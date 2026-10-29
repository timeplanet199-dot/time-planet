// Builds the Telegram restock report from JSON on stdin:
// {stock: rows, files: [rows...], end: 'YYYY-MM-DD', today: 'YYYY-MM-DD', stockTitle, stockDay: 'YYYY-MM-DD', sheetUrl}
// Prints {html, view, summary} as JSON (view feeds render.js). Uses the same Logic.gs and Data.gs as the Apps Script.
const fs = require('fs'), path = require('path'), vm = require('vm');
const ctx = vm.createContext({});
for (const f of ['Data.gs', 'Logic.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', f), 'utf8'), ctx);
ctx.input = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = vm.runInContext(`(function () {
  var files = input.files.map(parseSales).filter(Boolean);
  var plan = buildPlan(input.stock, files, dayNum(input.end));
  var html = formatReport(plan, {today: dayNum(input.today), stockTitle: input.stockTitle, stockDay: dayNum(input.stockDay), sheetUrl: input.sheetUrl});
  var meta = {today: dayNum(input.today), stockTitle: input.stockTitle, stockDay: dayNum(input.stockDay), skipped: input.skipped || []};
  return {html: html, view: summarize(plan, meta), summary: {files: files.length, cov14: plan.cov14, rows: plan.rows.length, units: plan.units, matched: plan.matched,
    order: plan.rows.reduce(function (t, r) { return t + r.order; }, 0), urgent: plan.rows.filter(function (r) { return r.pri === 'Urgent'; }).length}};
})()`, ctx);
process.stdout.write(JSON.stringify(out));
