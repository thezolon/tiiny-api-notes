"""Compare the Tiiny CLI with the direct API, feature by feature, on your own Tiiny.

    python tools/cli_compare.py                      # everything
    python tools/cli_compare.py chat ocr-GLM         # some cases (--list shows them)
    python tools/cli_compare.py --cli C:/path/tiiny.exe

Each case loads the model once, runs the CLI command and the matching tools/api_test.py check, and scores both the
same way (same prompt, same test image, same reference text). Needs: TIINY_URL / TIINY_KEY (as for api_test.py), the
Tiiny CLI installed and signed in (`tiiny login`), and tools/assets/ (ASR needs ref-voice.wav + ref-voice.txt).
The CLI is pointed at the same address as TIINY_URL, so USB vs Wi-Fi is your choice. Models the run loaded are
unloaded afterwards. Report: snapshots/cli-compare-<time>/report.json (git-ignored).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import api_test as at

HERE = Path(__file__).parent


def find_cli(given):
    for c in [given, shutil.which("tiiny"), str(Path.home() / ".local" / "tiiny" / "bin" / "tiiny.exe"),
              str(Path.home() / ".local" / "tiiny" / "bin" / "tiiny")]:
        if c and Path(c).exists():
            return c
    sys.exit("Tiiny CLI not found: install it or pass --cli <path>.")


def png_ok(p):
    return p.exists() and p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def cli_text(o):
    """The CLI prints file results as `File: <path> Content: <the API's JSON>`; pull the text out of that JSON."""
    if "Content:" in o:
        body = o.split("Content:", 1)[1].strip()
    else:  # ASR prints `File "<path>" <label>: <text>`
        body = re.sub(r'^File "[^"]*"[^:]*:\s*', "", o.strip())
    try:
        j = json.loads(body)
    except ValueError:
        return body
    if isinstance(j, dict) and j.get("data"):
        d = j["data"][0]
        return d.get("text") or "\n".join(l.get("text", "") for l in d.get("lines") or [])
    return j.get("text", body) if isinstance(j, dict) else body


def ocr_score(o):
    return at.similarity(cli_text(o), at.OCR_TEXT)


def asr_ref():
    wav, txt = at.ASSETS / "ref-voice.wav", at.ASSETS / "ref-voice.txt"
    return (wav, txt.read_text(encoding="utf-8").strip()) if wav.exists() and txt.exists() else (None, None)


def cases(out):
    wav, ref = asr_ref()
    img = str(at.ASSETS / "ocr-test.png")
    m = at.MODELS
    yield ("chat", m["chat"], ["run", "-m", m["chat"], "-p", "Reply with exactly one word: pineapple"], "chat",
           lambda o: ("pineapple" in o.lower(), o.strip()[:40]))
    yield ("vision", m["chat"], ["run", "-m", m["chat"], "-p", "What is the invoice number in this image? Reply with the number only.",
                                 "-f", img], "chat-vision", lambda o: ("4821" in o, o.strip()[:40]))
    yield ("embeddings", m["embed"], ["run", "embed", "-m", m["embed"], "-p", "The cat sat on the mat."], "embeddings",
           lambda o: (len(re.findall(r"-?\d+\.\d+", o)) > 16, f"{len(re.findall(r'-?[0-9]+[.][0-9]+', o))} numbers"))
    for mid in m["ocr"]:
        name = "ocr-" + mid.split("/")[1].replace("PP-OCRv6-", "PP-")
        yield (name, mid, ["run", "ocr", "-m", mid, "-f", img], "ocr-" + mid.split("/")[1],
               lambda o: (ocr_score(o) >= 0.8, f"match {ocr_score(o):.0%}"))
    yield ("image", m["image"], ["run", "image", "-m", m["image"], "-p", "API TEST: a red apple on a white table, studio photo",
                                 "-o", str(out / "cli-image.png")], "image",
           lambda o: (png_ok(out / "cli-image.png"), "PNG written" if png_ok(out / "cli-image.png") else o[-80:]))
    if wav:
        yield ("asr", m["asr"], ["run", "asr", "-m", m["asr"], "-f", str(wav), "--language", "en"], "audio-asr",
               lambda o: (at.similarity(cli_text(o), ref) >= 0.8, f"match {at.similarity(cli_text(o), ref):.0%}"))


def run_cli(cli, addr, args):
    t0 = time.time()
    try:
        p = subprocess.run([cli, "--device-address", addr, *args], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900)
        return p.returncode, (p.stdout + "\n" + p.stderr).strip(), time.time() - t0
    except subprocess.TimeoutExpired:
        return "timeout", "", time.time() - t0


def run_api(t, check, out):
    fn = next(c[2] for c in at.CHECKS if c[1] == check)
    t0 = time.time()
    try:
        return "PASS", fn(t, out), time.time() - t0
    except at.Skip as e:
        return "SKIP", str(e), time.time() - t0
    except Exception as e:
        return "FAIL", str(e)[:120], time.time() - t0


def bench(t, cli, addr, model):
    """Writing speed of the chat model: `tiiny bench` vs the API's own llama.cpp timings for a 256-token answer."""
    t.load(model)
    rc, o, _ = run_cli(cli, addr, ["bench", model, "--token-sizes", "256"])
    nums = re.findall(r"Output TPS:\s*(\d+(?:\.\d+)?)", o)  # `tiiny bench` prints "Output TPS: 30.77"
    res = t.ok("POST", "/v1/chat/completions", {"model": "default", "max_tokens": 256, "temperature": 0.7,
               "chat_template_kwargs": {"enable_thinking": False}, "cache_prompt": False,
               "messages": [{"role": "user", "content": f"Run {time.time_ns()}. Write a long story about a lighthouse."}]})
    api_tps = (res.get("timings") or {}).get("predicted_per_second")
    return {"cli_rc": rc, "cli_tok_s": nums, "cli_output": o[-600:], "api_tok_s": round(api_tps, 1) if api_tps else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("only", nargs="*", help="case names (default: all, plus bench)")
    ap.add_argument("--cli", help="path to the tiiny CLI")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    url, key = at.device()
    t = at.Tiiny(url, key)
    addr = urllib.parse.urlparse(url).hostname
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = HERE.parent / "snapshots" / f"cli-compare-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    todo = [c for c in cases(out) if not a.only or c[0] in a.only]
    if a.list:
        for c in todo:
            print(f"{c[0]:16} {c[1]}")
        print("bench            (chat model writing speed)")
        return
    cli = find_cli(a.cli)
    code = t.call("GET", "/api/v1/models/running", timeout=15)[0]
    if code == 502:
        sys.exit("The Tiiny looks locked after a restart: run `tiiny login` or open the TiinyOS app, then rerun.")
    rc, ver, _ = run_cli(cli, addr, ["status"])
    print(f"CLI {Path(cli).name} via {addr}: {'connected' if rc == 0 else 'NOT connected: ' + ver[-120:]}", flush=True)
    before = set(t.running())
    rows = []
    print(f"{'case':16} {'CLI':38} {'API':38}", flush=True)
    try:
        for name, mid, args, check, judge in todo:
            t.load(mid)
            rc, o, dt = run_cli(cli, addr, args)
            ok, detail = judge(o) if rc == 0 else (False, f"rc {rc}: {o[-90:]}")
            st, adetail, adt = run_api(t, check, out)
            rows.append({"case": name, "model": mid, "cli": "PASS" if ok else "FAIL", "cli_detail": detail,
                         "cli_s": round(dt, 1), "api": st, "api_detail": adetail, "api_s": round(adt, 1)})
            r = rows[-1]
            print(f"{name:16} {r['cli']:4} {r['cli_s']:5.1f}s {r['cli_detail'][:26]:26} {r['api']:4} {r['api_s']:5.1f}s "
                  f"{r['api_detail'][:26]}", flush=True)
        if not a.only or "bench" in a.only:
            b = bench(t, cli, addr, at.MODELS["chat"])
            rows.append({"case": "bench", **b})
            print(f"{'bench':16} CLI {', '.join(b['cli_tok_s']) or '?'} tok/s (rc {b['cli_rc']})   API {b['api_tok_s']} tok/s",
                  flush=True)
    finally:
        for mid in set(t.running()) - before:
            t.ok("POST", f"/api/v1/models/{urllib.parse.quote(mid, safe='')}/stop", {}, timeout=180)
    (out / "report.json").write_text(json.dumps({"when": stamp, "address": "set by TIINY_URL", "rows": rows}, indent=1),
                                     encoding="utf-8")
    print(f"\nReport: {out / 'report.json'}")


if __name__ == "__main__":
    main()
