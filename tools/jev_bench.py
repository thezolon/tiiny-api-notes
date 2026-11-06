"""Benchmark the Tiiny's Jev / System One models (POST /v1/systemone) on a fixed public eval set.

    python tools/jev_eval_build.py                          # once: fetch the eval set (1,600 items)
    python tools/jev_bench.py                               # every downloaded Jev model, all items
    python tools/jev_bench.py --model vllm-sr/d3-edge --limit 20    # quick check: 20 items per task
    python tools/jev_bench.py --md docs/JEV-BENCH.md        # also write the results page

Each item is one request with one question about one text, as an app would send it. Per task: choice tasks report
accuracy and macro-F1; score tasks the mean absolute error of the expected score, argmax accuracy and Spearman
correlation; yes/no ("noul") tasks AUROC, accuracy at 0.5, Brier score; all report calibration error (ECE, 10 bins:
does a 0.9 confidence mean right 90% of the time?) and request time (median and 95th percentile). Needs TIINY_URL /
TIINY_KEY. Stops if a model has an update waiting (--allow-outdated to run anyway). Models the run loaded are unloaded
afterwards. Results: snapshots/jev-bench-<time>/report.json (git-ignored; it holds no dataset text).
"""
import argparse
import json
import statistics
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path

import api_test as at

HERE = Path(__file__).parent
EVALSET = HERE.parent / "snapshots" / "jev-eval" / "evalset.json"


def ece(conf, correct, bins=10):
    """Expected calibration error: the gap between confidence and accuracy, averaged over confidence bins."""
    total, err = len(conf), 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        sel = [i for i, c in enumerate(conf) if lo <= c < hi or (b == bins - 1 and c == 1.0)]
        if sel:
            err += len(sel) / total * abs(sum(correct[i] for i in sel) / len(sel) - sum(conf[i] for i in sel) / len(sel))
    return err


def auroc(scores, labels):
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    if len(set(a)) < 2 or len(set(b)) < 2:
        return None
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return cov / (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5


def metrics(kind, rows):
    ok = [r for r in rows if r.get("answer")]
    out = {"items": len(rows), "errors": len(rows) - len(ok)}
    ms = [r["ms"] for r in ok]
    if ms:
        out["p50_ms"] = round(statistics.median(ms))
        out["p95_ms"] = round(sorted(ms)[max(0, -(-len(ms) * 95 // 100) - 1)])  # nearest rank
    if not ok:
        return out
    if kind == "choice":
        golds = sorted({r["gold"] for r in ok})
        correct = [r["answer"].get("choice") == r["gold"] for r in ok]
        f1s = []
        for g in golds:
            tp = sum(1 for r in ok if r["gold"] == g and r["answer"].get("choice") == g)
            fp = sum(1 for r in ok if r["gold"] != g and r["answer"].get("choice") == g)
            fn = sum(1 for r in ok if r["gold"] == g and r["answer"].get("choice") != g)
            f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
        out.update(accuracy=sum(correct) / len(ok), macro_f1=statistics.mean(f1s),
                   ece=ece([r["answer"].get("confidence", 0) for r in ok], correct))
    elif kind == "score":
        exp = [r["answer"].get("score", 0) for r in ok]
        gold = [r["gold"] for r in ok]
        probs = [r["answer"].get("probabilities") or {} for r in ok]
        argmax = [max(p, key=p.get) if p else None for p in probs]
        correct = [str(g) == a for g, a in zip(gold, argmax)]
        out.update(mae=statistics.mean(abs(e - g) for e, g in zip(exp, gold)), argmax_accuracy=sum(correct) / len(ok),
                   spearman=spearman(exp, gold), ece=ece([max(p.values()) if p else 0 for p in probs], correct))
    else:
        p = [r["answer"].get("noul", 0.5) for r in ok]
        y = [bool(r["gold"]) for r in ok]
        correct = [(pi >= 0.5) == yi for pi, yi in zip(p, y)]
        out.update(auroc=auroc(p, y), accuracy=sum(correct) / len(ok),
                   brier=statistics.mean((pi - yi) ** 2 for pi, yi in zip(p, y)),
                   ece=ece([max(pi, 1 - pi) for pi in p], correct))
    return out


def run_model(t, model, items):
    rows = []
    for n, it in enumerate(items, 1):
        body = {"model": model, "state": it["state"], "questions": {"q": it["question"]}}
        t0 = time.time()
        code, res = t.call("POST", "/v1/systemone", body, timeout=300)
        ms = (time.time() - t0) * 1000
        ans = ((res or {}).get("answers") or {}).get("q") if code < 300 else None
        rows.append({"id": it["id"], "task": it["task"], "type": it["type"], "gold": it["gold"], "ms": ms,
                     "answer": ans, "error": None if ans else code})
        if n % 100 == 0:
            print(f"    {n}/{len(items)}", flush=True)
    return rows


def fmt(v, pct=False):
    if v is None:
        return "-"
    return f"{v * 100:.1f}%" if pct else f"{v:.3f}" if isinstance(v, float) else str(v)


def write_md(path, report):
    models = list(report["models"])
    tasks = report["tasks"]
    m = report["models"]
    head = "| task | " + " | ".join(f"`{x}`" for x in models) + " |"
    sep = "|---|" + "---|" * len(models)
    out = ["# Jev / System One models on the Tiiny: accuracy, calibration, speed", "",
           f"Generated by `python tools/jev_bench.py --md docs/JEV-BENCH.md` on {report['when']}, TiinyOS "
           f"{report['tiiny_os']}, {report['per_task']} items per task (eval set: `tools/jev_eval_build.py`, public "
           "Hugging Face datasets; the repo keeps only which rows are used). One question per request, one request at "
           "a time. Model versions: " + ", ".join(f"`{k}` {v.get('version')}" for k, v in report["model_versions"].items())
           + ".", "",
           "How to read it: **choice** tasks pick one label (accuracy, higher is better); **score** tasks rate on a scale "
           "(MAE = average distance from the right level, lower is better); **yes/no** tasks give a probability "
           "(AUROC: 0.5 is guessing, 1.0 is perfect). ECE = calibration error (how far confidence is from actual "
           "accuracy; lower is better).", "",
           "## Summary", "", head, sep]
    for task, kind in tasks.items():
        key, pct = {"choice": ("accuracy", True), "score": ("mae", False), "noul": ("auroc", False)}[kind]
        label = {"choice": "accuracy", "score": "MAE", "noul": "AUROC"}[kind]
        out.append(f"| {task} ({kind}, {label}) | " + " | ".join(fmt(m[x]["tasks"][task].get(key), pct) for x in models) + " |")
    out.append("| **median request time** | " + " | ".join(f"{m[x]['p50_ms']} ms" for x in models) + " |")
    for kind, cols in (("choice", [("accuracy", True), ("macro_f1", False), ("ece", False)]),
                       ("score", [("mae", False), ("argmax_accuracy", True), ("spearman", False), ("ece", False)]),
                       ("noul", [("auroc", False), ("accuracy", True), ("brier", False), ("ece", False)])):
        kt = [tk for tk, k in tasks.items() if k == kind]
        if not kt:
            continue
        out += ["", f"## {kind} tasks", "", "| task | model | " + " | ".join(c for c, _ in cols) + " | p50 ms | p95 ms | errors |",
                "|---|---|" + "---|" * (len(cols) + 3)]
        for task in kt:
            for x in models:
                r = m[x]["tasks"][task]
                out.append(f"| {task} | `{x}` | " + " | ".join(fmt(r.get(c), p) for c, p in cols)
                           + f" | {r.get('p50_ms', '-')} | {r.get('p95_ms', '-')} | {r.get('errors', 0)} |")
    out += ["", "Datasets: AG News, dair-ai/emotion (choice); SST-5, Amazon reviews (score); SMS spam, SST-2, "
            "TweetEval irony, BoolQ (yes/no). Inspired by the jeff project's bench/RESULTS.md."]
    Path(path).write_text("\n".join(out) + "\n", "utf-8", newline="\n")
    print(f"wrote {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", action="append", help="model id (repeatable); default: every downloaded Jev model")
    ap.add_argument("--limit", type=int, help="items per task (default: all, 200)")
    ap.add_argument("--md", help="also write the results page (e.g. docs/JEV-BENCH.md)")
    ap.add_argument("--allow-outdated", action="store_true")
    a = ap.parse_args()
    if not EVALSET.exists():
        raise SystemExit("No eval set yet: run `python tools/jev_eval_build.py` first.")
    items = json.loads(EVALSET.read_text("utf-8"))
    tasks = dict.fromkeys(it["task"] for it in items)
    tasks = {tk: next(it["type"] for it in items if it["task"] == tk) for tk in tasks}
    if a.limit:
        by = defaultdict(list)
        for it in items:
            by[it["task"]].append(it)
        items = [it for tk in tasks for it in by[tk][::max(1, len(by[tk]) // a.limit)][:a.limit]]
    t = at.Tiiny(*at.device())
    if t.call("GET", "/api/v1/models/running", timeout=15)[0] == 502:
        raise SystemExit("The Tiiny looks locked after a restart: run `tiiny login` or open the TiinyOS app, then rerun.")
    store = t.ok("GET", "/api/v1/models/online_models")
    store = {x.get("model_id"): x for x in (store if isinstance(store, list) else store.get("data", store))}
    have = at.model_versions(t, list(store))
    models = a.model or sorted(x for x in have if (store.get(x) or {}).get("type") == "Text Classification")
    models = [x for x in models if x in have]
    if not models:
        raise SystemExit("No Jev / Text Classification models downloaded.")
    versions = at.require_current(t, models, a.allow_outdated)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = HERE.parent / "snapshots" / f"jev-bench-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    report = {"when": time.strftime("%Y-%m-%d"), "tiiny_os": t.ok("GET", "/api/v1/sys/device_info").get("tiiny_os"),
              "per_task": a.limit or max(sum(1 for i in items if i["task"] == tk) for tk in tasks),
              "model_versions": versions, "tasks": tasks, "models": {}}
    before = set(t.running())
    try:
        for model in models:
            for other in set(t.running()) - {model}:
                t.ok("POST", f"/api/v1/models/{urllib.parse.quote(other, safe='')}/stop", {}, timeout=180)
            t.load(model)
            print(f"\n{model}: {len(items)} items", flush=True)
            t0 = time.time()
            rows = run_model(t, model, items)
            per = {tk: metrics(kind, [r for r in rows if r["task"] == tk]) for tk, kind in tasks.items()}
            ok_ms = [r["ms"] for r in rows if r["answer"]]
            report["models"][model] = {"seconds": round(time.time() - t0), "p50_ms": round(statistics.median(ok_ms)) if ok_ms else None,
                                       "tasks": per}
            for tk, r in per.items():
                main_m = {"choice": "accuracy", "score": "mae", "noul": "auroc"}[tasks[tk]]
                print(f"  {tk:13} {main_m} {fmt(r.get(main_m))}  ece {fmt(r.get('ece'))}  p50 {r.get('p50_ms')} ms"
                      f"{'  errors ' + str(r['errors']) if r['errors'] else ''}", flush=True)
    finally:
        for model in set(t.running()) - before:
            t.ok("POST", f"/api/v1/models/{urllib.parse.quote(model, safe='')}/stop", {}, timeout=180)
        (out / "report.json").write_text(json.dumps(report, indent=1), "utf-8")
        print(f"\nReport: {out / 'report.json'}")
    if a.md:
        write_md(a.md, report)


if __name__ == "__main__":
    main()
