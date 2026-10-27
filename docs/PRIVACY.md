# What the Tiiny keeps about your chats

Checked 2026-10-27 on device services 0.1.36, with labelled test chats. Corrections welcome.

## What happens to a chat

- **Every chat sent to the device's API is captured**, not only TiinyOS's own: other apps (Hermes, Cline, scripts,
  anything using `/v1/chat/completions`) included. On an idle device the day's vault entry
  (`GET /kb/conversation_days/{day}`) didn't change for 9 minutes; one chat sent straight to the API changed its
  `content_updated_at` 14 seconds later. Captures are batched (they land on whole minutes).
- The vault collects them per day as a **conversation day**, for its optional **daily summary** (memory facts
  written overnight by a model you pick in TiinyOS). Without a summary model nothing becomes memory, but the
  days are kept with status `queued`.
- **TiinyOS doesn't show these**, and the API doesn't return their text (`journal_text` stays empty,
  `/kb/files/{source_id}` 404s for the day file).
- **The "memory scope" setting doesn't stop it.** `GET/PUT /kb/memory/scope` (`all` or `tiinyos`, added in the
  2026-10 update; the spec calls it the *summary* scope). After switching to `tiinyos`, an API chat was still
  captured the same way. At most it narrows what gets summarised.
- Days that were summarised also produced **facts** (`/kb/memory/facts`) and proposals.

## What you can delete through the API

```bash
curl -H "Authorization: Bearer YOUR_KEY" "http://192.168.1.50/kb/conversation_days?limit=500"
curl -X DELETE -H "Authorization: Bearer YOUR_KEY" "http://192.168.1.50/kb/conversation_days/2026-10-26"
```

- It removes the **whole day**, including that day's TiinyOS chats in the vault (they stay in TiinyOS's own chat
  history). There's no per-chat delete. It can't be undone.
- **Tested on a day that hadn't been summarised:** the day was gone from the list and its text from the vault, and
  the vault didn't re-import it afterwards.
- The response includes `deleted_facts`, `deleted_proposals`, `deleted_source` and `deleted_journal_file`, so it
  is meant to remove what was summarised from that day as well. **Not tested yet on a summarised day.**
- Facts and proposals can also be removed one by one: `DELETE /kb/memory/facts/{id}`,
  `POST /kb/memory/proposals/{id}/reject`.

## What the API can't remove

The device keeps its own record of requests to its models in addition to the vault's copy, and the API offers no
way to see or delete it. I've reported this to Tiiny and am waiting for their answer.

## If you want to be sure nothing leaves your network

Block the Tiiny's internet access in your router and allow it only when you update TiinyOS or download models.
Local use over Wi-Fi/LAN and USB keeps working.
