"""Speed sweeps on your own Tiiny: how prompt length (and, for Jev, the number of questions) changes the speed.

    python tools/speed_test.py chat                                   # Qwen3.6-35B-A3B at 1K..128K context
    python tools/speed_test.py chat --model Qwen/Qwen3.8-27B --ctx 1k,8k,32k
    python tools/speed_test.py jev                                    # every downloaded Jev / System One model
    python tools/speed_test.py jev --model vllm-sr/d3-lite --ctx 1k,4k,16k --questions 1,8,32,64

chat: one request per context size, prompt caching off, a 128-token answer; reports llama.cpp's own timings
(prompt tok/s = reading/prefill, writing tok/s = generation) plus time to the full answer.
jev:  POST /v1/systemone with a state of the given size and N yes/no questions; reports the whole request time and
input tokens/s (these models don't write text: all the work is reading).
Context sizes above a model's limit are skipped. Needs TIINY_URL / TIINY_KEY (as for api_test.py). Models the run
loads are unloaded afterwards. Report: snapshots/speed-<time>/report.json (git-ignored).
"""
import argparse
import json
import time
import urllib.parse
from pathlib import Path

import api_test as at

HERE = Path(__file__).parent
SENTENCES = ["The lighthouse keeper logged the weather at dawn and noted three ships passing to the north.",
             "Quarterly figures showed a small rise in rail freight, mostly grain and timber from the coast.",
             "A committee reviewed the bridge repairs and asked for a second survey of the eastern pillars.",
             "The library extended its opening hours and added a reading room for local history records.",
             "Fishermen reported calm seas, a light southerly breeze and a large shoal of mackerel offshore.",
             "The orchestra rehearsed the second movement twice before the conductor was finally satisfied."]


def size(s):
    s = s.strip().lower()
    return int(float(s[:-1]) * 1024) if s.endswith("k") else int(s)


def filler(tokens):
    """About `tokens` tokens of varied, unique-per-run text (~20 tokens per sentence)."""
    n = max(1, tokens // 20)
    return f"Run {time.time_ns()}. " + " ".join(f"({i}) {SENTENCES[i % len(SENTENCES)]}" for i in range(n))


def store_info(t):
    st = t.ok("GET", "/api/v1/models/online_models")
    st = st if isinstance(st, list) else st.get("data", st)
    return {m.get("model_id"): m for m in st}


def downloaded(t):
    have = t.ok("GET", "/api/v1/models/?including_downloading=false")
    have = have.get("data", have) if isinstance(have, dict) else have
    return {m.get("id") for m in have}


def sweep_chat(t, model, ctxs, limit):
    rows = []
    for c in ctxs:
        if limit and c > limit - 600:
            print(f"  {c // 1024:>4}K  skipped (model limit {limit // 1024}K)", flush=True)
            continue
        body = {"model": model, "max_tokens": 128, "temperature": 0.7, "cache_prompt": False,
                "chat_template_kwargs": {"enable_thinking": False},
                "messages": [{"role": "user", "content": filler(c) + "\n\nSummarise the text above in one paragraph."}]}
        t0 = time.time()
        code, res = t.call("POST", "/v1/chat/completions", body, timeout=3600)
        wall = time.time() - t0
        if code >= 300:
            print(f"  {c // 1024:>4}K  HTTP {code}: {json.dumps(res)[:120]}", flush=True)
            rows.append({"ctx": c, "error": code})
            continue
        tm = res.get("timings") or {}
        row = {"ctx": c, "prompt_tokens": tm.get("prompt_n") or res.get("usage", {}).get("prompt_tokens"),
               "prompt_tok_s": round(tm.get("prompt_per_second") or 0, 1), "write_tok_s": round(tm.get("predicted_per_second") or 0, 1),
               "first_token_s": round((tm.get("prompt_ms") or 0) / 1000, 1), "total_s": round(wall, 1)}
        rows.append(row)
        print(f"  {c // 1024:>4}K  prompt {row['prompt_tokens']:>7} tok  reading {row['prompt_tok_s']:>7} tok/s  "
              f"writing {row['write_tok_s']:>5} tok/s  first token {row['first_token_s']:>6} s  total {row['total_s']:>6} s", flush=True)
    return rows


def sweep_jev(t, model, ctxs, counts, limit):
    rows = []
    for c in ctxs:
        if limit and c > limit - 600:
            print(f"  {c // 1024:>4}K  skipped (model limit {limit // 1024}K)", flush=True)
            continue
        for n in counts:
            state = filler(c)  # a fresh text every time, so no request reuses another's cached read
            qs = {f"q{i}": {"type": "noul", "instructions": f"Does the text mention item ({i})?"} for i in range(n)}
            t0 = time.time()
            code, res = t.call("POST", "/v1/systemone", {"model": model, "state": state, "questions": qs}, timeout=3600)
            wall = time.time() - t0
            if code >= 300:
                print(f"  {c // 1024:>4}K x {n:>2} questions  HTTP {code}: {json.dumps(res)[:120]}", flush=True)
                rows.append({"ctx": c, "questions": n, "error": code})
                continue
            tok = (res.get("usage") or {}).get("input_tokens")
            row = {"ctx": c, "questions": n, "input_tokens": tok, "total_s": round(wall, 2),
                   "input_tok_s": round(tok / wall, 1) if tok else None, "answers": len(res.get("answers") or {})}
            rows.append(row)
            print(f"  {c // 1024:>4}K x {n:>2} questions  {tok:>7} input tok  {row['total_s']:>7} s  "
                  f"{row['input_tok_s']:>8} tok/s  ({row['answers']} answers)", flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["chat", "jev"])
    ap.add_argument("--model", action="append", help="model id (repeatable); default: chat model / all downloaded Jev models")
    ap.add_argument("--ctx", help="context sizes, e.g. 1k,4k,16k (default chat 1k..128k, jev 1k,4k,16k)")
    ap.add_argument("--questions", default="1,8,32,64", help="jev: question counts (max 64)")
    ap.add_argument("--allow-outdated", action="store_true", help="run even if a model has an update waiting")
    a = ap.parse_args()
    t = at.Tiiny(*at.device())
    if t.call("GET", "/api/v1/models/running", timeout=15)[0] == 502:
        raise SystemExit("The Tiiny looks locked after a restart: run `tiiny login` or open the TiinyOS app, then rerun.")
    info, have = store_info(t), downloaded(t)
    if a.model:
        models = a.model
    elif a.mode == "chat":
        models = [at.MODELS["chat"]]
    else:
        models = sorted(m for m in have if (info.get(m) or {}).get("type") == "Text Classification")
        if not models:
            raise SystemExit("No Jev / Text Classification models downloaded (e.g. `tiiny download vllm-sr/d3-lite`).")
    versions = at.require_current(t, models, a.allow_outdated)
    ctxs = [size(x) for x in (a.ctx or ("1k,4k,16k,32k,64k,128k" if a.mode == "chat" else "1k,4k,16k")).split(",")]
    counts = [min(64, int(x)) for x in a.questions.split(",")]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = HERE.parent / "snapshots" / f"speed-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    tiiny_os = t.ok("GET", "/api/v1/sys/device_info").get("tiiny_os")
    before = set(t.running())
    report = {"when": stamp, "tiiny_os": tiiny_os, "mode": a.mode, "model_versions": versions, "models": {}}
    try:
        for m in models:
            if m not in have:
                print(f"\n{m}: not downloaded, skipped", flush=True)
                continue
            limit = (info.get(m) or {}).get("context_window")
            print(f"\n{m} (context limit {limit // 1024 if limit else '?'}K), TiinyOS {tiiny_os}", flush=True)
            for other in set(t.running()) - {m}:  # measure each model on its own
                t.ok("POST", f"/api/v1/models/{urllib.parse.quote(other, safe='')}/stop", {}, timeout=180)
            t.load(m)
            report["models"][m] = (sweep_chat(t, m, ctxs, limit) if a.mode == "chat"
                                   else sweep_jev(t, m, ctxs, counts, limit))
    finally:
        for m in set(t.running()) - before:
            t.ok("POST", f"/api/v1/models/{urllib.parse.quote(m, safe='')}/stop", {}, timeout=180)
        (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(f"\nReport: {out / 'report.json'}")


if __name__ == "__main__":
    main()
