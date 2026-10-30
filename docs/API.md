# Tiiny device API reference

Everything the Tiiny Pocket answers on the network, in one place. **Unofficial.** First collected
2026-10-25 against TiinyOS 0.1.35, rechecked 2026-10-27 after the update to device services **0.1.36**
(gateway spec unchanged, 37 endpoints; vault 54 → 59). Sources, marked per endpoint:

| mark | meaning |
|---|---|
| **tested** | called and checked against a real device |
| **spec** | in an OpenAPI spec the device publishes (exact paths and schemas) |
| **docs** | in Tiiny's developer docs (dev.tiiny.ai), with example requests |
| **app** | only seen in the TiinyOS desktop app's code; behaviour not checked |

After a TiinyOS update, run `python tools/api_snapshot.py --check`: it refetches the device's specs, lists every
added/removed/changed endpoint, regenerates [endpoints/gateway.md](endpoints/gateway.md) and
[endpoints/kb.md](endpoints/kb.md), and probes the read-only routes below.

## Services and ports

| port | service | reachable over | notes |
|---|---|---|---|
| **80** | gateway: routes to everything below | Wi-Fi/LAN and USB | the only port you normally need |
| 80 `/api/v1/sys`, `/api/v1/account`, `/api/v1/apps`, `/api/v1/webapp`, `/api/v1/chat/history` | system & account service (FastAPI) | " | **spec**: `/openapi.json`, `/docs` → [endpoints/gateway.md](endpoints/gateway.md) |
| 80 `/api/v1/models`, `/api/v1/npu`, `/v1/*`, `/api/tags`, `/api/chat` | model service (also on 8800 on the device) | " | no published spec; documented below |
| 80 `/kb/*` | knowledge base / vault ("SimpleMem") | " | **spec**: `/kb/openapi.json`, `/kb/docs` → [endpoints/kb.md](endpoints/kb.md) |
| 80 `/v1/config`, `/v1/<connector>/…`, `/v1/mcp/…` | on-device assistant: connectors and MCP | " | **docs** |
| 80 `/api/services` | app services (Tiiny App Farm) | " | **docs**/**app** |
| dynamic | each loaded model's own container | Wi-Fi/LAN only | port from `GET /api/v1/models/running`; no auth |
| 8800 | model service directly | on the device only | the docs use `:8800`; not reachable from the network |
| 5555 | upgrade/OTA service | on the device only | `/api/upgrade/*` |
| 39218 | discovery metadata `GET /device.json` | Wi-Fi/LAN | no auth; names, addresses, USB link details |
| 39217/udp | discovery broadcast (`GADGET_DISCOVER_V1`) | LAN | `_gadget._tcp` mDNS/DNS-SD too |
| 9109 | community NPU dashboard + `/metrics` (optional, not part of TiinyOS) | Wi-Fi/LAN | only if installed on the device |

**Interactive docs:** only two services publish them: `/docs` and `/redoc` (system & account) and
`/kb/docs`, `/kb/redoc` (vault). Models/inference, the assistant's connectors and `/api/services` have no
docs or spec (`/v1/docs` 404); model containers vary (Foundation-1 has `/openapi.json`, the llama.cpp chat
container doesn't). The pages need the API key for "Try it out" calls.

**Auth:** `Authorization: Bearer <API key>` on port 80 (the key TiinyOS shows; the device accepts more
than one). The Anthropic-style route also accepts `x-api-key` (**tested**); no key → 401. Discovery (39218) and model containers
need no key. **Until the TiinyOS desktop app connects after the device boots, port 80 answers 502 on
every route** (TiinyOS "Auto Start" avoids this).

**Host names** (TiinyOS maps them to the device): `openai.api.tiiny`, `anthropic.api.tiiny`,
`ollama.api.tiiny`, `api.tiiny`. All of them are the same port 80 — the routes below work on the plain IP
too (**tested**).

## System and power

| method | path | what | mark |
|---|---|---|---|
| POST | `/api/v1/sys/shutdown/` | power off (empty body). Replies `{"status":"ok","message":"System shutdown will be initiated in seconds via host API"}`; off within ~10 s. 0.1.37 replies `…initiated in seconds via D-Bus` (earlier: `via host API`). **Broken on 0.1.36** (same `ok` reply, device stays on); **fixed in 0.1.37** (tested over USB and Wi-Fi, 2026-10-29) | **tested** |
| POST | `/api/v1/sys/reboot/` | restart | **spec** |
| GET / POST | `/api/v1/sys/ac_power/` | power on automatically when plugged in: GET → `{"status","ac_power": bool}`; POST `{"switch": 0\|1}` | **tested** (GET), **app** (POST) |
| GET | `/api/v1/sys/status` | live `cpu`, `memory`, `gpu`, `npus`, `disk` | **tested** |
| GET | `/api/v1/sys/performance` | request timings per endpoint: `summary`, `endpoints` (`limit`, `sort_by`, `include_stats_endpoint`) | **tested** |
| GET | `/api/v1/sys/device_info` | cpu, gpu, dnpu, ram, storage, network, versions, device name, settings | **tested** |
| POST | `/api/v1/sys/setting` | change a device setting | **spec** |
| POST | `/api/v1/sys/base_urls` | runtime base URLs | **spec** |
| GET | `/api/v1/sys/storage`, `/storage/llm`, `/storage/agent` | storage use | **spec** |
| DELETE | `/api/v1/sys/storage/agent/{agent_name}` | delete an agent's data | **spec** |
| GET/POST | `/api/v1/sys/wifi/wifi_list`, `wifi_connect`, `wifi_disconnect`, `connection_status`, `connection_switch`, `wifi_change`, `wifi_auto_connect` | Wi-Fi setup | **docs**/**app** — 404 on port 80 over Wi-Fi (2026-10-25); probably USB/first-setup only |
| GET | `/api/v1/npu/status` | NPU memory budget and utilisation (util only while a model is loaded) | **tested** |
| GET | `:39218/device.json` | discovery: device name, IPv4/IPv6, USB network (`usb.network`, `device_ip`, `host_ip`), metadata URLs | **tested** |
| POST | `:5555/api/upgrade/check`, `download_and_ota_prepare?target_version=`, `upgrade_to?target_version=prepared`, `pause_prepare`, `resume_prepare`, `reboot`; GET `status`, `status/v2` | firmware updates | **docs**/**app** (on-device only) |

## Models

All through port 80 (the model service). `{id}` is the URL-encoded model id, e.g. `Qwen%2FQwen-Image-2.1`.

| method | path | what | mark |
|---|---|---|---|
| GET | `/api/v1/models/?including_downloading=false` | installed models: `id`, `status` (running/stopped…), `type`, `input`, `supported` (e.g. `Image Editing`, `Tool Use`), `npu_usage` (% of NPU), `load_time`, `desc` | **tested** |
| GET | `/api/v1/models/running` | running instances, each container's `port` | **tested** |
| GET | `/api/v1/models/{id}/unload_candidate` | does it fit? `unload_required`, `model_id[]` to unload, `npu_required/available` | **tested** |
| POST | `/api/v1/models/{id}/launch` `{"model_id": id}` | load (async; poll `running`) | **tested** |
| POST | `/api/v1/models/{id}/launch/stream` | load with progress stream | **app** |
| POST | `/api/v1/models/{id}/stop` | unload | **tested** |
| POST | `/api/v1/models/unload_all` | unload everything | **tested** |
| POST | `/api/v1/models/{id}/download`, `/pause_download`, `/interrupt`; `/api/v1/models/interrupt_all` | downloads | **docs**/**app** |
| DELETE | `/api/v1/models/{id}` | delete a downloaded model | **docs** |
| POST | `/api/v1/models/import`, `/import/inspect`; GET `/import/toolkits` | import a custom model (checks toolkit support) | **docs**/**app** |
| GET | `/api/v1/models/types`, `/storage`, `/online_models`, `/api/v1/model-stats` | model types, disk use, store catalogue, stats | probed |
| GET (ws) | `/api/v1/models/running/ws`, `/api/v1/models/npu/status/ws` | live updates | **app** |
| GET | `/api/v1/statistics/week_usage?start_date=…`, `/app_week_usage` | usage stats | **app** (needs `start_date`) |

## Inference: OpenAI-compatible (`/v1`)

The **device handles one request at a time**; parallel requests to different models slow each other down badly.

| method | path | what | mark |
|---|---|---|---|
| GET | `/v1/models` | loaded models; each has `aliases` (`default` = the loaded chat model), `supports_vision`, `supports_chat`, `thinking`, `context_window` | **tested** |
| POST | `/v1/chat/completions` | OpenAI chat. Streaming (`reasoning_content` deltas when thinking), tools/tool calls, images as `image_url` data URIs. Thinking off: `chat_template_kwargs: {"enable_thinking": false}` (gpt-oss rejects it; use `reasoning_effort`). Model `default` = whatever is loaded | **tested** |
| GET | `/v1/capabilities` | capabilities of the running model (503 when none) | probed |
| POST | `/v1/embeddings` | embeddings (load an embedding model, e.g. Qwen3-Embedding-0.6B) | **tested** |
| POST | `/v1/rerank` | `{model, query, documents[]}` (not in the OpenAI spec) | **docs** |
| POST | `/v1/images/generations` | create: `model, prompt, size "WxH", negative_prompt, seed, steps, guidance_scale, response_format`; **edit**: add `image` (one, base64/data URI) or `images` (array, up to 10) with an edit-capable model. `n` > 1 fails: one image per request. `/images/edits` and `/variations` don't exist | **tested** |
| POST | `/v1/image/generate/stream` | image generation with progress | **app** |
| POST | `/v1/audio/speech` | voice clone: `model, input, ref_audio` (base64 WAV), `ref_text` (both required), `language, instruct, response_format wav\|pcm\|mp3`. The Base model only clones | **tested** |
| POST | `/v1/audio/transcriptions` | multipart `model, file, language`; json/text only. Resample 48 kHz stereo to 16 kHz mono first | **tested** |
| POST | `/v1/ocr?model=<id>` | `{"input": data URI, "response_format": "json"}` → `data[0].text` + lines. PP-OCRv6 Small/Medium work (100% on the test image, 0.1.36). **GLM-OCR doesn't work through the API on 0.1.36**: here it answers 404 `Endpoint not found`, and `/v1/chat/completions` answers 400 `does not support chat`. It works on its own port (see Model containers) | **tested** |
| GET/POST | `/v1/music/info`, `/v1/music/sessions`, `/v1/music/generate[/wav\|/preview\|/resume]`, `/v1/music/sessions/{id}/download?format=mp3` | music (Foundation-1 loops via `/generate/wav` with `{model, prompt, config}`; SongGeneration via `/generate/preview` + `/resume`) | **tested** |
| GET/POST | `/v1/3d/capabilities`, `/v1/3d/tasks`, `/v1/3d/tasks/{id}`, `/v1/3d/tasks/{id}/cancel` | Hunyuan3D stages: multipart `stage` (shape, simplify, texture, export), `params` JSON, files `image/mesh/material` | **tested** |
| — | `/v1/video/*` | reserved by the gateway; no video models yet | — |

## Inference: Anthropic- and Ollama-compatible

| method | path | what | mark |
|---|---|---|---|
| POST | `/v1/messages` | Anthropic Messages API (on `anthropic.api.tiiny` or the IP). With a thinking model it **thinks by default** (a `thinking` block before the text, which can use up `max_tokens`); send `"thinking": {"type": "disabled"}` for a plain answer | **tested** |
| GET | `/v1/models` | model list in Anthropic format | probed |
| POST | `/api/chat` | Ollama chat (`"stream": false`, `"think": false` work) | **tested** |
| GET | `/api/tags` | Ollama model list (all installed models) | **tested** |

## Model containers (direct, Wi-Fi/LAN only, no auth)

Port from `GET /api/v1/models/running`; changes on every load. Blocked over USB.

| model | call |
|---|---|
| Qwen3-TTS (Base) | `POST :port/v1/synthesize {"text", "config": {"ref_audio", "ref_text", "language", "instruct"}}` → `audio_data` (24 kHz WAV) |
| Foundation-1 | `POST :port/v1/generate/wav {"prompt", "config": {seconds_total, steps, cfg_scale, seed}}` → WAV; has `/openapi.json` |
| SongGeneration-v2 | `POST :port/v1/generate {"config": {caption, lyrics, generation_type: mixed\|bgm\|vocal\|separate, seconds_total, seed, steps, temperature, top_k, top_p}}` → `audio_data` (48 kHz); only `config` at the top level |
| Hunyuan3D-2.1 | `POST :port/v1/tasks` (multipart, as `/v1/3d/tasks`); `GET :port/v1/tasks/{id}` |
| GLM-OCR | `POST :port/v1/chat/completions` with the image and the text `Text Recognition:` (100% on the test image, 0.1.36; the only working route for GLM-OCR) |

## Knowledge base / vault (`/kb`)

Full list (54 endpoints, from the device's own spec): [endpoints/kb.md](endpoints/kb.md). The vault service calls
itself "SimpleMem Knowledge Base Service" 2.0.0.

**Before you start:** files are only indexed while an **embedding model** is loaded (e.g.
`Qwen/Qwen3-Embedding-0.6B`, ~1% NPU), and a normal search (and the nightly summaries) want a **chat
model** loaded too; without one TiinyOS shows "model not loaded" alerts and searches stall.
`fast_mode: true` skips the chat model. The docs send `Host: kb.tiiny.local`; it isn't needed on the IP.
Same `Authorization: Bearer <API key>` as everything else.

### Files: upload → index → search → rename → download → delete (**tested** 2026-10-25)

| step | call | body | real response (trimmed) |
|---|---|---|---|
| upload | `POST /kb/upload` | multipart `file` (optional `finalize_now`, `source_id`, `timestamp`) | `{"success": true, "source_id": "file-8cb17251b7f4", "filename": "…", "chunks": 1, "vectorized": false, "finalized": false}` (0.1 s) |
| list | `GET /kb/sources?limit=500` | — | `{"count", "total", "limit", "offset", "items": [{"source_id", "filename", "source_type", "chunk_count", "finalized", "vectorize_status", "dream_status", …}]}` |
| index | `POST /kb/finalize` | `{"source_id": "file-…"}` | `{"success": true, "generated_entries": 1}` (0.9 s) |
| search | `POST /kb/retrieve` | `{"question": "…", "fast_mode": false, "include_memory_context": false}` | `{"success", "query", "count", "results": [{"entry_id", "lossless_restatement": "Source file: …\n\n<text>", "keywords", …}]}` (26 s with no chat model loaded) |
| rename | `PATCH /kb/sources/{source_id}` | `{"filename": "new name.txt"}` | `{"success": true, "item": {…}}` |
| download | `GET /kb/files/{source_id}` | — | the original file, byte for byte |
| delete | `POST /kb/delete-memory` | `{"source_id": "file-…"}` | `{"success": true, "deleted_entries": 1, "removed_chunks": 1, "deleted_source": true}`; gone from search too |

`include_memory_context` defaults to **true**: the search then also pulls in your personal memory
(profile, facts). Set it to false to search only files. `GET /kb/retrieve?question=…` works too, and
`POST /kb/query` takes the same body.

```bash
KEY=your-api-key; TIINY=http://192.168.1.50
curl -H "Authorization: Bearer $KEY" -F "file=@notes.txt" $TIINY/kb/upload
curl -H "Authorization: Bearer $KEY" "$TIINY/kb/sources?limit=500"
curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{"source_id":"file-…"}' $TIINY/kb/finalize
curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{"question":"…","include_memory_context":false}' $TIINY/kb/retrieve
```

### Conversations, daily summaries and memory (**spec**; read-only parts checked)

TiinyOS chats are stored in the vault as conversations and summarised ("dreamed") into memory entries
by a background worker, nightly 23:00–05:00 by default (`/kb/memory/schedule`). All of it can be read and managed:

| method | path | what |
|---|---|---|
| POST | `/kb/upload_conversation` | add conversation text: `text`*, `time`* (`/stats` for counts) |
| POST | `/kb/add` | add a single memory: `speaker`*, `content`*, `timestamp`, `source_id`, `auto_finalize` |
| POST | `/kb/finalize_conversation` | summarise pending conversation text now |
| GET | `/kb/sources/conversations`, `/kb/sources/files` | conversation sources / file sources only |
| GET / DELETE | `/kb/conversation_days`, `/kb/conversation_days/{day}` | stored conversations per day |
| GET / PUT | `/kb/memory/schedule` | the nightly window (`nightly_start_hour`* …); GET also shows the summary worker's state (**tested**) |
| GET / PUT | `/kb/memory/model` | which model writes the summaries (`model_id`); GET → `{"model_id": "", "automatic_summary_enabled": true, "running_models": []}` (**tested**) |
| POST | `/kb/memory/process` | run memory processing now |
| GET / POST / PATCH / DELETE | `/kb/memory/facts`, `/kb/memory/facts/{fact_id}` | extracted facts (`fact_type`, `subject`, `predicate`, `object`, …), filterable (`status`, `fact_type`, `subject`, `q`) |
| GET / POST | `/kb/memory/proposals`, `/{id}/approve`, `/{id}/reject` | facts waiting for approval |
| POST | `/kb/context` | build the memory context the assistant uses: `query`*, `include_user_context`, `include_facts`, `include_vector_memories`, `max_tokens` |
| GET / PATCH | `/kb/user-context`, `/kb/user-context/profile/{field}`, `/kb/user-context/versions?limit=1` | your profile (occupation, preferences, more_about_you) |

**How the memory pipeline behaves** (read from the spec and the live data shapes, 2026-10-25; not
stress-tested):
- **Writers:** anything with the API key — files (`/kb/upload`), single memories with a free-form
  `speaker` (`/kb/add`), conversation text (`/kb/upload_conversation`, which TiinyOS chats feed as
  "conversation days"). There's no per-agent permission model in the API.
- **"Dreaming":** every source has `dream_status`, `dream_attempt_count`, `dream_deferred_until`;
  conversation days have `has_summary`, `summary_memory_worthy`, `summary_consumed`,
  `summary_refinement_status` (`queued`/`success`/`skipped`). A `conversation_summary` worker runs in the
  nightly window (default 23:00–05:00, `/kb/memory/schedule`) with the model from `/kb/memory/model`
  (empty `model_id` = automatic summaries off) and extracts **facts** (`subject`/`predicate`/`object`,
  `confidence`, `evidence`, `last_seen_at`, `created_by`, e.g. `curation_auto_approve`). Riskier ones
  become **proposals** (`risk_level`) waiting for approve/reject.
- **Eviction:** none found — no TTL, size cap or retention setting. Facts are replaced by newer facts
  (`supersedes_fact_id`, `status` other than `active`) rather than aged out; removal is explicit
  (`/kb/delete-memory`, `DELETE /kb/conversation_days/{day}`, `DELETE /kb/memory/facts/{id}`). The day delete's response reports
  `deleted_facts` and `deleted_proposals`, so it is meant to remove what was summarised from that day too (not yet tested).
- **Memory scope (added in the 2026-10 update, vault 59 endpoints):** `GET/PUT /kb/memory/scope`, body
  `{"scope": "all" | "tiinyos"}`. The spec describes it as the *summary scope*: `tiinyos` "summarizes TiinyOS
  client chats only", `all` "summarizes every LLM output". The GET also reports `supported_scopes` and
  `origin_tagging` (true here). Tested 2026-10-27 with `all`: on an idle device the day's
  `/kb/conversation_days/{day}` entry didn't change for 9 minutes; one chat sent straight to the gateway's
  `/v1/chat/completions` (not TiinyOS) changed its `content_updated_at` 14 s later. So **any client's chats
  through the gateway (other apps, scripts) are captured** into that day's conversation for the daily summary.
  The captured text isn't readable through the API (`journal_text` stays empty while queued;
  `/kb/files/{source_id}` 404s for the day file) and TiinyOS doesn't show it. Without a summary model nothing
  becomes memory, but the days stay `queued`. Imports are batched (whole minutes). **Switching to `tiinyos`
  did not stop the capture:** a gateway chat sent afterwards updated the day the same way (2026-10-27).
  See [PRIVACY.md](PRIVACY.md) for what you can delete.

## On-device assistant: connectors and MCP

From Tiiny's docs (**docs**), not tested here.

| method | path | what |
|---|---|---|
| GET | `/v1/{gmail\|outlook\|calendar\|outlook/calendar}/status`, `/auth-url` | OAuth email/calendar connectors |
| DELETE | `/v1/{connector}/connection` | disconnect |
| POST | `/v1/telegram/check-with-token`, `/v1/discord/check-with-token`, `/v2/x/check-with-token` | verify bot/API tokens |
| PATCH | `/v1/config/{telegram\|discord\|email\|x\|whatsapp}`, `/v1/config/channels/{…}` | save connector settings |
| POST | `/v1/email/imap/verify` | check IMAP settings |
| POST / GET | `/v1/whatsapp/qr`, `/v1/whatsapp/bridge/status`, `/bridge/logout` | WhatsApp bridge |
| GET / POST / DELETE | `/v1/mcp/servers`, `/v1/mcp/servers/import-json`, `/v1/mcp/servers/{id}`, `/{id}/check` | custom MCP servers |
| GET / POST | `/v1/mcp/tools`, `/v1/mcp/tools/call` | MCP tools (**app**) |
| GET | `/api/v1/chat/history/`, `/sessions`; DELETE `/{session_id}` | TiinyOS chat history (**spec**) |

## Account and pairing

`/api/v1/account/*` (auth, mail codes, passwords, recovery keys, device name, feedback),
`/api/v1/connect` (pair a client), `/api/v1/auth/init`, `/api/v1/auth/login`: see
[endpoints/gateway.md](endpoints/gateway.md) (**spec**) and the TiinyOS docs.

## Apps

`GET /api/v1/apps`, `/api/v1/apps/icons`; `GET /api/v1/webapp/`, `/running`, `POST /start`, `/stop` (**spec**);
`/api/services`, `/api/services/{id}`, `/download/{id}/status`, `/updates/check`, `/resource-usage/ws`
(**docs**/**app**): the app farm.

## Known quirks (checked on 0.1.35 and 0.1.36)

- One request at a time; images are one per request (`n` > 1 fails).
- A model that just reported `running` may answer its first request with `xh2a backend fail` (seen with
  Qwen-Image right after a load): wait ~10 s and retry.
- Since 0.1.36, `/v1/models` reports `thinking` as an object (`supported`, `toggleable`, `enabled_by_default`,
  `levels`, `default_level`) instead of a boolean.
- Port 80 returns 502 until the TiinyOS app has connected since boot.
- Over USB only port 80 is open (still true on 0.1.38): no model ports, so no GLM-OCR and no SongGeneration direct
  route (separate tracks, exact-length songs). The USB link's address can land in
  Docker's `172.17.x.x` (move Docker's `bip` if a container can't reach it).
- Hunyuan3D `background` stage fails (BriefNet missing); SongGeneration style reference fails.
- Plain `/v1/music/generate` fails for SongGeneration ("Session not found"); `/resume` ignores `seconds_total`.
- 0.1.36 to 0.1.38: GLM-OCR isn't reachable through the API at all (`/v1/ocr` 404, chat 400); use its own port over
  Wi-Fi/LAN, or PP-OCRv6 through `/v1/ocr`.
- 0.1.36: power off (`/api/v1/sys/shutdown/`) answers `ok` but the device stays on. Fixed in 0.1.37.
- With the NPU nearly full, `unload_candidate` can say a model fits (e.g. 55% needed, 56% free) while the load never
  starts. Unload other models first (`/api/v1/models/unload_all`), then launch.
- Streaming chat: the last chunk before `[DONE]` can carry `usage` with an empty `choices` list; don't index
  `choices[0]` blindly.

## Test runs: USB vs Wi-Fi (2026-10-30, TiinyOS 0.1.38, device services 0.1.30)

Same device, same [tools/api_test.py](../tools/api_test.py) run twice: once over the USB cable, once over Wi-Fi.
Everything behaves the same on both links except the models' own ports, which the USB link still blocks.

| check | USB cable | Wi-Fi |
|---|---|---|
| chat (Qwen3.6-35B-A3B): plain, streaming, tool calls, vision, Anthropic `/v1/messages`, Ollama `/api/chat` | PASS | PASS |
| embeddings (Qwen3-Embedding-0.6B) | PASS | PASS |
| OCR: PP-OCRv6 Small / Medium via `/v1/ocr` (100% on the test image) | PASS | PASS |
| OCR: GLM-OCR via `/v1/ocr` | FAIL (404) | FAIL (404) |
| OCR: GLM-OCR via `/v1/chat/completions` | FAIL (400 "does not support chat") | FAIL (400) |
| **OCR: GLM-OCR on its own port** | **not reachable** | PASS (100%) |
| image (Z-Image-Turbo, 512x512) | PASS | PASS |
| voice clone (Qwen3-TTS Base) | PASS | PASS |
| transcription (Qwen3-ASR, 98% match) | PASS | PASS |
| music loop (Foundation-1) | PASS | PASS |
| 3D shape (Hunyuan3D-2.1, ~7 min) | PASS | PASS |
| power off (`/api/v1/sys/shutdown/`) | not re-tested on 0.1.38 | not re-tested on 0.1.38 |

0.1.37 (2026-10-29) gave the same results, with power off working on both links (off in ~9 s). 0.1.36
(2026-10-28) was the same except power off, which answered `ok` but left the device on.
Compare your own runs: `python tools/api_test.py --via usb`, then `--via wifi`, then
`python tools/api_compare.py snapshots/api-test-*/report.json`.
