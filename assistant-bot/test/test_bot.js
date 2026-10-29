// Runs Code.gs with fake Google, Telegram and Claude services: start(), then messages
// arriving through doPost in a private chat, the group and an unknown chat.
// Usage: node assistant-bot/test/test_bot.js
const fs = require('fs'), path = require('path'), vm = require('vm');
const props = {}, cache = {}, tgCalls = [], claudeCalls = [], errors = [];
let claudeReplies = [], failHtml = false;
const resp = (code, obj) => ({getResponseCode: () => code, getContentText: () => typeof obj === 'string' ? obj : JSON.stringify(obj),
  getBlob: () => ({getBytes: () => [1, 2, 3]})});
const GROUP = -1001234, OWNER = 7161173460, STRANGER = 555, BOT = 999;
const g = {
  console: {error: (e) => errors.push(String(e)), log: console.log},
  Logger: {log: () => {}},
  Utilities: {formatDate: (d) => d.toISOString().slice(0, 16), getUuid: () => 'aaaa-bbbb', sleep: () => {},
    base64Encode: (b) => Buffer.from(b).toString('base64')},
  PropertiesService: {getScriptProperties: () => ({getProperty: (k) => props[k] || null, setProperty: (k, v) => { props[k] = String(v); }})},
  CacheService: {getScriptCache: () => ({get: (k) => k in cache ? cache[k] : null, put: (k, v) => { cache[k] = String(v); },
    remove: (k) => { delete cache[k]; }, removeAll: (ks) => ks.forEach((k) => delete cache[k])})},
  LockService: {getScriptLock: () => ({waitLock: () => {}, releaseLock: () => {}})},
  DocumentApp: {openById: () => ({getBody: () => ({getText: () =>
    'Assistant manager\n\n111:AAassist\n\n\nStock manager\n\n222:AAstock_x-y\n\nClaude API key\nsk-ant-api03-Ab_c-9\n'})})},
  ScriptApp: {getService: () => ({getUrl: () => 'https://script.google.com/macros/s/XYZ/exec'})},
  ContentService: {createTextOutput: (t) => ({text: t})},
  UrlFetchApp: {fetch: (url, opt) => {
    let m;
    if (url === 'https://api.anthropic.com/v1/messages') {
      claudeCalls.push({headers: opt.headers, body: JSON.parse(opt.payload)});
      const r = claudeReplies.shift() || [200, {content: [{type: 'thinking', thinking: ''}, {type: 'text', text: 'Answer **bold**'}], stop_reason: 'end_turn'}];
      return resp(r[0], r[1]);
    }
    if (url.startsWith('https://api.telegram.org/file/bot111:AAassist/')) return resp(200, '');
    if ((m = url.match(/api\.telegram\.org\/bot([^/]+)\/(\w+)$/))) {
      const body = JSON.parse(opt.payload);
      tgCalls.push({token: m[1], method: m[2], body});
      if (m[2] === 'getMe') return resp(200, {ok: true, result: {id: BOT, username: 'TP_assistant_bot'}});
      if (m[2] === 'getUpdates') return resp(200, {ok: true, result: [
        {update_id: 1, message: {chat: {id: GROUP, type: 'supergroup', title: 'Time Planet Operation'}, from: {id: OWNER}}},
        {update_id: 2, message: {chat: {id: OWNER, type: 'private', first_name: 'Boss'}, from: {id: OWNER}}}]});
      if (m[2] === 'getFile') return resp(200, {ok: true, result: {file_path: 'photos/a.jpg'}});
      if (m[2] === 'sendMessage' && failHtml && body.parse_mode) return resp(400, {ok: false, description: "can't parse entities"});
      return resp(200, {ok: true, result: {}});
    }
    throw new Error('unexpected fetch ' + url);
  }},
};
const ctx = vm.createContext(g);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'Code.gs'), 'utf8'), ctx);
let bad = 0; const check = (n, ok) => { console.log((ok ? 'ok   ' : 'FAIL ') + n); if (!ok) bad++; };

let uid = 100, mid = 1;
const post = (chatId, type, text, extra = {}, secret = props.WEBHOOK_SECRET, updateId = ++uid) => {
  tgCalls.length = 0; claudeCalls.length = 0;
  const message = Object.assign({message_id: ++mid, date: 1793000000, chat: {id: chatId, type}, from: {id: OWNER, first_name: 'Boss'}, text}, extra);
  if (text === undefined) delete message.text;
  ctx.__e = {parameter: {secret}, postData: {contents: JSON.stringify({update_id: updateId, message})}};
  return vm.runInContext('doPost(__e)', ctx);
};
const sent = () => tgCalls.filter((c) => c.method === 'sendMessage');

// ---- start ----
vm.runInContext('start()', ctx);
const hook = tgCalls.find((c) => c.method === 'setWebhook');
check('token from the access doc (Assistant manager line)', tgCalls.every((c) => c.token === '111:AAassist'));
check('webhook set to the web app with a secret', hook && hook.body.url === 'https://script.google.com/macros/s/XYZ/exec?secret=aaaabbbb' && hook.body.drop_pending_updates);
check('group and private chat allowed', props.ALLOWED_CHATS === GROUP + ',' + OWNER);
check('private chat user is admin', props.ADMINS === String(OWNER));
check('hello sent to both chats', sent().length === 2);

// ---- private chat ----
const r = post(OWNER, 'private', 'How many boxes for 300 orders?');
check('doPost answers ok', r.text === 'ok');
check('Claude called once', claudeCalls.length === 1);
const c = claudeCalls[0] || {body: {}, headers: {}};
check('Claude key from the access doc', c.headers['x-api-key'] === 'sk-ant-api03-Ab_c-9' && c.headers['anthropic-version']);
check('model, effort, fallback, no sampling params', c.body.model === 'claude-opus-5-5' && c.body.output_config.effort === 'low' &&
  c.body.fallbacks === 'default' && c.headers['anthropic-beta'] === 'server-side-fallback-2026-07-01' && !('temperature' in c.body));
check('system prompt is the brief', /Assistant manager/.test(c.body.system));
check('user message has time and name', c.body.messages.length === 1 && /^\[.+, Boss\]: How many boxes/.test(c.body.messages[0].content));
check('reply in HTML, thinking block ignored', sent().length === 1 && sent()[0].body.text === 'Answer <b>bold</b>' &&
  sent()[0].body.parse_mode === 'HTML' && sent()[0].body.chat_id === OWNER);
check('typing shown', tgCalls.some((t) => t.method === 'sendChatAction'));

post(OWNER, 'private', 'And for 600?');
const msgs = claudeCalls[0].body.messages;
check('remembers the conversation', msgs.length === 3 && msgs[1].role === 'assistant' && msgs[1].content === 'Answer **bold**');

// ---- duplicates and bad secret ----
post(OWNER, 'private', 'dup', {}, props.WEBHOOK_SECRET, 5000);
post(OWNER, 'private', 'dup', {}, props.WEBHOOK_SECRET, 5000);
check('same update twice is answered once', claudeCalls.length === 0 && sent().length === 0);
post(OWNER, 'private', 'hack', {}, 'wrong');
check('wrong secret ignored', claudeCalls.length === 0 && tgCalls.length === 0);

// ---- group ----
post(GROUP, 'supergroup', 'Ali: printer is jammed again', {from: {id: 42, first_name: 'Ali'}});
check('group chatter: no reply, no Claude', claudeCalls.length === 0 && sent().length === 0);
post(GROUP, 'supergroup', '@TP_assistant_bot what should we do?');
const gm = claudeCalls[0] && claudeCalls[0].body.messages;
check('mention in group: Claude sees earlier chatter', gm && gm.length === 1 && /printer is jammed/.test(gm[0].content) &&
  /what should we do\?$/.test(gm[0].content) && !/@TP_assistant_bot/.test(gm[0].content));
check('group reply quotes the message', sent().length === 1 && sent()[0].body.reply_parameters && sent()[0].body.chat_id === GROUP);
post(GROUP, 'supergroup', 'thanks, and the label printer?', {reply_to_message: {message_id: 1, from: {id: BOT, is_bot: true}, text: 'x'}});
check('reply to the bot is answered', claudeCalls.length === 1);
post(GROUP, 'supergroup', '/ask summarise today');
check('/ask works', claudeCalls.length === 1 && /summarise today$/.test(claudeCalls[0].body.messages.slice(-1)[0].content));
post(GROUP, 'supergroup', '/report@StockManagerBot');
check('command for another bot ignored', claudeCalls.length === 0 && tgCalls.length === 0);
post(GROUP, 'supergroup', 'summarise this @TP_assistant_bot', {reply_to_message: {message_id: 1, from: {id: 42, first_name: 'Ali'}, text: 'stock of BNB10986 is 3'}});
check('quoted message passed to Claude', /replying to Ali: "stock of BNB10986 is 3"/.test(claudeCalls[0].body.messages.slice(-1)[0].content));
post(GROUP, 'supergroup', '/reset');
check('/reset clears memory', !cache['h' + GROUP] && /forgotten/.test(sent()[0].body.text));

// ---- unknown chats ----
post(STRANGER, 'private', 'hi', {from: {id: STRANGER, first_name: 'X'}});
check('stranger refused without Claude', claudeCalls.length === 0 && /only work for the Time Planet team/.test(sent()[0].body.text));
post(-100777, 'supergroup', 'hello all', {from: {id: STRANGER}});
check('unknown group chatter ignored', tgCalls.length === 0);
post(-100777, 'supergroup', '/allow', {from: {id: STRANGER}});
check('non-admin cannot /allow', !/-100777/.test(props.ALLOWED_CHATS));
post(-100777, 'supergroup', '/allow');
check('admin /allow in a new group', props.ALLOWED_CHATS.split(',').includes('-100777'));

// ---- photo, long answer, fallbacks, errors ----
post(OWNER, 'private', undefined, {photo: [{file_id: 's', file_size: 100}, {file_id: 'big', file_size: 2000}], caption: 'what is wrong here?'});
const pc = claudeCalls[0] && claudeCalls[0].body.messages.slice(-1)[0].content;
check('photo sent to Claude as an image', Array.isArray(pc) && pc[0].type === 'image' && pc[0].source.data === 'AQID' &&
  /what is wrong here\? \[sent a photo\]$/.test(pc[1].text) && tgCalls.some((t) => t.method === 'getFile' && t.body.file_id === 'big'));
post(OWNER, 'private', undefined, {voice: {file_id: 'v'}});
check('voice note: polite no', claudeCalls.length === 0 && /text and photos only/.test(sent()[0].body.text));

claudeReplies = [[200, {content: [{type: 'text', text: ('line of text\n').repeat(700)}], stop_reason: 'end_turn'}]];
post(OWNER, 'private', 'long please');
check('long answer split under 4096', sent().length === 3 && sent().every((s) => s.body.text.length <= 4096));

failHtml = true;
post(OWNER, 'private', 'x');
failHtml = false;
check('HTML rejected: plain text sent', sent().length === 2 && !sent()[1].body.parse_mode && sent()[1].body.text === 'Answer **bold**');

claudeReplies = [[529, {error: {message: 'Overloaded'}}]];
post(OWNER, 'private', 'retry?');
check('overloaded: retried and answered', claudeCalls.length === 2 && sent()[0].body.text === 'Answer <b>bold</b>');

claudeReplies = [[400, {error: {message: 'bad request'}}]];
post(OWNER, 'private', 'error?');
check('API error logged', errors.length === 1 && /Claude API 400/.test(errors[0]));
check('API error: apology to the user', /couldn't answer just now \(Claude API 400: bad request\)/.test(sent()[0].body.text));

claudeReplies = [[200, {content: [], stop_reason: 'refusal'}]];
post(OWNER, 'private', 'refuse?');
check('refusal handled', /can't help with that/.test(sent()[0].body.text));

claudeReplies = [[200, {content: [{type: 'text', text: '[Wed 29 Oct, Assistant manager]: Hi'}], stop_reason: 'end_turn'}]];
post(OWNER, 'private', 'tag?');
check('copied [time, name] tag removed', sent()[0].body.text === 'Hi');

const hist = JSON.parse(cache['h' + OWNER]);
check('memory capped', hist.length <= 40);
const roles = vm.runInContext('toMessages_', ctx)(hist).map((x) => x.role);
check('messages alternate and start with user', roles[0] === 'user' && roles.every((x, i) => !i || x !== roles[i - 1]));

const html = vm.runInContext('toHtml_', ctx);
check('markdown to Telegram HTML', html('# Plan\n- a < b & c\n* *soon*\n`x<y`\n```\nA**B\n```\n[link](https://x.com/a?b=1&c=2)') ===
  '<b>Plan</b>\n• a &lt; b &amp; c\n• <i>soon</i>\n<code>x&lt;y</code>\n<pre>A**B</pre>\n<a href="https://x.com/a?b=1&amp;c=2">link</a>');

check('no other errors logged', errors.length === 1);
console.log(bad ? `FAILED: ${bad}` : 'ALL OK');
process.exit(bad ? 1 : 0);
