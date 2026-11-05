# Use the Tiiny as a provider in Hermes Agent

Hermes Agent (Nous Research) works with any OpenAI-compatible endpoint, and the Tiiny has one. This walks through
adding it. Tested with Hermes Desktop on Windows and TiinyOS 0.1.38: chat, tool calling and images work.

## What you need

1. **The Tiiny's address.**
   - Over Wi-Fi/LAN: the device's IP address on your network, e.g. `192.168.1.50` (TiinyOS shows it, or your router
     does).
   - Over the USB cable: the USB address TiinyOS shows, e.g. `172.20.31.109`. It's fixed per device, so it doesn't
     change when you move between networks.
2. **Your API key:** TiinyOS → **Settings → API Key**.
3. **A chat model loaded** on the Tiiny (TiinyOS, `tiiny load <model>`, or the API). Hermes uses whatever is loaded
   through the model name `default`.

## Step 1: check the Tiiny answers

```bash
curl -H "Authorization: Bearer YOUR_KEY" http://192.168.1.50/v1/models
```

You should see a list with your loaded model and the alias `default`. If every call answers **502**, the Tiiny was
restarted and is still locked: open the TiinyOS app once or run `tiiny login`, then try again.

To check chat, tools and images in one go: `TIINY_URL=http://192.168.1.50 TIINY_KEY=YOUR_KEY python tools/api_test.py chat`.

## Step 2: add the provider

### Option A: the setup wizard (easiest)

Close any Hermes chat first, then in a terminal:

```bash
hermes model
```

Choose **Custom endpoint (self-hosted / VLLM / etc.)** and enter:

| prompt | value |
|---|---|
| API base URL | `http://192.168.1.50/v1` (your address + `/v1`) |
| API key | your TiinyOS API key |
| Model name | `default` |

### Option B: edit `config.yaml`

The file is `%LOCALAPPDATA%\hermes\config.yaml` on Windows, `~/.hermes/config.yaml` on macOS/Linux. Back it up
first. Add a named provider under `custom_providers:` (keep any entries you already have):

```yaml
custom_providers:
  - name: Tiiny
    base_url: http://192.168.1.50/v1
    api_key: YOUR_KEY
    model: default
    models:
      default:
        supports_vision: true
```

To make it the main model, point the top-level `model:` section at it:

```yaml
model:
  default: default
  provider: custom:Tiiny
  base_url: http://192.168.1.50/v1
  api_key: YOUR_KEY
```

Restart Hermes after editing.

## Step 3: use it

- New session on the Tiiny: `hermes --provider custom:Tiiny`
- Switch inside a chat: `/model custom:Tiiny:default`
- Switch which model the Tiiny runs: load another model on the Tiiny (TiinyOS or `tiiny load`). Hermes keeps using
  `default`, so nothing changes on the Hermes side.

## Things worth knowing

- **Use the model name `default`,** not the real model id. It always means "whatever is loaded", so you can swap
  models on the Tiiny without touching Hermes.
- **Context size is detected automatically** from the Tiiny's `/v1/models` (`context_window`). Don't pin it: a pinned
  value goes stale when you load a model with a different context.
- **Images: keep `supports_vision: true`.** Hermes can't detect vision support on a generic OpenAI-style server, so
  it has to be set. With a text-only model loaded (gpt-oss-20b/120b, for example), turns with an image will fail:
  load a vision model (see "Chat with vision" in [MODELS.md](MODELS.md)) or remove the line.
- **The first reply is slow** (about 50-65 s in our test): Hermes sends a very large system prompt with its tools,
  and the Tiiny reads it before answering. Later turns are faster. A mixture-of-experts model such as
  Qwen3.6-35B-A3B helps (it reads prompts faster than a dense model of similar size; see
  [API.md](API.md#chat-speed-measured-2026-11-01-tiinyos-0138)).
- **Thinking models:** Hermes controls reasoning with `/reasoning` and `agent.reasoning_effort`. If replies come back
  empty with a small token limit, the thinking used up the budget (see the `max_tokens` quirk in [API.md](API.md)).
- **One request at a time:** the Tiiny answers one chat at a time, so Hermes features that run several model calls
  in parallel (subagents, background tasks) will queue up.
- **After a power cycle** everything answers 502 until the Tiiny is unlocked (TiinyOS app or `tiiny login`);
  [RECIPES.md](RECIPES.md#unlock-automatically-after-a-restart) has a script that does it automatically.
