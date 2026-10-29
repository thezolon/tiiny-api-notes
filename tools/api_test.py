"""Walk through the Tiiny's API and check each feature really works: chat (plain, streaming, tools, vision,
Anthropic and Ollama style), embeddings, OCR, image generation, voice clone (TTS), transcription (ASR), music
loops and 3D. Loads each model it needs in turn, checks the answers against known inputs, prints a pass/fail
table, and loads back what was running before.

Usage:
    TIINY_URL=http://192.168.1.50 TIINY_KEY=... python tools/api_test.py     # full run, every section
    python tools/api_test.py ocr                      # one section: info chat embeddings ocr image audio music 3d
    python tools/api_test.py ocr audio-asr            # several sections and/or single checks
    python tools/api_test.py --skip 3d,music          # full run minus some sections
    python tools/api_test.py --list                   # show sections, checks and the models they use

Inputs come from tools/assets/ (ocr-test.png, mug.png, ref-voice.wav + ref-voice.txt); outputs and a JSON report
go to snapshots/ (git-ignored). Standard library only. Needs the TiinyOS app connected (the API answers 502
until it is). One request at a time: don't use the Tiiny for anything else while this runs.
"""
import argparse
import base64
import difflib
import io
import json
import math
import os
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import wave
from pathlib import Path

HERE = Path(__file__).parent
ASSETS = HERE / "assets"
OCR_TEXT = """Tiiny Studio OCR Test
The quick brown fox jumps over the lazy dog.
Invoice #4821 - Total: $1,234.56 - Due 2026-11-15
Phone: (555) 010-7788 Email: hello@example.com
def add(a, b): return a + b # Python code line
Line six: 3 apples, 12 oranges, 0.5 kg grapes"""

MODELS = {
    "chat": "Qwen/Qwen3.6-35B-A3B",
    "embed": "Qwen/Qwen3-Embedding-0.6B",
    "ocr": ["PaddlePaddle/PP-OCRv6-Small", "PaddlePaddle/PP-OCRv6-Medium", "zai-org/GLM-OCR"],
    "image": "Tongyi-MAI/Z-Image-Turbo",
    "tts": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "asr": "Qwen/Qwen3-ASR-1.7B",
    "music": "RoyalCities/Foundation-1",
    "3d": "Tencent/Hunyuan3d-2.1",
}


class Fail(Exception):
    pass


class Skip(Exception):
    pass


class Tiiny:
    def __init__(self, url, key):
        self.url, self.key = url.rstrip("/"), key

    def call(self, method, path, body=None, timeout=300, raw=False, ctype="application/json"):
        data = body if isinstance(body, bytes) or body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.url + path, data, method=method)
        req.add_header("Authorization", f"Bearer {self.key}")
        if data is not None:
            req.add_header("Content-Type", ctype)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = r.read()
                return r.status, (out if raw else json.loads(out or b"{}"))
        except urllib.error.HTTPError as e:
            text = e.read()[:600].decode("utf-8", "replace")
            try:
                return e.code, json.loads(text)
            except ValueError:
                return e.code, {"error": text}

    def ok(self, method, path, body=None, **kw):
        code, res = self.call(method, path, body, **kw)
        if code >= 300:
            raise Fail(f"HTTP {code} from {path}: {json.dumps(res)[:300] if not isinstance(res, bytes) else res[:300]}")
        return res

    def direct(self, mid):
        """Base URL of a model's own container port (Wi-Fi/LAN only; the USB link blocks it), or Skip."""
        port = self.running().get(mid, {}).get("port")
        host = urllib.parse.urlparse(self.url).hostname
        if not port:
            raise Skip(f"{mid} has no port")
        try:
            urllib.request.urlopen(f"http://{host}:{port}/", timeout=5)
        except urllib.error.HTTPError:
            pass  # reachable; any HTTP answer will do
        except OSError:
            raise Skip(f"port {port} not reachable (USB link?); run over Wi-Fi/LAN")
        return f"http://{host}:{port}"

    def running(self):
        res = self.ok("GET", "/api/v1/models/running")
        return {r["model_id"]: r for r in res["instances"]["running"]}

    def load(self, mid, wait=600):
        """Load `mid`, unloading whatever the device says must make room. Returns seconds taken (0 if already up)."""
        if self.running().get(mid, {}).get("status") in ("running", "ready"):
            return 0
        t0 = time.time()
        q = urllib.parse.quote(mid, safe="")
        plan = self.ok("GET", f"/api/v1/models/{q}/unload_candidate")
        for other in plan.get("model_id") or []:
            self.ok("POST", f"/api/v1/models/{urllib.parse.quote(other, safe='')}/stop", {}, timeout=180)
        self.ok("POST", f"/api/v1/models/{q}/launch", {"model_id": mid})
        retried = False
        while time.time() - t0 < wait:
            time.sleep(5)
            st = self.running().get(mid, {}).get("status")
            if st in ("running", "ready"):
                return time.time() - t0
            if st in ("failed", "error"):
                raise Fail(f"{mid} failed to load")
            # 0.1.36: with the NPU nearly full, unload_candidate can say it fits (e.g. 55% needed, 56% free) while the
            # load never starts. Once, after 2 minutes: unload everything else and launch again.
            if not st and not retried and time.time() - t0 > 120:
                retried = True
                for other in self.running():
                    self.ok("POST", f"/api/v1/models/{urllib.parse.quote(other, safe='')}/stop", {}, timeout=180)
                self.ok("POST", f"/api/v1/models/{q}/launch", {"model_id": mid})
        raise Fail(f"{mid} not loaded after {wait} s")


def multipart(fields, files):
    b = uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, (name, data, ctype) in files.items():
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
        body += data + b"\r\n"
    return body + f"--{b}--\r\n".encode(), f"multipart/form-data; boundary={b}"


def data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def similarity(a, b):
    norm = lambda s: " ".join(s.split()).lower()
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise Fail("not a PNG")
    return struct.unpack(">II", data[16:24])


def wav_seconds(data):
    if data[:4] != b"RIFF":
        raise Fail(f"not a WAV (starts {data[:12]!r})")
    with wave.open(io.BytesIO(data)) as w:
        return w.getnframes() / w.getframerate()


def to_16k_mono(data):
    """16-bit PCM WAV -> 16 kHz mono WAV (what the ASR model wants), linear interpolation."""
    with wave.open(io.BytesIO(data)) as w:
        rate, ch, frames = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    pcm = struct.unpack(f"<{len(frames) // 2}h", frames)
    mono = [sum(pcm[i:i + ch]) / ch for i in range(0, len(pcm), ch)]
    n = int(len(mono) * 16000 / rate)
    out = []
    for i in range(n):
        x = i * rate / 16000
        j = int(x)
        a, b = mono[min(j, len(mono) - 1)], mono[min(j + 1, len(mono) - 1)]
        out.append(int(a + (b - a) * (x - j)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000)
        w.writeframes(struct.pack(f"<{len(out)}h", *out))
    return buf.getvalue()


def chat(t, messages, **extra):
    body = {"model": "default", "messages": messages, "max_tokens": 200,
            "chat_template_kwargs": {"enable_thinking": False}, **extra}
    return t.ok("POST", "/v1/chat/completions", body)["choices"][0]


# ---- checks: each returns a short detail string, raises Fail on a wrong answer ----

def check_info(t, out):
    i = t.ok("GET", "/api/v1/sys/device_info")
    t.ok("GET", "/v1/models")
    t.ok("GET", "/api/v1/sys/status")
    t.ok("GET", "/api/v1/npu/status")
    t.ok("GET", "/kb/conversation_days?limit=1")
    return f"TiinyOS {i.get('tiiny_os')}, services {i.get('version')}"


def check_chat(t, out):
    t.load(MODELS["chat"])
    text = chat(t, [{"role": "user", "content": "Reply with exactly one word: pineapple"}])["message"].get("content") or ""
    if "pineapple" not in text.lower():
        raise Fail(f"unexpected reply {text[:80]!r}")
    return f"{MODELS['chat']}: {text.strip()[:40]!r}"


def check_stream(t, out):
    t.load(MODELS["chat"])
    body = {"model": "default", "stream": True, "max_tokens": 60, "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": "Count from 1 to 5, separated by spaces."}]}
    raw = t.ok("POST", "/v1/chat/completions", body, raw=True).decode("utf-8", "replace")
    parts = []
    for line in raw.splitlines():
        if line.startswith("data: ") and line[6:].strip() != "[DONE]":
            choices = json.loads(line[6:]).get("choices") or []  # the last chunk can carry only usage
            parts.append((choices[0].get("delta") or {}).get("content") or "" if choices else "")
    text = "".join(parts)
    if not all(str(n) in text for n in range(1, 6)):
        raise Fail(f"stream text {text[:80]!r}")
    return f"{len(parts)} chunks: {text.strip()[:30]!r}"


def check_tools(t, out):
    t.load(MODELS["chat"])
    tool = {"type": "function", "function": {"name": "get_weather", "description": "Current weather for a city",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}
    msg = chat(t, [{"role": "user", "content": "What's the weather in Paris right now?"}], tools=[tool])["message"]
    calls = msg.get("tool_calls") or []
    if not calls or calls[0]["function"]["name"] != "get_weather":
        raise Fail(f"no tool call: {json.dumps(msg)[:200]}")
    args = json.loads(calls[0]["function"]["arguments"] or "{}")
    if "paris" not in str(args.get("city", "")).lower():
        raise Fail(f"tool args {args}")
    return f"get_weather({args})"


def check_vision(t, out):
    t.load(MODELS["chat"])
    content = [{"type": "text", "text": "What is the invoice number in this image? Reply with the number only."},
               {"type": "image_url", "image_url": {"url": data_uri(ASSETS / "ocr-test.png", "image/png")}}]
    text = chat(t, [{"role": "user", "content": content}])["message"].get("content") or ""
    if "4821" not in text:
        raise Fail(f"read {text[:80]!r}")
    return f"read {text.strip()[:30]!r}"


def check_anthropic(t, out):
    t.load(MODELS["chat"])
    body = {"model": "default", "max_tokens": 200, "messages": [{"role": "user", "content": "Reply with exactly one word: mango"}]}
    res = t.ok("POST", "/v1/messages", body)
    text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
    if "mango" not in text.lower():
        raise Fail(f"reply {json.dumps(res)[:200]}")
    return f"{text.strip()[:40]!r}"


def check_ollama(t, out):
    t.load(MODELS["chat"])
    t.ok("GET", "/api/tags")
    body = {"model": "default", "stream": False, "think": False,
            "messages": [{"role": "user", "content": "Reply with exactly one word: kiwi"}]}
    res = t.ok("POST", "/api/chat", body)
    text = (res.get("message") or {}).get("content", "")
    if "kiwi" not in text.lower():
        raise Fail(f"reply {json.dumps(res)[:200]}")
    return f"{text.strip()[:40]!r}"


def check_embeddings(t, out):
    t.load(MODELS["embed"])
    res = t.ok("POST", "/v1/embeddings", {"model": MODELS["embed"],
               "input": ["The cat sat on the mat.", "A kitten is resting on a rug.", "Quarterly tax filing deadline"]})
    v = [d["embedding"] for d in res["data"]]
    cos = lambda a, b: sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))
    near, far = cos(v[0], v[1]), cos(v[0], v[2])
    if len(v) != 3 or near <= far:
        raise Fail(f"similar {near:.2f} vs unrelated {far:.2f}")
    return f"dim {len(v[0])}, similar {near:.2f} > unrelated {far:.2f}"


def make_ocr_check(mid):
    def check(t, out):
        t.load(mid)
        q = urllib.parse.quote(mid, safe="")
        res = t.ok("POST", f"/v1/ocr?model={q}", {"input": data_uri(ASSETS / "ocr-test.png", "image/png"),
                                                    "response_format": "json"}, timeout=300)
        text = (res.get("data") or [{}])[0].get("text", "")
        score = similarity(text, OCR_TEXT)
        if score < 0.8:
            raise Fail(f"match {score:.0%}: {text[:80]!r}")
        return f"match {score:.0%}"
    return check


GLM_OCR = "zai-org/GLM-OCR"


def glm_messages():
    return [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": data_uri(ASSETS / "ocr-test.png", "image/png")}},
                                         {"type": "text", "text": "Text Recognition:"}]}]


def check_glm_ocr_chat(t, out):
    """GLM-OCR is a vision model, so the gateway's chat route is the other place it could be served."""
    t.load(GLM_OCR)
    res = t.ok("POST", "/v1/chat/completions", {"model": GLM_OCR, "max_tokens": 600, "messages": glm_messages()})
    score = similarity(res["choices"][0]["message"].get("content") or "", OCR_TEXT)
    if score < 0.8:
        raise Fail(f"match {score:.0%}")
    return f"match {score:.0%}"


def check_glm_ocr_direct(t, out):
    t.load(GLM_OCR)
    body = json.dumps({"model": GLM_OCR, "max_tokens": 600, "messages": glm_messages()}).encode()
    req = urllib.request.Request(t.direct(GLM_OCR) + "/v1/chat/completions", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        text = json.loads(r.read())["choices"][0]["message"].get("content") or ""
    score = similarity(text, OCR_TEXT)
    if score < 0.8:
        raise Fail(f"match {score:.0%}")
    return f"match {score:.0%} on its own port (not through the API)"


def check_image(t, out):
    t.load(MODELS["image"])
    body = {"model": MODELS["image"], "prompt": "API TEST: a red apple on a white table, studio photo",
            "size": "512x512", "n": 1, "response_format": "b64_json", "seed": 7}
    for attempt in (1, 2):  # the first render after a load can fail ("xh2a backend fail"); retry once
        code, res = t.call("POST", "/v1/images/generations", body, timeout=600)
        if code < 300:
            break
    if code >= 300:
        raise Fail(f"HTTP {code}: {json.dumps(res)[:200]}")
    png = base64.b64decode(res["data"][0]["b64_json"])
    w, h = png_size(png)
    (out / "image.png").write_bytes(png)
    return f"{w}x{h} PNG{' (2nd try)' if attempt == 2 else ''}"


def check_tts(t, out):
    t.load(MODELS["tts"])
    body = {"model": MODELS["tts"], "input": "This is the Tiiny API test, speaking in a cloned voice.",
            "ref_audio": base64.b64encode((ASSETS / "ref-voice.wav").read_bytes()).decode(),
            "ref_text": (ASSETS / "ref-voice.txt").read_text().strip(), "language": "en", "response_format": "wav"}
    wav = t.ok("POST", "/v1/audio/speech", body, raw=True, timeout=600)
    secs = wav_seconds(wav)
    (out / "speech.wav").write_bytes(wav)
    return f"{secs:.1f} s of audio"


def check_asr(t, out):
    t.load(MODELS["asr"])
    audio = to_16k_mono((ASSETS / "ref-voice.wav").read_bytes())
    body, ctype = multipart({"model": MODELS["asr"], "language": "en", "response_format": "json"},
                            {"file": ("ref-voice.wav", audio, "audio/wav")})
    res = t.ok("POST", "/v1/audio/transcriptions", body, ctype=ctype, timeout=300)
    text = res.get("text", "") if isinstance(res, dict) else str(res)
    score = similarity(text, (ASSETS / "ref-voice.txt").read_text())
    if score < 0.8:
        raise Fail(f"match {score:.0%}: {text[:80]!r}")
    return f"match {score:.0%}"


def check_music(t, out):
    t.load(MODELS["music"])
    body = {"model": MODELS["music"], "prompt": "API TEST: warm lo-fi piano loop, 90 bpm",
            "config": {"seconds_total": 5, "seed": 7}}
    wav = t.ok("POST", "/v1/music/generate/wav", body, raw=True, timeout=600)
    secs = wav_seconds(wav)
    (out / "loop.wav").write_bytes(wav)
    return f"{secs:.1f} s loop"


def check_3d(t, out):
    t.load(MODELS["3d"])
    t.ok("GET", "/v1/3d/capabilities")
    body, ctype = multipart({"stage": "shape", "params": "{}"},
                            {"image": ("mug.png", (ASSETS / "mug.png").read_bytes(), "image/png")})
    tid = t.ok("POST", "/v1/3d/tasks", body, ctype=ctype)["data"]["task_id"]
    t0 = time.time()
    while time.time() - t0 < 1200:
        time.sleep(5)
        d = t.ok("GET", f"/v1/3d/tasks/{tid}")["data"]
        if d["status"] in ("completed", "failed", "cancelled", "error"):
            break
    if d["status"] != "completed":
        raise Fail(f"shape task {d['status']}: {d.get('error') or d.get('message')}")
    output = (d.get("result") or {}).get("output") or {}
    glb = base64.b64decode(output.get("glb") or output.get("mesh") or "")
    if glb[:4] != b"glTF":
        raise Fail("no GLB in the result")
    (out / "shape.glb").write_bytes(glb)
    return f"shape GLB {len(glb) // 1024} KB in {time.time() - t0:.0f} s"


# (section, check, function, model). Run a section by name (`api_test.py ocr`) or one check (`api_test.py chat-tools`).
CHECKS = [
    ("info", "info", check_info, None),
    ("chat", "chat", check_chat, MODELS["chat"]),
    ("chat", "chat-stream", check_stream, MODELS["chat"]),
    ("chat", "chat-tools", check_tools, MODELS["chat"]),
    ("chat", "chat-vision", check_vision, MODELS["chat"]),
    ("chat", "chat-anthropic", check_anthropic, MODELS["chat"]),
    ("chat", "chat-ollama", check_ollama, MODELS["chat"]),
    ("embeddings", "embeddings", check_embeddings, MODELS["embed"]),
    *[("ocr", f"ocr-{m.split('/')[1]}", make_ocr_check(m), m) for m in MODELS["ocr"]],
    ("ocr", "ocr-GLM-OCR-chat", check_glm_ocr_chat, "zai-org/GLM-OCR"),
    ("ocr", "ocr-GLM-OCR-direct", check_glm_ocr_direct, "zai-org/GLM-OCR"),
    ("image", "image", check_image, MODELS["image"]),
    ("audio", "audio-tts", check_tts, MODELS["tts"]),
    ("audio", "audio-asr", check_asr, MODELS["asr"]),
    ("music", "music", check_music, MODELS["music"]),
    ("3d", "3d", check_3d, MODELS["3d"]),
]
SECTIONS = list(dict.fromkeys(c[0] for c in CHECKS))


def device():
    url, key = os.environ.get("TIINY_URL"), os.environ.get("TIINY_KEY")
    if not url:
        sys.exit("Set TIINY_URL (e.g. http://192.168.1.50) and TIINY_KEY (Settings > API key in TiinyOS).")
    return url, key or ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("only", nargs="*", help="sections or check names to run (default: everything)")
    ap.add_argument("--skip", help="comma-separated sections or check names to leave out")
    ap.add_argument("--list", action="store_true", help="list the checks and exit")
    ap.add_argument("--no-restore", action="store_true", help="don't reload the models that were running before")
    a = ap.parse_args()
    known = set(SECTIONS) | {c[1] for c in CHECKS}
    wanted = [w for spec in a.only for w in spec.split(",") if w]
    unknown = [w for w in wanted + (a.skip or "").split(",") if w and w not in known]
    if unknown:
        sys.exit(f"unknown section/check: {', '.join(unknown)}. Sections: {' '.join(SECTIONS)} (--list for checks)")
    pick = lambda names, c: c[0] in names or c[1] in names
    skip = (a.skip or "").split(",")
    checks = [c for c in CHECKS if (not wanted or pick(wanted, c)) and not pick(skip, c)]
    if a.list:
        for section, name, _, mid in checks:
            print(f"{section:11} {name:24} {mid or '-'}")
        return
    t = Tiiny(*device())
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = HERE.parent / "snapshots" / f"api-test-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    before = list(t.running())
    results = []
    for section, name, fn, mid in checks:
        t0 = time.time()
        try:
            detail, status = fn(t, out), "PASS"
        except Fail as e:
            detail, status = str(e), "FAIL"
        except Skip as e:
            detail, status = str(e), "SKIP"
        except Exception as e:  # a crash in one check shouldn't stop the walk
            detail, status = f"{type(e).__name__}: {e}", "FAIL"
        results.append({"section": section, "check": name, "model": mid, "status": status, "seconds": round(time.time() - t0, 1), "detail": detail})
        print(f"{status:4}  {name:26} {results[-1]['seconds']:7.1f}s  {detail}", flush=True)
    if before and not a.no_restore:
        for mid in before:
            try:
                t.load(mid)
            except Fail as e:
                print(f"couldn't reload {mid}: {e}")
    passed = sum(r["status"] == "PASS" for r in results)
    failed = sum(r["status"] == "FAIL" for r in results)
    print(f"\n{passed} passed, {failed} failed, {len(results) - passed - failed} skipped. Report and outputs: {out}")
    (out / "report.json").write_text(json.dumps({"when": stamp, "ran": wanted or ["all"], "results": results}, indent=1))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
