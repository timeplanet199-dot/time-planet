/**
 * Fulfillment Tracker — Google Apps Script web app.
 *
 * Every worker scans the order barcode when they FINISH their step.
 * Each scan is logged with time + worker, so you can see per person:
 * how many orders, how fast, idle gaps, and which orders are stuck.
 *
 * Sheets used (created by setup()):
 *   Staff : ID | Name | Active
 *   Log   : Timestamp | Date | Order | Step | Staff ID | Staff Name | Flag
 */

const CONFIG = {
  LOG_SHEET: 'Log',
  STAFF_SHEET: 'Staff',
  // Order matters: the flow goes left to right.
  STEPS: {
    PICK: 'Pick & Label',     // label printed, products found, label stuck
    PACK: 'Pack & Warranty',  // packed, warranty card inserted, sealed
  },
  IDLE_MINUTES: 10,   // gap between two scans of one person counted as idle
  STUCK_MINUTES: 60,  // picked but not packed for longer than this = stuck
  DUP_LOOKBACK_ROWS: 5000,
};

const LOG_HEADERS = ['Timestamp', 'Date', 'Order', 'Step', 'Staff ID', 'Staff Name', 'Flag'];

/** Run once from the Apps Script editor to create the sheets. */
function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  let staff = ss.getSheetByName(CONFIG.STAFF_SHEET);
  if (!staff) {
    staff = ss.insertSheet(CONFIG.STAFF_SHEET);
    staff.appendRow(['ID', 'Name', 'Active']);
    [['S01', 'Worker 1'], ['S02', 'Worker 2'], ['S03', 'Worker 3'],
     ['S04', 'Worker 4'], ['S05', 'Worker 5'], ['S06', 'Worker 6']]
      .forEach(r => staff.appendRow([r[0], r[1], true]));
    staff.setFrozenRows(1);
  }

  let log = ss.getSheetByName(CONFIG.LOG_SHEET);
  if (!log) {
    log = ss.insertSheet(CONFIG.LOG_SHEET);
    log.appendRow(LOG_HEADERS);
    log.setFrozenRows(1);
  }
  // Keep Date and Order as plain text so order numbers keep leading zeros.
  log.getRange('B:C').setNumberFormat('@');
  log.getRange('A:A').setNumberFormat('yyyy-mm-dd hh:mm:ss');
}

function doGet(e) {
  const page = e && e.parameter && e.parameter.page === 'dashboard' ? 'Dashboard' : 'Index';
  return HtmlService.createTemplateFromFile(page)
    .evaluate()
    .setTitle(page === 'Dashboard' ? 'Fulfillment Dashboard' : 'Fulfillment Scan')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function getConfig() {
  return {
    staff: getStaff(),
    steps: Object.keys(CONFIG.STEPS).map(k => ({ id: k, label: CONFIG.STEPS[k] })),
    url: ScriptApp.getService().getUrl(),
  };
}

function getStaff() {
  const sheet = getSheet_(CONFIG.STAFF_SHEET);
  const last = sheet.getLastRow();
  if (last < 2) return [];
  return sheet.getRange(2, 1, last - 1, 3).getValues()
    .filter(r => r[0] && r[2] !== false && String(r[2]).toUpperCase() !== 'FALSE')
    .map(r => ({ id: String(r[0]).trim(), name: String(r[1]).trim() }));
}

/** Called by the scan page for every barcode scan. */
function recordScan(staffId, step, orderId) {
  orderId = String(orderId || '').trim().toUpperCase();
  if (!orderId) throw new Error('Empty order number');
  if (!CONFIG.STEPS[step]) throw new Error('Unknown step: ' + step);
  const staff = getStaff().find(s => s.id === staffId);
  if (!staff) throw new Error('Unknown staff: ' + staffId);

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const sheet = getSheet_(CONFIG.LOG_SHEET);
    const recent = readRows_(sheet, CONFIG.DUP_LOOKBACK_ROWS);
    const now = new Date();
    const today = formatDate_(now);

    const dup = recent.find(r => r.order === orderId && r.step === step);
    if (dup) {
      return {
        status: 'duplicate',
        message: `${orderId} already scanned for ${CONFIG.STEPS[step]} by ${dup.staffName} at ${formatTime_(dup.ts)}`,
      };
    }

    // Every step except the first must have the previous step done.
    const stepKeys = Object.keys(CONFIG.STEPS);
    const prev = stepKeys[stepKeys.indexOf(step) - 1];
    const flag = prev && !recent.some(r => r.order === orderId && r.step === prev)
      ? `MISSING_${prev}` : '';

    sheet.appendRow([now, today, orderId, step, staff.id, staff.name, flag]);

    const count = recent.filter(r => r.date === today && r.staffId === staff.id && r.step === step).length + 1;
    return {
      status: flag ? 'warning' : 'ok',
      message: flag
        ? `${orderId} saved, but it was never scanned at ${CONFIG.STEPS[prev]}`
        : `${orderId} done`,
      count: count,
    };
  } finally {
    lock.releaseLock();
  }
}

/** Data for the dashboard page. dateStr = 'yyyy-MM-dd', defaults to today. */
function getDashboard(dateStr) {
  const now = new Date();
  const date = dateStr || formatDate_(now);
  const isToday = date === formatDate_(now);
  const rows = readRows_(getSheet_(CONFIG.LOG_SHEET))
    .filter(r => r.date === date)
    .sort((a, b) => a.ts - b.ts);
  const stepKeys = Object.keys(CONFIG.STEPS);
  const idleMs = CONFIG.IDLE_MINUTES * 60000;

  // Per person.
  const people = {};
  getStaff().forEach(s => { people[s.id] = newPerson_(s.id, s.name, stepKeys); });
  rows.forEach(r => {
    const p = people[r.staffId] || (people[r.staffId] = newPerson_(r.staffId, r.staffName, stepKeys));
    p.steps[r.step] = (p.steps[r.step] || 0) + 1;
    p.times.push(r.ts.getTime());
    if (r.flag) p.flags++;
  });

  const persons = Object.values(people).map(p => {
    const t = p.times;
    const gaps = t.slice(1).map((x, i) => x - t[i]);
    const workGaps = gaps.filter(g => g <= idleMs).sort((a, b) => a - b);
    const idle = gaps.filter(g => g > idleMs);
    const spanH = t.length > 1 ? (t[t.length - 1] - t[0]) / 3600000 : 0;
    const total = t.length;
    return {
      id: p.id,
      name: p.name,
      steps: p.steps,
      total: total,
      first: t.length ? formatTime_(new Date(t[0])) : '',
      last: t.length ? formatTime_(new Date(t[t.length - 1])) : '',
      perHour: spanH > 0 ? Math.round(total / spanH * 10) / 10 : 0,
      medianSec: workGaps.length ? Math.round(workGaps[Math.floor(workGaps.length / 2)] / 1000) : 0,
      idleCount: idle.length,
      idleMin: Math.round(idle.reduce((a, b) => a + b, 0) / 60000),
      flags: p.flags,
    };
  }).sort((a, b) => b.total - a.total);

  // Scans per person per hour.
  const hourly = {};
  rows.forEach(r => {
    const h = Number(Utilities.formatDate(r.ts, tz_(), 'H'));
    hourly[h] = hourly[h] || {};
    hourly[h][r.staffId] = (hourly[h][r.staffId] || 0) + 1;
  });

  // Per order: lead time and stuck orders.
  const orders = {};
  rows.forEach(r => {
    const o = orders[r.order] || (orders[r.order] = { order: r.order, done: {} });
    o.done[r.step] = { ts: r.ts.getTime(), by: r.staffName };
  });
  const first = stepKeys[0];
  const lastStep = stepKeys[stepKeys.length - 1];
  const leads = [];
  const stuck = [];
  Object.values(orders).forEach(o => {
    const a = o.done[first];
    const b = o.done[lastStep];
    if (a && b) leads.push(b.ts - a.ts);
    if (a && !b && (!isToday || now.getTime() - a.ts > CONFIG.STUCK_MINUTES * 60000)) {
      stuck.push({
        order: o.order,
        since: formatTime_(new Date(a.ts)),
        by: a.by,
        minutes: Math.round((now.getTime() - a.ts) / 60000),
      });
    }
  });

  const totals = {};
  stepKeys.forEach(k => { totals[k] = rows.filter(r => r.step === k).length; });

  return {
    date: date,
    steps: stepKeys.map(k => ({ id: k, label: CONFIG.STEPS[k] })),
    totals: totals,
    completed: Object.values(orders).filter(o => o.done[lastStep]).length,
    avgLeadMin: leads.length ? Math.round(leads.reduce((a, b) => a + b, 0) / leads.length / 60000) : 0,
    persons: persons,
    hourly: hourly,
    stuck: stuck.sort((a, b) => b.minutes - a.minutes),
    flagged: rows.filter(r => r.flag).map(r => ({
      order: r.order, step: r.step, by: r.staffName, at: formatTime_(r.ts), flag: r.flag,
    })),
    idleMinutes: CONFIG.IDLE_MINUTES,
  };
}

function newPerson_(id, name, stepKeys) {
  const steps = {};
  stepKeys.forEach(k => { steps[k] = 0; });
  return { id: id, name: name, steps: steps, times: [], flags: 0 };
}

function readRows_(sheet, maxRows) {
  const last = sheet.getLastRow();
  if (last < 2) return [];
  const start = maxRows ? Math.max(2, last - maxRows + 1) : 2;
  return sheet.getRange(start, 1, last - start + 1, LOG_HEADERS.length).getValues()
    .filter(v => v[0])
    .map(v => ({
      ts: new Date(v[0]),
      date: v[1] instanceof Date ? formatDate_(v[1]) : String(v[1]),
      order: String(v[2]).toUpperCase(),
      step: String(v[3]),
      staffId: String(v[4]),
      staffName: String(v[5]),
      flag: String(v[6] || ''),
    }));
}

function getSheet_(name) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
  if (!sheet) throw new Error(`Sheet "${name}" not found — run setup() first`);
  return sheet;
}

function tz_() { return Session.getScriptTimeZone(); }
function formatDate_(d) { return Utilities.formatDate(d, tz_(), 'yyyy-MM-dd'); }
function formatTime_(d) { return Utilities.formatDate(d, tz_(), 'HH:mm'); }
