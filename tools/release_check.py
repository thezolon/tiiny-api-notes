"""Check the API changes claimed for the 2026-11-18 Model Store release on your own Tiiny.

    python tools/release_check.py                 # every check whose model you have downloaded
    python tools/release_check.py --only tts,ocr  # some of them: scheduler, tts, ocr, music, vision, chat

Checks (each runs only if its model is downloaded; models it loads are unloaded afterwards):
  scheduler  ERNIE-Image-Turbo / HiDream-O1-Image-Dev: `"scheduler": {"type": ...}` in /v1/images/generations is used
             (another scheduler gives another image; an unknown one is refused)
  tts        every text-to-speech model: one plain sentence ending in "." vs the same with a trailing space
  ocr        PP-OCRv6 / Unlimited-OCR: an http:// image URL as `input` instead of a data URI
  music      ACE-Step / SongGeneration: `reference_audio_url` is fetched (a missing file is refused, a real one works)
  vision     Qwen3.6-35B-A3B-Turbo: image tokens at 1 MP vs 4 MP (bigger images are shrunk to ~1 MP)
  chat       Qwen3.5-9B-Turbo / Ornith-1.5 / Qwen3.6 Turbo: context window, thinking switch, default sampling settings
             (the sampling defaults come from the model's own port: Wi-Fi/LAN only)

The URL checks serve test files from this computer, so the Tiiny must be able to reach it (same network; allow
Python through the firewall if asked). Needs TIINY_URL / TIINY_KEY. Stops if a model has an update waiting
(--allow-outdated to run anyway). Report: snapshots/release-check-<time>/report.json (git-ignored).
"""
import argparse
import base64
import functools
import hashlib
import http.server
import io
import json
import socket
import struct
import threading
import time
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

import api_test as at

HERE = Path(__file__).parent
SENTENCE = "Hello there friend how are you."
# TTS models that need more than text (see docs/VOICES.md), so a plain request fails by design
TTS_NEEDS = {"Qwen/Qwen3-TTS-12Hz-1.7B-Base": "voice cloning only (ref_audio + ref_text)",
             "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign": "a voice description (instruct)"}


def stop(t, mid):
    t.ok("POST", f"/api/v1/models/{urllib.parse.quote(mid, safe='')}/stop", {}, timeout=180)


def serve_assets(tiiny_url):
    """Serve tools/assets over http on this computer's address as the Tiiny sees it. Returns the base URL."""
    host = urllib.parse.urlparse(tiiny_url).hostname
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect((host, 80))
        me = s.getsockname()[0]
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(at.ASSETS))
    srv = http.server.ThreadingHTTPServer((me, 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://{me}:{srv.server_port}"


def png(side):
    """A side x side PNG of diagonal stripes, made without an image library."""
    rows = bytearray()
    for y in range(side):
        rows.append(0)
        for x in range(side):
            v = ((x + y) // 16) % 2
            rows += bytes((230, 90, 160) if v else (60, 120, 230))
    chunk = lambda k, d: struct.pack(">I", len(d)) + k + d + struct.pack(">I", zlib.crc32(k + d))
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", side, side, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(bytes(rows), 6)) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(data).decode()


def check_scheduler(t, have, out, ctx):
    alt = {"baidu/ERNIE-Image-Turbo": "unipc_flow", "HiDream-ai/HiDream-O1-Image-Dev": "euler"}
    for mid in [m for m in alt if m in have]:
        t.load(mid)
        base = {"model": mid, "prompt": "a red apple on a wooden table", "size": "512x512", "seed": 42,
                "response_format": "b64_json"}
        try:
            shots = {}
            for name, extra in [("default", {}), (alt[mid], {"scheduler": {"type": alt[mid]}}),
                                ("unknown", {"scheduler": {"type": "no_such_scheduler"}})]:
                code, res = t.call("POST", "/v1/images/generations", {**base, **extra}, timeout=600)
                shots[name] = (hashlib.sha1(res["data"][0]["b64_json"].encode()).hexdigest()[:10] if code < 300
                               else f"HTTP {code}: {json.dumps(res)[:120]}")
            ok = shots["default"] != shots[alt[mid]] and shots["unknown"].startswith("HTTP 400")
            out[f"scheduler {mid}"] = {"pass": ok, **shots}
            print(f"  {'PASS' if ok else 'FAIL'} scheduler {mid}: {shots}", flush=True)
        finally:
            stop(t, mid)


def check_tts(t, have, out, ctx):
    for mid in sorted(m for m, info in have.items() if info.get("type") == "Text-to-Speech"):
        if mid in TTS_NEEDS:
            print(f"  tts {mid}: skipped, needs {TTS_NEEDS[mid]}", flush=True)
            continue
        t.load(mid)
        try:
            codes = {}
            for name, txt in [("one sentence", SENTENCE), ("+ trailing space", SENTENCE + " ")]:
                try:
                    codes[name] = t.call("POST", "/v1/audio/speech", {"model": mid, "input": txt}, raw=True, timeout=180)[0]
                except OSError:
                    codes[name] = "no answer"
            out[f"tts {mid}"] = codes
            note = "  <- single sentence fails; add a trailing space" if codes["one sentence"] != 200 and codes["+ trailing space"] == 200 else ""
            print(f"  tts {mid}: {codes}{note}", flush=True)
        finally:
            stop(t, mid)


def check_ocr(t, have, out, ctx):
    for mid in [m for m in ("PaddlePaddle/PP-OCRv6-Medium", "PaddlePaddle/PP-OCRv6-Small", "baidu/Unlimited-Ocr") if m in have]:
        t.load(mid)
        q = urllib.parse.quote(mid, safe="")
        try:
            r = {}
            for name, inp in [("data URI", at.data_uri(at.ASSETS / "ocr-test.png", "image/png")),
                              ("http URL", ctx["assets"] + "/ocr-test.png")]:
                code, res = t.call("POST", f"/v1/ocr?model={q}", {"input": inp, "response_format": "json"}, timeout=300)
                r[name] = (f"{at.similarity((res.get('data') or [{}])[0].get('text', ''), at.OCR_TEXT):.0%}" if code < 300
                           else f"HTTP {code}")
            ok = r["http URL"] == r["data URI"] and r["http URL"].endswith("%")
            out[f"ocr {mid}"] = {"pass": ok, **r}
            print(f"  {'PASS' if ok else 'FAIL'} ocr URL input {mid}: {r}", flush=True)
        finally:
            stop(t, mid)


def check_music(t, have, out, ctx):
    for mid in [m for m in ("ACE-Step/AceStep-XL-Turbo", "tencent/SongGeneration-v2-large") if m in have]:
        t.load(mid)
        base = {"model": mid, "prompt": "API TEST: calm acoustic guitar",
                "config": {"seconds_total": 10, "seed": 1, "lyrics": "[verse]\nAPI test, la la la"}}
        if "SongGeneration" in mid:
            base["config"]["preview_seconds"] = 10  # its preview call refuses to run without it
        try:
            r = {}
            for name, url in [("missing file", ctx["assets"] + "/does-not-exist.wav"), ("real file", ctx["assets"] + "/ref-voice.wav")]:
                body = json.loads(json.dumps(base))
                body["config"]["reference_audio_url"] = url
                path = "/v1/music/generate/wav" if "ACE-Step" in mid else "/v1/music/generate/preview"
                code, res = t.call("POST", path, body, raw=True, timeout=900)
                r[name] = f"{code} " + (f"{len(res)} bytes" if code < 300 else (res.decode('utf-8', 'replace') if isinstance(res, bytes) else json.dumps(res))[:120])
            ok = r["missing file"].startswith("400") and "404" in r["missing file"] and r["real file"].startswith("200")
            out[f"music {mid}"] = {"pass": ok, **r}
            print(f"  {'PASS' if ok else 'FAIL'} music reference_audio_url {mid}: {r}", flush=True)
        finally:
            stop(t, mid)


def check_vision(t, have, out, ctx):
    mid = "Qwen/Qwen3.6-35B-A3B-Turbo"
    if mid not in have:
        return
    t.load(mid)
    try:
        tokens = {}
        for side in (1024, 2048):
            body = {"model": mid, "max_tokens": 10, "chat_template_kwargs": {"enable_thinking": False},
                    "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": png(side)}},
                                                              {"type": "text", "text": "Describe this in three words."}]}]}
            code, res = t.call("POST", "/v1/chat/completions", body, timeout=300)
            tokens[f"{side}x{side}"] = res["usage"]["prompt_tokens"] if code < 300 else f"HTTP {code}"
        ok = tokens["1024x1024"] == tokens["2048x2048"]
        out["vision 1MP cap"] = {"pass": ok, "prompt_tokens": tokens}
        print(f"  {'PASS' if ok else 'FAIL'} vision: prompt tokens {tokens} (same = shrunk to ~1 MP)", flush=True)
    finally:
        stop(t, mid)


def check_chat(t, have, out, ctx):
    for mid in [m for m in ("Qwen/Qwen3.5-9B-Turbo", "ornith-ai/Ornith-1.5-35B-A3B-Turbo", "Qwen/Qwen3.6-35B-A3B-Turbo") if m in have]:
        t.load(mid)
        try:
            m = next(x for x in t.ok("GET", "/v1/models")["data"] if x["id"] == mid)
            r = {"context_window": m.get("context_window"), "thinking": m.get("thinking")}
            try:
                props = json.loads(urllib.request.urlopen(t.direct(mid) + "/props", timeout=10).read())
                g = props.get("default_generation_settings", {})
                p = g.get("params", g)
                r.update(n_ctx=g.get("n_ctx"), **{k: p.get(k) for k in ("presence_penalty", "repeat_penalty", "temperature", "top_p", "top_k")})
            except at.Skip as e:
                r["defaults"] = f"not read ({e})"
            out[f"chat {mid}"] = r
            print(f"  chat {mid}: {r}", flush=True)
        finally:
            stop(t, mid)


CHECKS = {"scheduler": check_scheduler, "tts": check_tts, "ocr": check_ocr, "music": check_music,
          "vision": check_vision, "chat": check_chat}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", help="comma-separated: " + ", ".join(CHECKS))
    ap.add_argument("--allow-outdated", action="store_true")
    a = ap.parse_args()
    only = a.only.split(",") if a.only else list(CHECKS)
    url, key = at.device()
    t = at.Tiiny(url, key)
    if t.call("GET", "/api/v1/models/running", timeout=15)[0] == 502:
        raise SystemExit("The Tiiny looks locked after a restart: run `tiiny login` or open the TiinyOS app, then rerun.")
    rows = t.ok("GET", "/api/v1/models/?including_downloading=false")
    have = {m["id"]: m for m in (rows.get("data", rows) if isinstance(rows, dict) else rows) if m.get("status") == "downloaded"}
    at.require_current(t, list(have), a.allow_outdated)
    ctx = {"assets": serve_assets(url)}
    out = {"when": time.strftime("%Y-%m-%d %H:%M"), "tiiny_os": t.ok("GET", "/api/v1/sys/device_info").get("tiiny_os")}
    before = set(t.running())
    try:
        for name in only:
            print(f"\n{name}", flush=True)
            CHECKS[name](t, have, out, ctx)
    finally:
        for mid in set(t.running()) - before:
            stop(t, mid)
        d = HERE.parent / "snapshots" / f"release-check-{time.strftime('%Y%m%d-%H%M%S')}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "report.json").write_text(json.dumps(out, indent=1), "utf-8")
        print(f"\nReport: {d / 'report.json'}")


if __name__ == "__main__":
    main()
