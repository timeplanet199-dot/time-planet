/**
 * Live Commission Tracker — Google Apps Script (Sheet + web app).
 *
 * Hosts press GO LIVE / END LIVE on their phone, so every live session has an
 * exact start and end time. The marketplace order export is pasted into the
 * Import sheet, and each order is matched to a host by:
 *   1. the host's live-only voucher code, or
 *   2. the order time falling inside one of their live sessions (and, if the
 *      export says where the order came from, it came from live).
 * Commission is only paid on orders the marketplace marks Completed. Pending
 * orders wait for a later payout, cancelled/returned ones are never paid, and
 * an order cancelled after it was paid is deducted from the next payout.
 *
 * Sheets (created by setup()):
 *   Hosts    : ID | Name | Commission % | Voucher Codes | Active
 *   Sessions : Session ID | Host ID | Host Name | Platform | Start | End | Note
 *   Import   : paste a marketplace order export here (headers in row 1)
 *   Orders   : one row per order, updated by every import
 *   Payouts  : one row per host per payout (+ one statement sheet per payout)
 */

const CONFIG = {
  PLATFORMS: ['Shopee', 'TikTok', 'Lazada'],
  GRACE_MINUTES: 15,       // orders up to this long after END LIVE still count
  MAX_SESSION_HOURS: 6,    // a session nobody ended is cut off here (and flagged)
  COUNT_TIME_ONLY: true,   // count orders matched by time only (no voucher, no live source in export)
  DASHBOARD_PIN: '',       // set a PIN so hosts can't open the dashboard
  DATE_ORDER: 'DMY',       // how text dates in the export are written: 'DMY', 'MDY' or 'YMD'
  DECIMAL: '.',            // decimal separator of amounts in the export: '.' or ','
  AMOUNT_PER_ITEM_ROW: true, // true: amount column is per product row, rows of one order are added up
  // Header names to look for in the export; the first one found is used. Add yours if missing.
  COLUMNS: {
    order: ['Order ID', 'Order No.', 'Order Number', 'Order SN', 'Order Item ID'],
    created: ['Order Creation Date', 'Created Time', 'Order Created Time', 'Create Time', 'Order Date', 'Created at'],
    status: ['Order Status', 'Status'],
    refund: ['Return / Refund Status', 'Cancelation/Return Type', 'Cancellation/Return Type', 'Return Status', 'Refund Status'],
    amount: ['SKU Subtotal After Discount', 'Product Subtotal', 'Subtotal', 'Paid Price', 'Item Total'],
    voucher: ['Voucher Code', 'Seller Voucher Code', 'Promo Code', 'Coupon Code'],
    source: ['Order Source', 'Content Type', 'Traffic Source', 'Channel'],
  },
  LIVE_SOURCE_WORDS: ['live'],
  CANCELLED_WORDS: ['cancel', 'return', 'refund', 'failed', 'lost'],
  COMPLETED_WORDS: ['completed'],
  SHEETS: { HOSTS: 'Hosts', SESSIONS: 'Sessions', IMPORT: 'Import', ORDERS: 'Orders', PAYOUTS: 'Payouts' },
};

const HOST_HEADERS = ['ID', 'Name', 'Commission %', 'Voucher Codes', 'Active'];
const SESSION_HEADERS = ['Session ID', 'Host ID', 'Host Name', 'Platform', 'Start', 'End', 'Note'];
const PAYOUT_HEADERS = ['Payout ID', 'Created', 'Cutoff', 'Host ID', 'Host Name', 'Orders Paid', 'Sales', 'Commission', 'Deducted', 'Net'];
const ORDER_FIELDS = [
  ['platform', 'Platform'], ['order', 'Order ID'], ['created', 'Created'], ['status', 'Status'],
  ['state', 'State'], ['amount', 'Amount'], ['voucher', 'Voucher'], ['source', 'Source'],
  ['hostId', 'Host ID'], ['hostName', 'Host Name'], ['sessionId', 'Session ID'], ['matchedBy', 'Matched By'],
  ['commission', 'Commission'], ['overrideHost', 'Override Host'], ['overrideState', 'Override State'],
  ['payoutId', 'Payout ID'], ['clawbackId', 'Clawback ID'], ['updated', 'Updated'],
];
const STATES = ['PENDING', 'COMPLETED', 'CANCELLED'];

/** Run once from the Apps Script editor to create the sheets. */
function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const hosts = ensureSheet_(ss, CONFIG.SHEETS.HOSTS, HOST_HEADERS);
  if (hosts.getLastRow() < 2) {
    [['H01', 'Host 1', 5, 'LIVEHOST1'], ['H02', 'Host 2', 5, 'LIVEHOST2'], ['H03', 'Host 3', 5, 'LIVEHOST3']]
      .forEach(r => hosts.appendRow(r.concat(true)));
  }
  ensureSheet_(ss, CONFIG.SHEETS.SESSIONS, SESSION_HEADERS).getRange('E:F').setNumberFormat('yyyy-mm-dd hh:mm');
  const orders = ensureSheet_(ss, CONFIG.SHEETS.ORDERS, ORDER_FIELDS.map(f => f[1]));
  orders.getRange('B:B').setNumberFormat('@');
  orders.getRange('C:C').setNumberFormat('yyyy-mm-dd hh:mm');
  ensureSheet_(ss, CONFIG.SHEETS.PAYOUTS, PAYOUT_HEADERS);
  // Plain text, so long order numbers keep all their digits.
  const imp = ss.getSheetByName(CONFIG.SHEETS.IMPORT) || ss.insertSheet(CONFIG.SHEETS.IMPORT);
  if (imp.getMaxColumns() < 80) imp.insertColumnsAfter(imp.getMaxColumns(), 80 - imp.getMaxColumns());
  imp.getRange(1, 1, imp.getMaxRows(), imp.getMaxColumns()).setNumberFormat('@');
}

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Live Commission')
    .addItem('Import orders from Import sheet…', 'importOrders')
    .addItem('Recalculate matching', 'recalculate')
    .addSeparator()
    .addItem('Create payout…', 'createPayout')
    .addSeparator()
    .addItem('Show web app links', 'showLinks')
    .addToUi();
}

function doGet(e) {
  const page = e && e.parameter && e.parameter.page === 'dashboard' ? 'Dashboard' : 'Live';
  return HtmlService.createTemplateFromFile(page)
    .evaluate()
    .setTitle(page === 'Dashboard' ? 'Live Commission Dashboard' : 'Live Session')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function showLinks() {
  const url = ScriptApp.getService().getUrl();
  SpreadsheetApp.getUi().alert(url
    ? `Hosts (GO LIVE / END LIVE):\n${url}\n\nDashboard:\n${url}?page=dashboard`
    : 'Deploy the web app first: Deploy → New deployment → Web app.');
}

// ---------- Host page: GO LIVE / END LIVE ----------

function getLiveState() {
  const now = new Date();
  return {
    hosts: readHosts_().filter(h => h.active).map(h => ({ id: h.id, name: h.name })),
    platforms: CONFIG.PLATFORMS,
    live: readSessions_(now).filter(s => s.open)
      .map(s => ({ hostId: s.hostId, hostName: s.hostName, platform: s.platform, start: s.start })),
    now: now.getTime(),
    url: ScriptApp.getService().getUrl(),
  };
}

function goLive(hostId, platform) {
  const host = readHosts_().find(h => h.id === hostId && h.active);
  if (!host) throw new Error('Unknown host: ' + hostId);
  if (CONFIG.PLATFORMS.indexOf(platform) < 0) throw new Error('Unknown platform: ' + platform);
  return withLock_(() => {
    const now = new Date();
    const open = readSessions_(now).filter(s => s.open);
    const mine = open.find(s => s.hostId === host.id);
    if (mine) return { state: getLiveState(), message: `You are already live on ${mine.platform} since ${formatTime_(new Date(mine.start))}` };
    const id = 'L' + Utilities.formatDate(now, tz_(), 'yyMMdd-HHmmss') + '-' + host.id;
    getSheet_(CONFIG.SHEETS.SESSIONS).appendRow([id, host.id, host.name, platform, now, '', '']);
    const others = open.filter(s => s.platform === platform).map(s => s.hostName);
    return {
      state: getLiveState(),
      message: `LIVE on ${platform} from ${formatTime_(now)}` +
        (others.length ? `. ${others.join(', ')} is still live on ${platform}: ask them to press END LIVE.` : ''),
    };
  });
}

function endLive(hostId) {
  return withLock_(() => {
    const now = new Date();
    const mine = readSessions_(now).filter(s => s.open && s.hostId === hostId).pop();
    if (!mine) return { state: getLiveState(), message: 'You are not live' };
    getSheet_(CONFIG.SHEETS.SESSIONS).getRange(mine.row, 6).setValue(now);
    const min = Math.round((now.getTime() - mine.start) / 60000);
    return { state: getLiveState(), message: `Ended. You were live ${Math.floor(min / 60)}h ${min % 60}m on ${mine.platform}` };
  });
}

// ---------- Import & matching ----------

function importOrders() {
  const ui = SpreadsheetApp.getUi();
  const res = ui.prompt('Import orders',
    `Which platform is the export in the Import sheet from? (${CONFIG.PLATFORMS.join(' / ')})`, ui.ButtonSet.OK_CANCEL);
  if (res.getSelectedButton() !== ui.Button.OK) return;
  const answer = res.getResponseText().trim().toLowerCase();
  const platform = CONFIG.PLATFORMS.find(p => p.toLowerCase() === answer);
  if (!platform) return ui.alert('Unknown platform: ' + res.getResponseText());
  ui.alert('Import done', importFromSheet_(platform), ui.ButtonSet.OK);
}

function importFromSheet_(platform) {
  const imp = getSheet_(CONFIG.SHEETS.IMPORT);
  const range = imp.getDataRange();
  const parsed = parseExport_(range.getValues(), range.getDisplayValues());
  if (!parsed.orders.length) throw new Error('No orders found. Paste the export into the Import sheet with its header row in row 1.');

  return withLock_(() => {
    const now = new Date();
    const ctx = context_(now);
    const sheet = getSheet_(CONFIG.SHEETS.ORDERS);
    const orders = readOrders_(sheet);
    const index = {};
    orders.forEach(o => { index[key_(o.platform, o.order)] = o; });
    let added = 0, lateCancel = 0;
    const seen = [];
    parsed.orders.forEach(p => {
      let o = index[key_(platform, p.order)];
      if (!o) {
        o = index[key_(platform, p.order)] = { platform: platform, order: p.order, overrideHost: '', overrideState: '', payoutId: '', clawbackId: '' };
        orders.push(o);
        added++;
      }
      o.status = p.status;
      o.state = stateOf_(o.status, o.overrideState);
      o.updated = now;
      seen.push(o);
      if (o.payoutId) {
        // Already paid: amount and host stay as paid; only the status moves on.
        if (o.state === 'CANCELLED' && !o.clawbackId) lateCancel++;
        return;
      }
      o.created = p.created;
      o.amount = p.amount;
      o.voucher = p.voucher;
      o.source = p.source;
      attribute_(o, ctx);
    });
    writeOrders_(sheet, orders);
    imp.clearContents();

    const live = seen.filter(o => o.hostId);
    const lines = [
      `${parsed.rows} rows → ${parsed.orders.length} orders (${added} new, ${parsed.orders.length - added} updated).`,
      `${live.length} matched to a live host: ` + summarize_(live.map(o => o.matchedBy.replace(/^Voucher .*/, 'Voucher'))),
      `States of matched orders: ` + summarize_(live.map(o => o.state)),
    ];
    const notCounted = seen.filter(o => o.matchedBy === 'Time only (not counted)').length;
    if (notCounted) lines.push(`${notCounted} orders were placed during a live but have no live signal and were not counted (COUNT_TIME_ONLY is off).`);
    if (lateCancel) lines.push(`⚠ ${lateCancel} already-paid orders are now cancelled. They will be deducted in the next payout.`);
    lines.push('', 'Columns used:', parsed.used.join('\n'));
    return lines.join('\n');
  });
}

/** Re-match all unpaid orders, e.g. after fixing a session time, a voucher code or a commission %. */
function recalculate() {
  const msg = withLock_(() => {
    const ctx = context_(new Date());
    const sheet = getSheet_(CONFIG.SHEETS.ORDERS);
    const orders = readOrders_(sheet);
    orders.forEach(o => {
      o.state = stateOf_(o.status, o.overrideState);
      if (!o.payoutId) attribute_(o, ctx);
    });
    writeOrders_(sheet, orders);
    return `${orders.length} orders checked, ${orders.filter(o => o.hostId).length} matched to a live host.`;
  });
  SpreadsheetApp.getUi().alert(msg);
}

/** Turns the pasted export into one object per order. */
function parseExport_(values, display) {
  if (!display.length) return { orders: [], used: [], rows: 0 };
  const headers = display[0].map(h => String(h).trim().toLowerCase());
  const col = {};
  const used = [];
  Object.keys(CONFIG.COLUMNS).forEach(f => {
    const name = CONFIG.COLUMNS[f].find(n => headers.indexOf(n.toLowerCase()) >= 0);
    col[f] = name ? headers.indexOf(name.toLowerCase()) : -1;
    used.push(`${f}: ${name || '(not found)'}`);
  });
  const missing = ['order', 'created', 'status'].filter(f => col[f] < 0);
  if (missing.length) {
    throw new Error(`Could not find the ${missing.join(', ')} column. Headers in row 1: ` +
      display[0].filter(String).join(', ') + '. Add the right header name to CONFIG.COLUMNS.');
  }
  const text = (r, f) => col[f] >= 0 ? String(display[r][col[f]]).trim() : '';
  const add = (list, v) => { if (v && list.indexOf(v) < 0) list.push(v); };

  const byId = {};
  const list = [];
  for (let r = 1; r < display.length; r++) {
    const raw = values[r][col.order];
    if (typeof raw === 'number' && !Number.isSafeInteger(raw)) {
      throw new Error(`Row ${r + 1}: order number ${display[r][col.order]} was turned into a number and lost digits. ` +
        'Import the file as plain text (see README, "Importing orders").');
    }
    const id = (typeof raw === 'number' ? String(raw) : text(r, 'order')).toUpperCase();
    if (!id) continue;
    let o = byId[id];
    if (!o) {
      const c = values[r][col.created];
      o = byId[id] = {
        order: id, created: c instanceof Date ? c : parseDate_(text(r, 'created')),
        status: text(r, 'status'), refund: [], amount: 0, voucher: [], source: [], rows: 0,
      };
      list.push(o);
    }
    o.rows++;
    if (col.amount >= 0 && (CONFIG.AMOUNT_PER_ITEM_ROW || o.rows === 1)) {
      const a = values[r][col.amount];
      o.amount += typeof a === 'number' ? a : parseNumber_(text(r, 'amount'));
    }
    add(o.refund, text(r, 'refund'));
    add(o.voucher, text(r, 'voucher'));
    add(o.source, text(r, 'source'));
  }
  return {
    rows: display.length - 1,
    used: used,
    orders: list.map(o => ({
      order: o.order,
      created: o.created,
      status: o.status + (o.refund.length ? ' / ' + o.refund.join(', ') : ''),
      amount: round2_(o.amount),
      voucher: o.voucher.join(', '),
      source: o.source.join(', '),
    })),
  };
}

function stateOf_(status, override) {
  const ov = String(override || '').trim().toUpperCase();
  if (STATES.indexOf(ov) >= 0) return ov;
  const s = String(status).toLowerCase();
  if (CONFIG.CANCELLED_WORDS.some(w => s.indexOf(w) >= 0)) return 'CANCELLED';
  if (CONFIG.COMPLETED_WORDS.some(w => s.indexOf(w) >= 0)) return 'COMPLETED';
  return 'PENDING';
}

/** true = export says live, false = export says not live, null = export doesn't say. */
function isLive_(source) {
  const s = String(source || '').toLowerCase();
  if (!s) return null;
  return CONFIG.LIVE_SOURCE_WORDS.some(w => s.indexOf(w) >= 0);
}

/** Sets hostId, hostName, sessionId, matchedBy and commission on an order. */
function attribute_(o, ctx) {
  const t = o.created instanceof Date ? o.created.getTime() : NaN;
  const platform = String(o.platform).toLowerCase();
  const graceMs = CONFIG.GRACE_MINUTES * 60000;
  // Latest-started session covering the order time, so a handover overlap goes to the new host.
  const covering = hostId => ctx.sessions
    .filter(s => s.platform.toLowerCase() === platform && (!hostId || s.hostId === hostId) &&
      t >= s.start && t <= s.end + graceMs)
    .sort((a, b) => b.start - a.start)[0] || null;

  let host = null, session = null, how = '';
  const override = String(o.overrideHost || '').trim().toUpperCase();
  const code = String(o.voucher || '').toUpperCase().split(/[\s,;]+/).find(c => ctx.byVoucher[c]);
  if (override) {
    host = ctx.hosts[override] || null;
    session = host && covering(host.id);
    how = host || override === 'NONE' ? 'Override' : `Override (unknown host ${override})`;
  } else if (code) {
    host = ctx.byVoucher[code];
    session = covering(host.id);
    how = 'Voucher ' + code;
  } else if (isNaN(t)) {
    how = 'No order date';
  } else if (isLive_(o.source) !== false && (session = covering())) {
    if (isLive_(o.source) || CONFIG.COUNT_TIME_ONLY) {
      host = ctx.hosts[session.hostId] || { id: session.hostId, name: session.hostName, rate: 0 };
      how = isLive_(o.source) ? 'Live source + time' : 'Time only';
    } else {
      how = 'Time only (not counted)';
      session = null;
    }
  }
  o.hostId = host ? host.id : '';
  o.hostName = host ? host.name : '';
  o.sessionId = session ? session.id : '';
  o.matchedBy = how;
  o.commission = host ? round2_(Number(o.amount || 0) * host.rate / 100) : 0;
}

function context_(now) {
  const hosts = {};
  const byVoucher = {};
  readHosts_().forEach(h => {
    hosts[h.id] = h;
    h.vouchers.forEach(v => { byVoucher[v] = h; });
  });
  return { hosts: hosts, byVoucher: byVoucher, sessions: readSessions_(now) };
}

// ---------- Payout ----------

function createPayout() {
  const ui = SpreadsheetApp.getUi();
  const now = new Date();
  const lastMonthEnd = formatDate_(new Date(now.getFullYear(), now.getMonth(), 0));
  const res = ui.prompt('Create payout',
    `Pay commission on COMPLETED orders placed on or before this date (yyyy-mm-dd).\nLeave empty for ${lastMonthEnd}.`,
    ui.ButtonSet.OK_CANCEL);
  if (res.getSelectedButton() !== ui.Button.OK) return;
  const d = parseDate_(res.getResponseText().trim() || lastMonthEnd);
  if (!d) return ui.alert('Not a date: ' + res.getResponseText());
  ui.alert('Payout', makePayout_(new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59)), ui.ButtonSet.OK);
}

function makePayout_(cutoff) {
  return withLock_(() => {
    const now = new Date();
    const id = 'P' + Utilities.formatDate(now, tz_(), 'yyyyMMdd-HHmm');
    const sheet = getSheet_(CONFIG.SHEETS.ORDERS);
    const orders = readOrders_(sheet);
    const lines = [];
    let waiting = 0, waitingComm = 0;
    orders.forEach(o => {
      if (!o.hostId) return;
      if (!o.payoutId) {
        if (!(o.created instanceof Date) || o.created > cutoff) return;
        if (o.state === 'COMPLETED' && o.commission > 0) {
          o.payoutId = id;
          lines.push({ o: o, type: 'Paid', comm: o.commission, sales: Number(o.amount) });
        } else if (o.state === 'PENDING') {
          waiting++;
          waitingComm += Number(o.commission);
        }
      } else if (o.state === 'CANCELLED' && !o.clawbackId) {
        o.clawbackId = id;
        lines.push({ o: o, type: 'Deducted', comm: -o.commission, sales: 0 });
      }
    });
    const waitNote = `${waiting} matched orders up to ${formatDate_(cutoff)} are not completed yet ` +
      `(commission ${round2_(waitingComm)}). They will be paid in a later payout once completed, or never if cancelled.`;
    if (!lines.length) return 'Nothing to pay. ' + waitNote;

    const byHost = {};
    lines.forEach(l => {
      const h = byHost[l.o.hostId] || (byHost[l.o.hostId] = { id: l.o.hostId, name: l.o.hostName, paid: 0, sales: 0, comm: 0, deducted: 0, lines: [] });
      if (l.type === 'Paid') { h.paid++; h.sales += l.sales; h.comm += l.comm; } else { h.deducted += l.comm; }
      h.lines.push(l);
    });
    const hosts = Object.values(byHost).sort((a, b) => a.name.localeCompare(b.name));
    const payouts = getSheet_(CONFIG.SHEETS.PAYOUTS);
    hosts.forEach(h => payouts.appendRow([id, now, cutoff, h.id, h.name, h.paid, round2_(h.sales),
      round2_(h.comm), round2_(h.deducted), round2_(h.comm + h.deducted)]));

    // Statement to hand to accounts: every order behind every amount.
    const st = SpreadsheetApp.getActiveSpreadsheet().insertSheet('Payout ' + id);
    const rows = [['Host ID', 'Host Name', 'Type', 'Platform', 'Order ID', 'Order Date', 'Status', 'Amount', 'Commission']];
    const totals = [];
    hosts.forEach(h => {
      h.lines.sort((a, b) => a.o.created - b.o.created).forEach(l => rows.push([
        h.id, h.name, l.type, l.o.platform, l.o.order, l.o.created, l.o.status, l.sales, l.comm]));
      rows.push(['', 'TOTAL ' + h.name, `${h.paid} orders`, '', '', '', '', round2_(h.sales), round2_(h.comm + h.deducted)]);
      totals.push(rows.length);
      rows.push(['', '', '', '', '', '', '', '', '']);
    });
    st.getRange(1, 5, rows.length, 1).setNumberFormat('@');
    st.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
    st.getRange(2, 6, rows.length - 1, 1).setNumberFormat('yyyy-mm-dd hh:mm');
    st.getRange(1, 1, 1, rows[0].length).setFontWeight('bold');
    totals.forEach(r => st.getRange(r, 1, 1, rows[0].length).setFontWeight('bold'));
    st.setFrozenRows(1);

    writeOrders_(sheet, orders);
    const net = hosts.reduce((a, h) => a + h.comm + h.deducted, 0);
    return [
      `Payout ${id}: ${hosts.length} hosts, total ${round2_(net)}.`,
      ...hosts.map(h => `• ${h.name}: ${h.paid} orders, ${round2_(h.comm)}` + (h.deducted ? `, deducted ${round2_(-h.deducted)}` : '')),
      '', `Statement with every order: sheet "Payout ${id}".`, waitNote,
    ].join('\n');
  });
}

// ---------- Dashboard ----------

/** month = 'yyyy-MM', defaults to this month. */
function getDashboard(month, pin) {
  if (CONFIG.DASHBOARD_PIN && String(pin || '') !== String(CONFIG.DASHBOARD_PIN)) throw new Error('PIN required');
  const now = new Date();
  const monthOf = d => Utilities.formatDate(d, tz_(), 'yyyy-MM');
  month = month || monthOf(now);
  const sessions = readSessions_(now).filter(s => monthOf(new Date(s.start)) === month).sort((a, b) => a.start - b.start);
  const orders = readOrders_(getSheet_(CONFIG.SHEETS.ORDERS))
    .filter(o => o.created instanceof Date && monthOf(o.created) === month);

  const hosts = {};
  const hostRow = (id, name) => hosts[id] || (hosts[id] = {
    id: id, name: name, sessions: 0, hours: 0, orders: 0, sales: 0,
    completed: 0, payable: 0, paid: 0, pending: 0, pendingComm: 0, cancelled: 0, cancelledSales: 0,
  });
  readHosts_().filter(h => h.active).forEach(h => hostRow(h.id, h.name));

  const rows = {};
  sessions.forEach((s, i) => {
    const h = hostRow(s.hostId, s.hostName);
    h.sessions++;
    h.hours += (s.end - s.start) / 3600000;
    const overlap = sessions.slice(0, i)
      .filter(p => p.platform.toLowerCase() === s.platform.toLowerCase() && p.end > s.start).map(p => p.hostName);
    rows[s.id] = {
      id: s.id, host: s.hostName, platform: s.platform,
      start: formatDateTime_(new Date(s.start)),
      end: s.open && !s.cut ? 'LIVE NOW' : formatTime_(new Date(s.end)),
      hours: round2_((s.end - s.start) / 3600000), orders: 0, sales: 0, cancelled: 0,
      flag: s.cut ? `END LIVE not pressed: counted as ${CONFIG.MAX_SESSION_HOURS}h, fix End in Sessions sheet`
        : overlap.length ? 'Overlaps ' + overlap.join(', ') : '',
    };
  });

  const detail = [];
  let notLive = 0;
  const clawbacks = [];
  orders.forEach(o => {
    if (!o.hostId) { notLive++; return; }
    const amount = Number(o.amount) || 0;
    const comm = Number(o.commission) || 0;
    const h = hostRow(o.hostId, o.hostName);
    h.orders++;
    h.sales += amount;
    if (o.state === 'CANCELLED') {
      h.cancelled++;
      h.cancelledSales += amount;
      if (o.payoutId && !o.clawbackId) clawbacks.push(o.order);
    } else if (o.payoutId) h.paid += comm;
    else if (o.state === 'COMPLETED') { h.completed++; h.payable += comm; }
    else { h.pending++; h.pendingComm += comm; }
    const s = rows[o.sessionId];
    if (s) {
      s.orders++;
      s.sales += amount;
      if (o.state === 'CANCELLED') s.cancelled++;
    }
    detail.push({
      hostId: o.hostId, order: o.order, platform: o.platform, at: formatDateTime_(o.created),
      amount: amount, status: String(o.status), state: o.state, commission: comm,
      matchedBy: String(o.matchedBy), payoutId: String(o.payoutId || ''),
    });
  });

  return {
    month: month,
    hosts: Object.values(hosts).map(h => {
      ['hours', 'sales', 'payable', 'paid', 'pendingComm', 'cancelledSales'].forEach(k => { h[k] = round2_(h[k]); });
      h.cancelRate = h.orders ? Math.round(h.cancelled / h.orders * 100) : 0;
      return h;
    }).sort((a, b) => b.sales - a.sales),
    sessions: Object.values(rows).map(s => { s.sales = round2_(s.sales); return s; }),
    orders: detail.sort((a, b) => a.at < b.at ? 1 : -1),
    notLive: notLive,
    clawbacks: clawbacks,
    graceMinutes: CONFIG.GRACE_MINUTES,
  };
}

// ---------- Sheet helpers ----------

function readHosts_() {
  const sheet = getSheet_(CONFIG.SHEETS.HOSTS);
  const last = sheet.getLastRow();
  if (last < 2) return [];
  return sheet.getRange(2, 1, last - 1, HOST_HEADERS.length).getDisplayValues()
    .filter(r => r[0])
    .map(r => ({
      id: r[0].trim().toUpperCase(),
      name: r[1].trim(),
      rate: parseNumber_(r[2]),
      vouchers: r[3].toUpperCase().split(/[\s,;]+/).filter(String),
      active: r[4].trim().toUpperCase() !== 'FALSE',
    }));
}

/** Sessions with start/end in ms. A session with no End runs until now, cut off at MAX_SESSION_HOURS. */
function readSessions_(now) {
  const sheet = getSheet_(CONFIG.SHEETS.SESSIONS);
  const last = sheet.getLastRow();
  if (last < 2) return [];
  const maxMs = CONFIG.MAX_SESSION_HOURS * 3600000;
  const values = sheet.getRange(2, 1, last - 1, SESSION_HEADERS.length).getValues();
  const out = [];
  values.forEach((v, i) => {
    const start = v[4] instanceof Date ? v[4] : parseDate_(String(v[4]));
    if (!v[1] || !start) return;
    const end = v[5] instanceof Date ? v[5] : parseDate_(String(v[5]));
    const s = start.getTime();
    out.push({
      row: i + 2,
      id: String(v[0]),
      hostId: String(v[1]).trim().toUpperCase(),
      hostName: String(v[2]),
      platform: String(v[3]),
      start: s,
      end: end ? end.getTime() : Math.min(now.getTime(), s + maxMs),
      open: !end,
      cut: !end && now.getTime() - s > maxMs,
    });
  });
  return out;
}

function readOrders_(sheet) {
  const last = sheet.getLastRow();
  if (last < 2) return [];
  return sheet.getRange(2, 1, last - 1, ORDER_FIELDS.length).getValues()
    .filter(v => v[1] !== '')
    .map(v => {
      const o = {};
      ORDER_FIELDS.forEach((f, i) => { o[f[0]] = v[i]; });
      o.order = String(o.order).toUpperCase();
      o.hostId = String(o.hostId).toUpperCase();
      if (!(o.created instanceof Date)) o.created = parseDate_(String(o.created));
      return o;
    });
}

function writeOrders_(sheet, orders) {
  const old = sheet.getLastRow();
  if (orders.length) {
    const rows = orders.map(o => ORDER_FIELDS.map(f => o[f[0]] === undefined || o[f[0]] === null ? '' : o[f[0]]));
    sheet.getRange(2, 2, rows.length, 1).setNumberFormat('@');
    sheet.getRange(2, 1, rows.length, ORDER_FIELDS.length).setValues(rows);
  }
  if (old > orders.length + 1) sheet.getRange(orders.length + 2, 1, old - orders.length - 1, ORDER_FIELDS.length).clearContent();
}

function ensureSheet_(ss, name, headers) {
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(headers);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function getSheet_(name) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
  if (!sheet) throw new Error(`Sheet "${name}" not found — run setup() first`);
  return sheet;
}

function withLock_(fn) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try { return fn(); } finally { lock.releaseLock(); }
}

// ---------- Small helpers ----------

/** Reads '2026-10-27 20:15', '27/10/2026 8:15 PM', etc. (order of day/month from CONFIG.DATE_ORDER). */
function parseDate_(s) {
  const m = String(s || '').trim().match(
    /^(\d{1,4})[-\/.](\d{1,2})[-\/.](\d{1,4})(?:[ T,]+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?)?/i);
  if (!m) return null;
  let y, mo, d;
  if (m[1].length === 4 || CONFIG.DATE_ORDER === 'YMD') { y = +m[1]; mo = +m[2]; d = +m[3]; }
  else if (CONFIG.DATE_ORDER === 'MDY') { mo = +m[1]; d = +m[2]; y = +m[3]; }
  else { d = +m[1]; mo = +m[2]; y = +m[3]; }
  if (y < 100) y += 2000;
  let h = +(m[4] || 0);
  if (m[7] && m[7].toUpperCase() === 'PM' && h < 12) h += 12;
  if (m[7] && m[7].toUpperCase() === 'AM' && h === 12) h = 0;
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return null;
  return new Date(y, mo - 1, d, h, +(m[5] || 0), +(m[6] || 0));
}

/** '1,234.50', 'RM 12.90', '5%' → number. */
function parseNumber_(s) {
  let t = String(s || '').replace(/[^\d.,\-]/g, '');
  t = CONFIG.DECIMAL === ',' ? t.replace(/\./g, '').replace(',', '.') : t.replace(/,/g, '');
  const n = parseFloat(t);
  return isNaN(n) ? 0 : n;
}

function summarize_(list) {
  const c = {};
  list.forEach(x => { c[x] = (c[x] || 0) + 1; });
  return Object.keys(c).map(k => `${k} ${c[k]}`).join(', ') || 'none';
}

function key_(platform, order) { return String(platform).toLowerCase() + '|' + String(order).toUpperCase(); }
function round2_(n) { return Math.round(Number(n || 0) * 100) / 100; }
function tz_() { return Session.getScriptTimeZone(); }
function formatDate_(d) { return Utilities.formatDate(d, tz_(), 'yyyy-MM-dd'); }
function formatTime_(d) { return Utilities.formatDate(d, tz_(), 'HH:mm'); }
function formatDateTime_(d) { return Utilities.formatDate(d, tz_(), 'yyyy-MM-dd HH:mm'); }
