// Assistant manager: Time Planet's AI assistant on Telegram.
// It answers you in a private chat with the bot, and in the group when you
// @mention it, reply to one of its messages or use /ask. Claude writes the answers.
// Telegram sends every message to this script, deployed as a web app (see README.md).
// Secrets are never in code: the bot token is the line after "Assistant manager" in the
// access doc and the Claude API key is the sk-ant-... key in the same doc
// (or script properties TG_TOKEN / ANTHROPIC_API_KEY if set).

var WEB_APP_URL = '';   // paste the Web app URL from Deploy → New deployment here
var ACCESS_DOC = '1o6kk_61Au53DkF2_FI3e-M3OVw0Of2gqrtej7OgFOyQ';  // "access" doc in REPORT
var NOTES_DOC = '';     // optional: id of a Google Doc with extra things the bot should know
var TZ = 'Asia/Kuala_Lumpur';
var MODEL = 'claude-opus-5-5';
var EFFORT = 'low';     // low = quick chat replies; medium or high = more careful, slower and dearer
var HISTORY = 40;       // messages per chat the bot remembers (kept for 6 hours)

var BRIEF = [
  'You are "Assistant manager", the AI assistant manager of Time Planet, a Malaysian online watch retailer.',
  'Time Planet sells watches (Bonia, Casio incl. G-Shock and Baby-G, Bilano Polo and other brands) on TikTok Shop,',
  'Shopee and Lazada, managed through BigSeller. The team: the owner (director), a packing team (pick & label, then',
  'pack & warranty card), live-stream hosts paid commission on completed orders, KOL partners, and a stock manager who',
  'uploads the daily TPSB stock file. A separate "Stock manager" bot posts the restock report in the operation group at 8pm.',
  '',
  'You chat on Telegram with the owner in private and with the team in the operation group. Help with whatever they ask:',
  'answering questions, planning and prioritising work, drafting messages, announcements, SOPs and customer replies,',
  'checking calculations, translating, and summarising the group discussion.',
  '',
  'How to reply:',
  '- Use the language the person writes in (English, Malay or Chinese; mixed is fine).',
  '- Keep it short and practical, like a capable manager on chat: the answer first, then the steps.',
  '  Short lines and simple bullets; no tables.',
  '- Each message starts with [time, sender name]. In the group you also see messages that were not for you, as',
  '  context; answer the latest message addressed to you. Do not start your reply with a [time, name] tag.',
  '- You cannot see live sales, stock or order data, and you cannot send messages, set reminders or change anything',
  '  yourself. If an answer needs data, ask them to paste it or send a screenshot. Never invent figures.',
  '- If something is unclear, ask one short question.',
].join('\n');

var HELP = [
  "Hi, I'm Assistant manager, Time Planet's AI assistant.",
  '• Private chat: just type.',
  '• Group: mention me, reply to my message, or use /ask your question.',
  '• Photos and screenshots work too.',
  '• /reset clears what I remember of this chat. /id shows the chat id.',
  "I can't see sales or stock data unless you paste it or send a screenshot.",
].join('\n');

// ---- run once ----

// One-click setup: remembers the chats the bot has seen (they become the allowed chats,
// private chats are also admins), then points Telegram at this web app.
// Before running it: deploy the web app, send the bot a private message and a message in the group.
function start() {
  var p = props_();
  var url = webAppUrl_();
  CacheService.getScriptCache().removeAll(['sec_tg', 'sec_key']);
  apiKey_();   // fail now, not on the first message, if the Claude key is missing
  var me = tg('getMe', {}).result;
  p.setProperty('BOT_ID', String(me.id));
  p.setProperty('BOT_USERNAME', me.username);

  tg('deleteWebhook', {});   // getUpdates only works without a webhook
  var seen = {};
  (tg('getUpdates', {}).result || []).forEach(function (u) {
    var m = u.message || u.edited_message || u.my_chat_member;
    if (!m || !m.chat) return;
    seen[m.chat.id] = m.chat.title || fullName_(m.chat);
    if (m.chat.type === 'private') addTo_('ADMINS', m.chat.id);
  });
  var fresh = Object.keys(seen).filter(function (id) { return !allowed_(id); });
  fresh.forEach(function (id) { addTo_('ALLOWED_CHATS', id); });
  if (!list_('ALLOWED_CHATS').length)
    throw new Error('No chats found: send the bot a private message and a message in the group, then run start again.');

  var secret = p.getProperty('WEBHOOK_SECRET');
  if (!secret) p.setProperty('WEBHOOK_SECRET', secret = Utilities.getUuid().replace(/-/g, ''));
  tg('setWebhook', {url: url + '?secret=' + secret, allowed_updates: ['message'], drop_pending_updates: true});

  fresh.forEach(function (id) { tg('sendMessage', {chat_id: id, text: HELP}); });
  Logger.log('Bot @' + me.username + ' is listening.');
  Logger.log('Allowed chats: ' + list_('ALLOWED_CHATS').map(function (id) { return id + (seen[id] ? ' (' + seen[id] + ')' : ''); }).join(', '));
  Logger.log('Admins: ' + list_('ADMINS').join(', '));
}

// Shows what Telegram says about the webhook (last error, messages waiting).
function checkWebhook() { Logger.log(JSON.stringify(tg('getWebhookInfo', {}).result, null, 2)); }

// Turns the bot off: Telegram stops sending messages here. Run start to turn it on again.
function stop() { tg('deleteWebhook', {}); Logger.log('Webhook removed: the bot no longer answers.'); }

function webAppUrl_() {
  var url = WEB_APP_URL || ScriptApp.getService().getUrl() || '';
  if (!/^https:\/\/script\.google\.com\/.*\/exec$/.test(url))
    throw new Error('Deploy the script as a web app first, then paste its URL (ending in /exec) into WEB_APP_URL at the top.');
  return url;
}

// ---- every message ----

// Telegram calls this for every message. Always answer 200 quickly-ish; errors are logged.
function doPost(e) {
  try {
    var secret = props_().getProperty('WEBHOOK_SECRET');
    if (secret && e && e.parameter && e.parameter.secret === secret && e.postData) {
      var update = JSON.parse(e.postData.contents);
      // Telegram may send the same update again (it does not follow Apps Script's redirect)
      if (firstTime_('u' + update.update_id)) onMessage(update.message);
    }
  } catch (err) {
    console.error(err && err.stack || err);
  }
  return ContentService.createTextOutput('ok');
}

function onMessage(m) {
  if (!m || !m.chat || !m.from) return;
  var chat = String(m.chat.id), isPrivate = m.chat.type === 'private';
  if (m.migrate_to_chat_id) {   // group upgraded to supergroup: it gets a new id
    if (allowed_(chat)) addTo_('ALLOWED_CHATS', m.migrate_to_chat_id);
    return;
  }
  var me = props_().getProperty('BOT_USERNAME') || '';
  var text = m.text || m.caption || '';
  var cmd = text.match(/^\/(\w+)(?:@(\w+))?\s*([\s\S]*)$/);
  if (cmd && cmd[2] && cmd[2].toLowerCase() !== me.toLowerCase()) return;   // a command for another bot
  var command = cmd ? cmd[1].toLowerCase() : '';
  var mention = me ? new RegExp('@' + me + '\\b', 'ig') : null;
  var addressed = isPrivate || !!command || (me && new RegExp('@' + me + '\\b', 'i').test(text)) ||
    !!(m.reply_to_message && m.reply_to_message.from && String(m.reply_to_message.from.id) === props_().getProperty('BOT_ID'));

  if (command === 'id') return reply_(m, 'Chat id: ' + chat + '\nYour user id: ' + m.from.id);
  if (command === 'allow') {
    if (!isAdmin_(m.from.id)) return reply_(m, 'Only an admin can allow chats.');
    var id = (cmd[3].match(/-?\d+/) || [chat])[0];
    addTo_('ALLOWED_CHATS', id);
    return reply_(m, 'Allowed chat ' + id + '.');
  }
  if (!allowed_(chat)) {
    if (addressed) reply_(m, 'Sorry, I only work for the Time Planet team. Ask the admin to send /allow ' + chat + ' to me.');
    return;
  }
  if (command === 'start' || command === 'help') return reply_(m, HELP);
  if (command === 'reset') {
    CacheService.getScriptCache().remove('h' + chat);
    return reply_(m, 'Done, I have forgotten this chat.');
  }
  if (command === 'ask') text = cmd[3];
  if (mention) text = text.replace(mention, '').trim();

  var image = imageOf_(m);
  var line = '[' + Utilities.formatDate(new Date(m.date * 1000), TZ, 'EEE d MMM yyyy HH:mm') + ', ' + fullName_(m.from) + ']: ';
  var quoted = m.reply_to_message;
  if (quoted && String(quoted.from && quoted.from.id) !== props_().getProperty('BOT_ID') && (quoted.text || quoted.caption))
    line += '(replying to ' + fullName_(quoted.from || {}) + ': "' + (quoted.text || quoted.caption).slice(0, 500) + '") ';
  line += (text || (image ? '' : '(no text)')) + (image ? ' [sent a photo]' : '');
  if (!text && !image && !m.photo && (m.document || m.voice || m.video || m.sticker || m.audio)) {
    if (addressed) reply_(m, 'I can read text and photos only, for now.');
    return;
  }
  var history = remember_(chat, 'user', line);
  if (!addressed) return;   // group chatter: kept as context only

  tg('sendChatAction', {chat_id: chat, action: 'typing'});
  var answer;
  try {
    var messages = toMessages_(history);
    if (image) {
      var last = messages[messages.length - 1];
      last.content = [{type: 'image', source: {type: 'base64', media_type: image.type, data: download_(image.fileId)}},
        {type: 'text', text: last.content}];
    }
    answer = askClaude_(messages);
  } catch (err) {
    console.error(err && err.stack || err);
    return reply_(m, "Sorry, I couldn't answer just now (" + String(err.message || err).slice(0, 200) + '). Please try again.');
  }
  remember_(chat, 'assistant', answer);
  reply_(m, answer);
}

// Biggest photo size, or an image sent as a file; null if none (or too big for Claude)
function imageOf_(m) {
  if (m.photo && m.photo.length) {
    var p = m.photo[m.photo.length - 1];
    if ((p.file_size || 0) <= 5e6) return {fileId: p.file_id, type: 'image/jpeg'};
  }
  var d = m.document;
  if (d && /^image\/(jpeg|png|gif|webp)$/.test(d.mime_type || '') && (d.file_size || 0) <= 5e6)
    return {fileId: d.file_id, type: d.mime_type};
  return null;
}

function download_(fileId) {
  var path = tg('getFile', {file_id: fileId}).result.file_path;
  var r = UrlFetchApp.fetch('https://api.telegram.org/file/bot' + token_() + '/' + path);
  return Utilities.base64Encode(r.getBlob().getBytes());
}

// ---- memory (script cache, 6 hours per chat) ----

function remember_(chat, role, text) {
  var cache = CacheService.getScriptCache(), lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var h = JSON.parse(cache.get('h' + chat) || '[]');
    h.push({r: role, t: String(text).slice(0, 4000)});
    while (h.length > HISTORY || (h.length > 1 && JSON.stringify(h).length > 90000)) h.shift();
    cache.put('h' + chat, JSON.stringify(h), 21600);
    return h;
  } finally {
    lock.releaseLock();
  }
}

// History -> Claude messages: starts with the user, roles alternate (same-role lines are joined)
function toMessages_(h) {
  var out = [];
  h.forEach(function (x) {
    var role = x.r === 'assistant' ? 'assistant' : 'user';
    if (!out.length && role !== 'user') return;
    var last = out[out.length - 1];
    if (last && last.role === role) last.content += '\n' + x.t;
    else out.push({role: role, content: x.t});
  });
  return out;
}

// True the first time a key is seen in 6 hours
function firstTime_(key) {
  var cache = CacheService.getScriptCache(), lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    if (cache.get(key)) return false;
    cache.put(key, '1', 21600);
    return true;
  } finally {
    lock.releaseLock();
  }
}

// ---- Claude ----

function askClaude_(messages) {
  var body = {model: MODEL, max_tokens: 16000, system: systemPrompt_(), output_config: {effort: EFFORT}, messages: messages};
  var headers = {'x-api-key': apiKey_(), 'anthropic-version': '2026-10-21'};
  if (!/haiku/i.test(MODEL)) {   // if the model declines for safety reasons, Anthropic retries on a suitable model
    body.fallbacks = 'default';
    headers['anthropic-beta'] = 'server-side-fallback-2026-07-01';
  }
  for (var attempt = 0; ; attempt++) {
    var r = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', {method: 'post', contentType: 'application/json',
      headers: headers, payload: JSON.stringify(body), muteHttpExceptions: true});
    var code = r.getResponseCode();
    if ((code === 429 || code >= 500) && attempt < 2) { Utilities.sleep(3000 * (attempt + 1)); continue; }
    var res;
    try { res = JSON.parse(r.getContentText()); } catch (e) { res = {}; }
    if (code !== 200) throw new Error('Claude API ' + code + ': ' + (res.error && res.error.message || r.getContentText().slice(0, 200)));
    if (res.stop_reason === 'refusal') return "Sorry, I can't help with that one.";
    var text = (res.content || []).filter(function (b) { return b.type === 'text'; })
      .map(function (b) { return b.text; }).join('').trim()
      .replace(/^\[[^\]\n]{0,80}\]:?\s*/, '');   // in case it copies the [time, name] tag
    if (res.stop_reason === 'max_tokens') text += '\n… (cut off)';
    return text || '(no answer)';
  }
}

function systemPrompt_() {
  if (!NOTES_DOC) return BRIEF;
  var cache = CacheService.getScriptCache(), notes = cache.get('notes');
  if (notes === null) {
    notes = DocumentApp.openById(NOTES_DOC).getBody().getText().trim().slice(0, 50000);
    cache.put('notes', notes, 600);
  }
  return notes ? BRIEF + '\n\nNotes from the owner (company facts, rules, prices):\n' + notes : BRIEF;
}

// ---- Telegram ----

// Sends the text as a reply (in groups), split to Telegram's 4096-character limit.
// Claude's Markdown is turned into Telegram HTML; if Telegram rejects that, plain text is sent.
function reply_(m, text) {
  var parts = [];
  while (text.length) {
    var cut = text.length <= 3500 ? text.length : Math.max(text.lastIndexOf('\n', 3500), 1000);
    parts.push(text.slice(0, cut));
    text = text.slice(cut).replace(/^\n+/, '');
  }
  parts.forEach(function (part, i) {
    var msg = {chat_id: m.chat.id, text: part, disable_web_page_preview: true};
    if (i === 0 && m.chat.type !== 'private') msg.reply_parameters = {message_id: m.message_id, allow_sending_without_reply: true};
    try {
      tg('sendMessage', Object.assign({}, msg, {text: toHtml_(part), parse_mode: 'HTML'}));
    } catch (e) {
      tg('sendMessage', msg);
    }
  });
}

function toHtml_(s) {
  var code = [];
  s = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/```\w*\n?([\s\S]*?)```/g, function (_, c) { code.push('<pre>' + c.replace(/\n$/, '') + '</pre>'); return '\u0000' + (code.length - 1) + '\u0000'; })
    .replace(/`([^`\n]+)`/g, function (_, c) { code.push('<code>' + c + '</code>'); return '\u0000' + (code.length - 1) + '\u0000'; })
    .replace(/^#{1,6}\s+(.+)$/gm, '<b>$1</b>')
    .replace(/^(\s*)[*-]\s+/gm, '$1• ')
    .replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>')
    .replace(/__([^_\n]+)__/g, '<b>$1</b>')
    .replace(/(^|[^*\w])\*([^*\s][^*\n]*?)\*(?!\w)/g, '$1<i>$2</i>')
    .replace(/\[([^\]\n]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2">$1</a>');
  return s.replace(/\u0000(\d+)\u0000/g, function (_, i) { return code[+i]; });
}

// Assistant manager bot token: script property TG_TOKEN, else the line after "Assistant manager" in the access doc
function token_() {
  return secret_('sec_tg', 'TG_TOKEN', /Assistant manager\s+(\d+:[A-Za-z0-9_-]+)/i, 'Assistant manager token');
}

// Claude API key: script property ANTHROPIC_API_KEY, else the sk-ant-... key in the access doc
function apiKey_() {
  return secret_('sec_key', 'ANTHROPIC_API_KEY', /(sk-ant-[A-Za-z0-9_-]+)/, 'Claude API key (sk-ant-...)');
}

// Reading the doc takes about a second, so the value is cached for an hour
function secret_(cacheKey, prop, re, label) {
  var v = props_().getProperty(prop);
  if (v) return v;
  var cache = CacheService.getScriptCache();
  if ((v = cache.get(cacheKey))) return v;
  var m = DocumentApp.openById(ACCESS_DOC).getBody().getText().match(re);
  if (!m) throw new Error(label + ' not found in the access doc.');
  cache.put(cacheKey, m[1], 3600);
  return m[1];
}

function tg(method, payload) {
  var r = UrlFetchApp.fetch('https://api.telegram.org/bot' + token_() + '/' + method,
    {method: 'post', contentType: 'application/json', payload: JSON.stringify(payload), muteHttpExceptions: true});
  var body = JSON.parse(r.getContentText());
  if (!body.ok) throw new Error('Telegram ' + method + ': ' + body.description);
  return body;
}

// ---- small helpers ----

function props_() { return PropertiesService.getScriptProperties(); }
function list_(key) { return (props_().getProperty(key) || '').split(',').filter(String); }
function addTo_(key, id) {
  var l = list_(key);
  if (l.indexOf(String(id)) < 0) props_().setProperty(key, l.concat(String(id)).join(','));
}
function allowed_(chat) { return list_('ALLOWED_CHATS').indexOf(String(chat)) >= 0; }
function isAdmin_(user) { return list_('ADMINS').indexOf(String(user)) >= 0; }
function fullName_(u) { return [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username || 'Someone'; }
