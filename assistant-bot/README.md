# Assistant manager bot: chat with it on Telegram

The **Assistant manager** bot reads your messages and answers them. Claude writes the answers.

- **Private chat with the bot:** it answers every message.
- **Time Planet group:** it answers when you:
  - @mention it (`@YourBotName what should we do?`);
  - reply to one of its messages;
  - type `/ask your question`.

  It also reads the other messages in the group, so "@bot summarise this" works.
- **Photos and screenshots:** send them with a question in the caption, for example a sales screenshot.
- **Languages:** English, Malay or Chinese. It answers in the language you write in.
- **Commands:**
  - `/reset` makes it forget the chat.
  - `/id` shows the chat id.
  - `/help` shows how to use it.
- **Memory:** it remembers the last 40 messages of each chat for 6 hours.

It can't see live sales, stock or order data, and it can't send messages, set reminders or change anything on its own.
For a question that needs data, paste the numbers or send a screenshot. It has been told not to make up figures.

It's one Google Apps Script file (`Code.gs`) that runs as a web app, so there's no server to keep running.
Telegram sends each message to the script, the script asks Claude, and the bot posts the answer.

## What you need

- **The Assistant manager bot token.** It's already in the
  ["access" doc](https://docs.google.com/document/d/1o6kk_61Au53DkF2_FI3e-M3OVw0Of2gqrtej7OgFOyQ/edit), on the line after
  "Assistant manager".
- **A Claude API key:**
  1. Sign in at [platform.claude.com](https://platform.claude.com) and add credit under **Billing**.
  2. Under **API keys**, click **Create key**. The key starts with `sk-ant-`.
  3. Add two lines to the access doc: `Claude API key`, then the key on the next line.

  The script finds the key there itself.

**Cost:** about 1–3 US cents per answer. Group messages that aren't addressed to the bot cost nothing.
In the Claude console, set a monthly limit under **Limits**.

## Setup (once, about 10 minutes, on a computer, signed in as timeplanet199@gmail.com)

1. **Let the bot read the group.** In Telegram:
   1. Open **@BotFather** and send `/mybots`.
   2. Pick the Assistant manager bot, then **Bot Settings → Group Privacy → Turn off**.
   3. Remove the bot from the **Time Planet operation group**, then add it again. The change only applies after this.

   Without this step, Telegram doesn't pass @mentions to the bot. It would only see `/ask` and replies to its own
   messages.
2. **Say hello to the bot.** Open a private chat with the bot, press **Start** and send "hi". Then send any message in
   the group. The script uses these to learn which chats are yours. Whoever messages the bot privately becomes an
   admin.
3. **Create the script.**
   1. Open [script.google.com](https://script.google.com) and click **New project**.
   2. Name it "Assistant manager bot".
   3. Delete the sample code, paste in all of [`Code.gs`](Code.gs), then click **Save** (Ctrl+S).
4. **Deploy it as a web app.**
   1. Click **Deploy → New deployment**.
   2. Click the gear next to "Select type" and choose **Web app**.
   3. Set **Execute as:** *Me*. Set **Who has access:** *Anyone*. Telegram needs to reach it, and the script ignores
      anything that doesn't carry its secret code.
   4. Click **Deploy** and allow the permissions:
      - Review permissions → choose the account → Advanced → "Go to … (unsafe)" → Allow.
      - It's your own script.
   5. Copy the **Web app URL**. It ends in `/exec`.
5. **Paste the URL into the script.** At the top of the code, paste it between the quotes of
   `var WEB_APP_URL = '';`, then click **Save**.
6. **Run `start`.** In the function list at the top of the editor, pick **start** and click **Run**. It:
   - finds the group and your private chat, and allows only those;
   - points Telegram at the web app;
   - posts a short hello in both chats.
7. **Test it.** Message the bot privately, and @mention it in the group.

If `start` says no chats were found, send the bot another message (step 2) and run `start` again.

## Day to day

- **A new group or person:**
  - **Group:** add the bot. As an admin, send `/allow` in that group.
  - **Person:** they send the bot a message, and it replies with their chat id. As an admin, send `/allow <id>` to the
    bot.

  Anyone else gets "Sorry, I only work for the Time Planet team", so strangers can't run up your Claude bill.
- **Teach it about the business:**
  1. Create a Google Doc with facts, rules, prices or SOPs.
  2. Put its id in `NOTES_DOC` at the top of the code. The id is the long part of the doc's link between `/d/` and
     `/edit`.

  The bot reads the doc every 10 minutes.
- **Turn it off:** run `stop`. Run `start` to turn it back on.
- **Something wrong:**
  - Run `checkWebhook` and read the log.
  - Look under **Executions** in the script editor.

  A `302 Moved Temporarily` error in `checkWebhook` is normal for Apps Script. If Telegram sends a message twice, the
  bot still answers it only once.

## Changing the code or settings

The settings are at the top of `Code.gs`:

| Setting | What it does |
|---|---|
| `MODEL` | `claude-opus-5-5` gives the best answers. `claude-sonnet-5-5` costs about half as much; `claude-haiku-5-5` is much cheaper but weaker. |
| `EFFORT` | `low` gives quick chat replies. `medium` or `high` think harder, but are slower and cost more. |
| `HISTORY` | How many messages per chat it remembers. |
| `BRIEF` | Who the bot is and how it should answer. Edit it to change its tone or rules. |

After any change, click **Save**, then **Deploy → Manage deployments**. Click the pencil, set **Version** to
**New version**, and click **Deploy**. The URL stays the same. If you only click Save, Telegram keeps talking to the
old version.

## Test

`test/test_bot.js` runs `Code.gs` in Node with fake Telegram, Google and Claude services. It covers:
- `start()`, the secrets read from the access doc, and the webhook secret;
- private chats, group @mentions, replies to the bot, `/ask`, `/reset` and `/allow`;
- strangers and duplicate updates;
- photos, long answers, the formatting fallback, and retries and errors from Claude.

```bash
node assistant-bot/test/test_bot.js
```

It hasn't been run against the real Telegram and Claude services yet. The setup steps above are the first real test.
