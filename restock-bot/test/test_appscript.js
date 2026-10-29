// Runs dist/RestockBot.gs end to end with fake Google and Telegram services:
// start() on a fresh project, then a second nightly run that should use the cache.
// Usage: node restock-bot/test/test_appscript.js <fixtures dir from make_fixtures.py>
const fs = require('fs'), path = require('path'), vm = require('vm');
const fx = JSON.parse(fs.readFileSync(path.join(process.argv[2], 'fixtures.json'), 'utf8'));
const log = [], calls = [], props = {}, sheets = {}, triggers = [];
let copies = 0, deletes = 0;
const file = (id, name, rows) => { sheets[id] = rows; return {getId: () => id, getName: () => name, getLastUpdated: () => new Date(1793000000000)}; };
const daily = [['Sales Report', 'Time:2026-10-28'], fx.other[0][1], ['Shopee Time Planet', 'BNB10986-2227', 'x', '2']];
const folders = {
  '1ePcVVTswJ_n520Avw1EwRpUjOVsga44M': [file('s1', 'TPSB 27/10.xlsx', fx.stock), file('s2', 'TPSB 28/10.xlsx', fx.stock), file('s3', 'TZG 28/10.xlsx', [])],
  '1tdwYVsuQuVRD8qHKei0CJzLNQz5HY22m': [file('t2', 'TIKTOK OCT26 WEEK 2.xlsx', fx.other[0]), file('t3', 'TIKTOK OCT26 WEEK 3.xlsx', fx.other[2]),
    file('old', 'TIKTOK AUG26 WEEK 1.xlsx', fx.other[0])],
  '1vSfwEKhJJrid3O3UUQNva8TcdoUUYK58': [file('p2', 'SHOPEE OCT26 WEEK 2.xlsx', fx.other[1]), file('p3', 'SHOPEE OCT26 WEEK 3.xlsx', fx.other[3]),
    file('d28', '28/10 SHOPEE.xlsx', daily)],
};
const iter = (a) => { let i = 0; return {hasNext: () => i < a.length, next: () => a[i++]}; };
const resp = (code, obj) => ({getResponseCode: () => code, getContentText: () => obj === null ? '' : JSON.stringify(obj)});
const g = {
  console, Logger: {log: (x) => log.push(String(x))},
  Utilities: {formatDate: () => '2026-10-29'},
  PropertiesService: {getScriptProperties: () => ({getProperty: (k) => props[k] || null, setProperty: (k, v) => { props[k] = String(v); },
    getProperties: () => Object.assign({}, props), deleteProperty: (k) => { delete props[k]; }})},
  DocumentApp: {openById: () => ({getBody: () => ({getText: () => 'Assistant manager\n\n111:AAassist\n\n\nStock manager\n\n222:AAstock_x-y\n'})})},
  DriveApp: {getFolderById: (id) => ({getFiles: () => iter(folders[id])})},
  SpreadsheetApp: {openById: (id) => ({getSheets: () => [{getDataRange: () => ({getDisplayValues: () => sheets[id.replace('tmp_', '')]})}]})},
  ScriptApp: {getOAuthToken: () => 'oauth', getProjectTriggers: () => triggers, deleteTrigger: () => {},
    newTrigger: (fn) => { const t = {fn}; const c = {timeBased: () => c, everyDays: (n) => (t.every = n, c), atHour: (h) => (t.hour = h, c),
      nearMinute: () => c, inTimezone: (z) => (t.tz = z, c), create: () => triggers.push(t)}; return c; }},
  UrlFetchApp: {fetch: (url, opt) => {
    let m;
    if ((m = url.match(/drive\/v3\/files\/([^/]+)\/copy$/))) { copies++; return resp(200, {id: 'tmp_' + m[1]}); }
    if (/drive\/v3\/files\/tmp_/.test(url) && opt.method === 'delete') { deletes++; return resp(204, null); }
    if ((m = url.match(/api\.telegram\.org\/bot([^/]+)\/(\w+)$/))) {
      calls.push({token: m[1], method: m[2], body: JSON.parse(opt.payload)});
      if (m[2] === 'getUpdates') return resp(200, {ok: true, result: [{my_chat_member: {chat: {id: -1001234, type: 'supergroup', title: 'Time Planet Operation Group'}}},
        {message: {chat: {id: 7161173460, type: 'private'}}}]});
      return resp(200, {ok: true, result: {}});
    }
    throw new Error('unexpected fetch ' + url);
  }},
};
const ctx = vm.createContext(g);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'dist', 'RestockBot.gs'), 'utf8'), ctx);
let bad = 0; const check = (n, ok) => { console.log((ok ? 'ok   ' : 'FAIL ') + n); if (!ok) bad++; };

vm.runInContext('start()', ctx);
const sent = calls.filter(c => c.method === 'sendMessage');
check('token read from the access doc (Stock manager line)', calls.every(c => c.token === '222:AAstock_x-y'));
check('operation group chat id saved', props.TG_CHAT_ID === '-1001234');
check('daily trigger at 20:00 Asia/Kuala_Lumpur', triggers.length === 1 && triggers[0].fn === 'dailyRestockReport' && triggers[0].hour === 20 && triggers[0].tz === 'Asia/Kuala_Lumpur');
check('report sent to the group as HTML', sent.length >= 1 && sent.every(c => c.body.chat_id === '-1001234' && c.body.parse_mode === 'HTML'));
const text = sent.map(c => c.body.text).join('\n');
check('no "failed" message', !/Restock report failed/.test(text));
check('uses newest stock file TPSB 28/10', /Stock: TPSB 28\/10/.test(text));
check('stock-missing reminder for 29/10', /stock report for 29\/10 is not in STOCK REPORT FILE/.test(text));
check('urgent-order reminder present', /Reminder: order these urgent SKUs/.test(text));
check('every temp sheet deleted', copies > 0 && copies === deletes);
check('August weekly file not read', copies === 6);   // TPSB 28/10 + 2 TikTok + 2 Shopee weeks + 1 daily
check('messages within Telegram limit', sent.every(c => c.body.text.length <= 4096));
const firstCopies = copies;
vm.runInContext('dailyRestockReport()', ctx);
check('second night: sales files come from the cache', copies - firstCopies === 1);   // only the stock file
console.log('\n--- message ---\n' + text.split('\n').slice(0, 6).join('\n') + '\n...');
console.log(bad ? `FAILED: ${bad}` : 'ALL OK');
process.exit(bad ? 1 : 0);
