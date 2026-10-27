# KOL Tracker

A single-file web app for tracking engaged KOLs (influencers): where each one is in the process, what was discussed and agreed, and whether the promised content has been delivered.

## How to use

Open `index.html` in any browser. You don't need to install anything or run a server.

The first time you open it, three sample KOLs (named "Sample: …") are loaded so you can see how it works. Delete them when you're ready.

## Features

- **Dashboard**: total and active KOLs, content fulfilment %, overdue deliverables, open follow-ups, committed fees, total views, KOLs by stage, upcoming deadlines.
- **KOLs**: a searchable, filterable list (by stage, campaign or platform) with a fulfilment bar for each KOL.
- **Pipeline**: a Kanban board. Drag a KOL card to move it to another stage:
  Prospect → Contacted → Negotiating → Contracted → In Production → Content Review → Published → Completed (or Dropped).
- **KOL profile**: platform, followers, niche, campaign, internal owner, contacts, manager or agency, fee, payment status, notes.
- **Discussions log**: one entry per call, meeting or chat, with a summary, the agreed points (deliverables, rates, dates, usage rights) and a next action with a due date.
- **Content deliverables**: type, platform, quantity, due date, status (Not Started → Brief Sent → Draft Submitted → Revision → Approved → Published), draft and live links, and performance (views, likes, comments, shares).
- **Follow-ups**: every open next action across all KOLs. Overdue items are shown in red.
- **Export / Import**: back up and restore everything as JSON. **CSV** downloads the KOL, content and discussion tables for Excel or Google Sheets.

## Data storage

Your data is saved in the browser you use (localStorage). That means:

- It stays on that browser and device only.
- Clearing your browser data deletes it, so use **Export** regularly to keep a backup.
- To move to another computer, Export there, then Import on the new machine.
