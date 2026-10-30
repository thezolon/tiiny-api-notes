# Recipes

Replace `192.168.1.50` with your Tiiny's address (Wi-Fi/LAN; over the USB cable it's the other end of the cable's
small network) and `YOUR_KEY` with the key from **TiinyOS → Settings → API Key**. Everything goes to port 80.

```bash
TIINY=http://192.168.1.50; KEY=YOUR_KEY
```

## Is it up? What's loaded?

```bash
curl -H "Authorization: Bearer $KEY" $TIINY/v1/models                      # loaded models ("default" = the chat model)
curl -H "Authorization: Bearer $KEY" "$TIINY/api/v1/models/?including_downloading=false"   # installed models
curl -H "Authorization: Bearer $KEY" $TIINY/api/v1/npu/status               # NPU use
```

Every route answers 502 until the TiinyOS desktop app has connected once since the device booted.

## Load and unload a model

```bash
ID=Qwen%2FQwen3-Embedding-0.6B                                              # URL-encoded model id
curl -H "Authorization: Bearer $KEY" $TIINY/api/v1/models/$ID/unload_candidate    # does it fit?
curl -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
     -d '{"model_id":"Qwen/Qwen3-Embedding-0.6B"}' $TIINY/api/v1/models/$ID/launch
curl -X POST -H "Authorization: Bearer $KEY" $TIINY/api/v1/models/$ID/stop
curl -X POST -H "Authorization: Bearer $KEY" $TIINY/api/v1/models/unload_all
```

## Power off (no TiinyOS needed)

```bash
curl -X POST -H "Authorization: Bearer $KEY" $TIINY/api/v1/sys/shutdown/
```

Keep the trailing slash. It answers `{"status":"ok", …}` and switches off a few seconds later; press the power
button to turn it back on. `POST /api/v1/sys/reboot/` restarts.

> **TiinyOS 0.1.36:** power off didn't work there, from this call or from the TiinyOS app (the reply was still
> `{"status":"ok", …}` but the Tiiny stayed on). **Fixed in 0.1.37**: tested over USB and Wi-Fi, off in ~10 s; still works on 0.1.38.
> On 0.1.36, update or use the power button.

Windows PowerShell:

```powershell
Invoke-RestMethod -Method Post -Headers @{Authorization="Bearer YOUR_KEY"} "http://192.168.1.50/api/v1/sys/shutdown/"
```

## OCR (read text from an image)

**PP-OCRv6** (Small or Medium) works through the normal API on any connection, USB included:

```bash
curl -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  "$TIINY/v1/ocr?model=PaddlePaddle%2FPP-OCRv6-Small" \
  -d '{"input": "data:image/png;base64,BASE64_OF_YOUR_IMAGE", "response_format": "json"}'
```

The text is in `data[0].text`.

**GLM-OCR** doesn't work through the API on TiinyOS 0.1.36 (`/v1/ocr` answers 404, chat answers 400), but the
model works on its own port. Over Wi-Fi/LAN only (the USB link blocks model ports), no key needed:

1. Load GLM-OCR, then find its port (it changes on every load):
   ```bash
   curl -H "Authorization: Bearer $KEY" $TIINY/api/v1/models/running   # "model_id": "zai-org/GLM-OCR" -> "port"
   ```
2. Send the image with the prompt `Text Recognition:`:
   ```bash
   curl http://192.168.1.50:PORT/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "zai-org/GLM-OCR",
     "max_tokens": 1000, "messages": [{"role": "user", "content": [
       {"type": "image_url", "image_url": {"url": "data:image/png;base64,BASE64_OF_YOUR_IMAGE"}},
       {"type": "text", "text": "Text Recognition:"}]}]}'
   ```
   The text is in `choices[0].message.content`. While GLM-OCR is loaded, anyone on your network can use that port.

## Chat (OpenAI style)

```bash
curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" $TIINY/v1/chat/completions -d '{
  "model": "default", "messages": [{"role": "user", "content": "Hello!"}],
  "chat_template_kwargs": {"enable_thinking": false}}'
```

`enable_thinking: false` turns reasoning off (gpt-oss models want `"reasoning_effort": "low"` instead). The
device serves one request at a time.

## Use it from other apps

Any OpenAI-compatible client works with base URL `http://<tiiny>/v1`, your key, and model **`default`** (whatever
chat model is loaded, so switching models in TiinyOS needs no client change).

- **Hermes:** a custom provider with that base URL, key and model `default`; mark it as supporting images if the
  loaded model has vision. Leave the context length unset so it follows the model.
- **Cline:** "OpenAI Compatible" provider, same base URL/key/model.
- **Python OpenAI SDK:** `OpenAI(base_url="http://192.168.1.50/v1", api_key="YOUR_KEY")`.
- Anthropic-style clients: `POST /v1/messages` (accepts `x-api-key`). Ollama-style: `/api/tags`, `/api/chat`.

Prefer the USB address if the device moves between networks: it stays the same.

## Vault (knowledge base): add, find and remove a file

Indexing needs an **embedding model** loaded (e.g. Qwen3-Embedding-0.6B); a full search also wants a chat model
(`"fast_mode": true` skips it).

```bash
curl -H "Authorization: Bearer $KEY" -F "file=@notes.txt" $TIINY/kb/upload                     # → source_id
curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{"source_id":"file-…"}' $TIINY/kb/finalize
curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
     -d '{"question":"what did I write about…","include_memory_context":false}' $TIINY/kb/retrieve
curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{"source_id":"file-…"}' $TIINY/kb/delete-memory
```

`include_memory_context` defaults to true and pulls your personal memory into the results.

## Delete captured chats from the vault

See [PRIVACY.md](PRIVACY.md) first: this deletes whole days.

```bash
curl -H "Authorization: Bearer $KEY" "$TIINY/kb/conversation_days?limit=500"         # list days and their status
curl -X DELETE -H "Authorization: Bearer $KEY" "$TIINY/kb/conversation_days/2026-10-26"
```

```powershell
Invoke-RestMethod -Method Delete -Headers @{Authorization="Bearer YOUR_KEY"} "http://192.168.1.50/kb/conversation_days/2026-10-26"
```
