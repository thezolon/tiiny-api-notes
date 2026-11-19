"""Check whether a chat model really thinks, whatever its `thinking` field says, and whether turning thinking off works.

    python tools/thinking_check.py                                  # the two Qwen-Image prompt enhancers
    python tools/thinking_check.py --model Qwen/Qwen3.5-9B-Turbo --max-tokens 512

For each model: shows what GET /v1/models reports in `thinking`, then sends the same request twice through
POST /v1/chat/completions, once as-is and once with "chat_template_kwargs": {"enable_thinking": false}, and prints
how much came back as thinking (`reasoning_content`) and as the answer (`content`), the finish reason and the time.
Image-input models also get a small generated test picture. Needs TIINY_URL / TIINY_KEY. Stops if a model has an
update waiting (--allow-outdated to run anyway). Models the run loaded are unloaded afterwards.
"""
import argparse
import base64
import json
import struct
import time
import urllib.parse
import zlib

import api_test as at

DEFAULT = ["Qwen/Qwen-Image-2.1-PE-T2I", "Qwen/Qwen-Image-2.1-PE-I2I"]
TEXT = "a cat sleeping on a sofa"
EDIT = "make the background blue"


def test_png(w=64, h=64):
    """A small two-colour PNG (left half orange, right half grey), made without any image library."""
    rows = b"".join(b"\x00" + b"".join(bytes((240, 140, 40) if x < w // 2 else (128, 128, 128)) for x in range(w))
                    for _ in range(h))
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode()


def ask(t, model, vision, max_tokens, thinking_off):
    content = [{"type": "image_url", "image_url": {"url": test_png()}}, {"type": "text", "text": EDIT}] if vision else TEXT
    body = {"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": max_tokens,
            "temperature": 0, "stream": False}
    if thinking_off:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    t0 = time.time()
    code, res = t.call("POST", "/v1/chat/completions", body, timeout=600)
    dt = time.time() - t0
    if code >= 300:
        return {"error": f"HTTP {code}: {json.dumps(res)[:200]}", "seconds": dt}
    ch = (res.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    return {"answer_chars": len((msg.get("content") or "").strip()),
            "thinking_chars": len((msg.get("reasoning_content") or "").strip()),
            "finish": ch.get("finish_reason"), "tokens": (res.get("usage") or {}).get("completion_tokens"),
            "seconds": dt, "answer": (msg.get("content") or "").strip()[:200]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", action="append", help="model id (repeatable); default: the Qwen-Image prompt enhancers")
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--allow-outdated", action="store_true")
    a = ap.parse_args()
    models = a.model or DEFAULT
    t = at.Tiiny(*at.device())
    if t.call("GET", "/api/v1/models/running", timeout=15)[0] == 502:
        raise SystemExit("The Tiiny looks locked after a restart: run `tiiny login` or open the TiinyOS app, then rerun.")
    have = t.ok("GET", "/api/v1/models/?including_downloading=false")
    have = {m["id"]: m for m in (have.get("data", have) if isinstance(have, dict) else have)}
    versions = at.require_current(t, models, a.allow_outdated)
    before = set(t.running())
    try:
        for model in models:
            for other in set(t.running()) - {model}:
                t.ok("POST", f"/api/v1/models/{urllib.parse.quote(other, safe='')}/stop", {}, timeout=180)
            t.load(model)
            listed = next((m for m in t.ok("GET", "/v1/models").get("data", []) if m.get("id") == model), {})
            vision = "Image" in (have.get(model, {}).get("input") or "")
            print(f"\n{model} (build {versions.get(model, {}).get('version')}): /v1/models thinking = "
                  f"{json.dumps(listed.get('thinking'))}")
            for off in (False, True):
                r = ask(t, model, vision, a.max_tokens, off)
                label = "thinking off" if off else "as-is       "
                if "error" in r:
                    print(f"  {label}: {r['error']}")
                    continue
                print(f"  {label}: thinking {r['thinking_chars']:5} chars, answer {r['answer_chars']:5} chars, "
                      f"finish {r['finish']}, {r['tokens']} tokens, {r['seconds']:.1f} s")
                if r["answer"]:
                    print(f"      answer starts: {r['answer'][:120]!r}")
    finally:
        for model in set(t.running()) - before:
            t.ok("POST", f"/api/v1/models/{urllib.parse.quote(model, safe='')}/stop", {}, timeout=180)


if __name__ == "__main__":
    main()
