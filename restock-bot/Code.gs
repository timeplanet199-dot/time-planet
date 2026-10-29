// Daily restock report for the Time Planet operation group on Telegram.
// Runs every day at 8pm Malaysia time (setup() creates the trigger).
// Reads the newest TPSB stock file and the BigSeller sales reports from Drive,
// works out the restock plan (Logic.gs) and the Stock manager bot posts it.
// Script properties (Project Settings -> Script properties):
//   TG_TOKEN    Stock manager bot token, from the "access" doc. Never put it in code.
//   TG_CHAT_ID  the group's chat id. findChats() fills it in.

var STOCK_FOLDER = '1ePcVVTswJ_n520Avw1EwRpUjOVsga44M';   // STOCK REPORT FILE
var SALES_FOLDERS = ['1tdwYVsuQuVRD8qHKei0CJzLNQz5HY22m',  // big seller data (TikTok)
                     '1vSfwEKhJJrid3O3UUQNva8TcdoUUYK58']; // Shopee
var SHEET_URL = 'https://docs.google.com/spreadsheets/d/1cc-NC3740UwtJ3JnrOHYe94p09382vAZrUvkxTIs3-w/edit';
var TZ = 'Asia/Kuala_Lumpur';
var MONTHS = {JAN: 1, FEB: 2, MAR: 3, APR: 4, MAY: 5, JUN: 6, JUL: 7, AUG: 8, SEP: 9, OCT: 10, NOV: 11, DEC: 12};

// ---- run once ----

// Creates the daily 8pm trigger (Apps Script runs it between 8:00 and 8:15pm).
function setup() {
  var p = PropertiesService.getScriptProperties();
  if (!p.getProperty('TG_TOKEN')) throw new Error('Add the script property TG_TOKEN first (Stock manager bot token).');
  if (!p.getProperty('TG_CHAT_ID')) throw new Error('Run findChats() first to save the group chat id.');
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'dailyRestockReport') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('dailyRestockReport').timeBased().everyDays(1).atHour(20).nearMinute(0).inTimezone(TZ).create();
  Logger.log('Daily trigger set for 8pm ' + TZ + '.');
}

// Lists the groups the bot has seen and saves the operation group's chat id.
// First add the Stock manager bot to the group and send a message in the group.
function findChats() {
  var res = tg('getUpdates', {});
  var chats = {};
  (res.result || []).forEach(function (u) {
    var m = u.message || u.my_chat_member || u.channel_post || u.edited_message;
    if (m && m.chat && m.chat.type !== 'private') chats[m.chat.id] = m.chat.title;
  });
  var ids = Object.keys(chats);
  ids.forEach(function (id) { Logger.log(id + '  ' + chats[id]); });
  var op = ids.filter(function (id) { return /operation/i.test(chats[id] || ''); });
  if (op.length === 1) {
    PropertiesService.getScriptProperties().setProperty('TG_CHAT_ID', op[0]);
    Logger.log('Saved TG_CHAT_ID = ' + op[0] + ' (' + chats[op[0]] + ')');
  } else {
    Logger.log(ids.length ? 'Set TG_CHAT_ID by hand to one of the ids above.' :
      'No group found. Add the bot to the group, send a message there, then run findChats() again.');
  }
}

// Builds the report and shows it in the log without sending it.
function previewReport() { Logger.log(makeReport()); }

// ---- daily ----

function dailyRestockReport() {
  var text;
  try {
    text = makeReport();
  } catch (e) {
    text = '<b>Restock report failed</b>: ' + esc(e.message) + '\nPlease check the Apps Script log.';
  }
  send(text);
}

function makeReport() {
  var today = dayNum(Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd'));
  var stock = newestStock(today);
  if (!stock) throw new Error('No TPSB stock file found in STOCK REPORT FILE.');
  var end = today - 1;                      // yesterday's sales reports are uploaded before 10am
  var files = salesFiles(end);
  var plan = buildPlan(readRows(stock.file), files, end);
  return formatReport(plan, {today: today, stockTitle: stock.file.getName().replace(/\.xlsx$/i, ''),
    stockDay: stock.day, sheetUrl: SHEET_URL});
}

// Newest "TPSB dd/mm" file by the date in its name
function newestStock(today) {
  var best = null, it = DriveApp.getFolderById(STOCK_FOLDER).getFiles();
  while (it.hasNext()) {
    var f = it.next(), m = f.getName().match(/^TPSB\s+(\d{1,2})[\/\-.](\d{1,2})/i);
    if (!m) continue;
    var day = titleDay(+m[1], +m[2], today);
    if (!best || day > best.day || (day === best.day && f.getLastUpdated() > best.file.getLastUpdated())) best = {file: f, day: day};
  }
  return best;
}

// dd/mm in a file name -> day number, in the year that puts it on or before today
function titleDay(d, m, today) {
  var y = +dayStr(today).slice(0, 4);
  var n = dayNum(y + '-' + ('0' + m).slice(-2) + '-' + ('0' + d).slice(-2));
  return n > today + 1 ? dayNum((y - 1) + '-' + ('0' + m).slice(-2) + '-' + ('0' + d).slice(-2)) : n;
}

// Daily files "dd/mm TIKTOK|SHOPEE" in the 24-day window, and weekly files
// "TIKTOK|SHOPEE MMMYY WEEK n" of the window's months. Parsed files are cached
// in script properties so only new files are converted each night.
function salesFiles(end) {
  var start = end - 23, months = {};
  [start, end].forEach(function (d) { months[dayStr(d).slice(0, 7)] = 1; });
  var cache = PropertiesService.getScriptProperties(), keep = {}, out = [];
  SALES_FOLDERS.forEach(function (folder) {
    var it = DriveApp.getFolderById(folder).getFiles();
    while (it.hasNext()) {
      var f = it.next(), name = f.getName(), use = false, m;
      if ((m = name.match(/^(\d{1,2})\/(\d{1,2})\s+(TIKTOK|SHOPEE)/i))) {
        var d = titleDay(+m[1], +m[2], end + 1);
        use = d >= start && d <= end;
      } else if ((m = name.match(/^(TIKTOK|SHOPEE)\s+([A-Z]+)(\d{2})\s+WEEK/i))) {
        var mon = MONTHS[m[2].slice(0, 3).toUpperCase()];
        use = !!mon && months['20' + m[3] + '-' + ('0' + mon).slice(-2)] === 1;
      }
      if (!use) continue;
      var key = 'f_' + f.getId() + '_' + f.getLastUpdated().getTime();
      keep[key] = 1;
      var hit = cache.getProperty(key), parsed;
      if (hit) parsed = unpack(hit);
      else {
        parsed = parseSales(readRows(f));
        var s = pack(parsed);
        if (s.length < 9000) cache.setProperty(key, s);
      }
      if (parsed) out.push(parsed);
    }
  });
  // drop cache entries of files no longer used
  Object.keys(cache.getProperties()).forEach(function (k) {
    if (k.indexOf('f_') === 0 && !keep[k]) cache.deleteProperty(k);
  });
  return out;
}

function pack(p) {
  if (!p) return 'none';
  var q = [];
  p.q.forEach(function (v, k) { if (v) q.push(k + '\t' + v); });
  return [p.plat, p.a, p.b].join('|') + '\n' + q.join('\n');
}
function unpack(s) {
  if (s === 'none') return null;
  var lines = s.split('\n'), h = lines[0].split('|'), q = new Map();
  lines.slice(1).forEach(function (l) { if (l) { var t = l.split('\t'); q.set(t[0], +t[1]); } });
  return {plat: h[0], a: +h[1], b: +h[2], q: q};
}

// xlsx -> rows of the first sheet, via a temporary Google Sheet copy
function readRows(file) {
  var tmp = Drive.Files.copy({name: 'tmp restock ' + file.getName(), mimeType: MimeType.GOOGLE_SHEETS}, file.getId());
  try {
    return SpreadsheetApp.openById(tmp.id).getSheets()[0].getDataRange().getDisplayValues();
  } finally {
    Drive.Files.remove(tmp.id);
  }
}

// ---- Telegram ----

function send(text) {
  var chat = PropertiesService.getScriptProperties().getProperty('TG_CHAT_ID');
  // Telegram allows 4096 characters per message
  while (text.length) {
    var cut = text.length <= 4000 ? text.length : text.lastIndexOf('\n', 4000);
    tg('sendMessage', {chat_id: chat, text: text.slice(0, cut), parse_mode: 'HTML', disable_web_page_preview: true});
    text = text.slice(cut).replace(/^\n/, '');
  }
}

function tg(method, payload) {
  var token = PropertiesService.getScriptProperties().getProperty('TG_TOKEN');
  if (!token) throw new Error('Script property TG_TOKEN is missing.');
  var r = UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/' + method,
    {method: 'post', contentType: 'application/json', payload: JSON.stringify(payload), muteHttpExceptions: true});
  var body = JSON.parse(r.getContentText());
  if (!body.ok) throw new Error('Telegram ' + method + ': ' + body.description);
  return body;
}
