"""Build the fixed eval set for tools/jev_bench.py from public datasets on Hugging Face.

    python tools/jev_eval_build.py            # uses tools/jev_eval_manifest.json (the same items everyone uses)
    python tools/jev_eval_build.py --new      # pick a new balanced sample and rewrite the manifest
    python tools/jev_eval_build.py --cached-only   # after a rate limit: use only what's already fetched

8 public datasets, 200 label-balanced items each (1,600 in all), covering the three Jev question types:
choice (AG News topic, emotion), score (SST-5 sentiment, Amazon review stars) and yes/no "noul" (SMS spam, SST-2
sentiment, tweet irony, BoolQ). Rows come from Hugging Face's public dataset API (no account). The repo only keeps
the manifest (which rows), not the texts: they're saved to snapshots/jev-eval/evalset.json (git-ignored).
"""
import argparse
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
MANIFEST = HERE / "jev_eval_manifest.json"
OUT = HERE.parent / "snapshots" / "jev-eval" / "evalset.json"
WINDOW = 1000  # sample from the first rows of each split, so the manifest stays small and stable
PER_TASK = 200
UA = {"User-Agent": "tiiny-api-notes-jev-bench/1.0"}

# name, dataset, config, split, question type, how to read one row -> (state, gold), question
SPECS = [
    ("ag_news", "fancyzhx/ag_news", "default", "test", "choice",
     lambda r: (r["text"], ["World", "Sports", "Business", "Sci/Tech"][r["label"]]),
     {"type": "choice", "instructions": "What is this news article about?",
      "criteria": {"World": "world news and politics", "Sports": "sports", "Business": "business, economy, companies",
                   "Sci/Tech": "science and technology"}}),
    ("emotion", "dair-ai/emotion", "split", "test", "choice",
     lambda r: (r["text"], ["sadness", "joy", "love", "anger", "fear", "surprise"][r["label"]]),
     {"type": "choice", "instructions": "Which emotion does the writer express?",
      "criteria": {"sadness": "", "joy": "", "love": "", "anger": "", "fear": "", "surprise": ""}}),
    ("sst5", "SetFit/sst5", "default", "test", "score",
     lambda r: (r["text"], int(r["label"])),
     {"type": "score", "instructions": "How positive is the sentiment of this movie review?",
      "criteria": ["very negative", "negative", "neutral", "positive", "very positive"]}),
    ("amazon_stars", "SetFit/amazon_reviews_multi_en", "default", "test", "score",
     lambda r: (r["text"], int(r["label"])),
     {"type": "score", "instructions": "How many stars did the customer give this product?",
      "criteria": ["1 star", "2 stars", "3 stars", "4 stars", "5 stars"]}),
    ("sms_spam", "ucirvine/sms_spam", "plain_text", "train", "noul",
     lambda r: (r["sms"], r["label"] == 1),
     {"type": "noul", "instructions": "Is this message spam?"}),
    ("sst2", "stanfordnlp/sst2", "default", "validation", "noul",
     lambda r: (r["sentence"], r["label"] == 1),
     {"type": "noul", "instructions": "Is the sentiment of this text positive?"}),
    ("irony", "cardiffnlp/tweet_eval", "irony", "test", "noul",
     lambda r: (r["text"], r["label"] == 1),
     {"type": "noul", "instructions": "Is this tweet ironic?"}),
    ("boolq", "google/boolq", "default", "validation", "noul",
     lambda r: ({"passage": r["passage"], "question": r["question"]}, bool(r["answer"])),
     {"type": "noul", "instructions": "Based on the passage, is the answer to the question yes?"}),
]


def fetch(dataset, config, split, n):
    """The first n rows, 100 per request, paced. A 429 (rate limit) stops the build: wait a while and rerun."""
    rows = []
    for off in range(0, n, 100):
        q = urllib.parse.urlencode({"dataset": dataset, "config": config, "split": split, "offset": off,
                                    "length": min(100, n - off)})
        req = urllib.request.Request("https://datasets-server.huggingface.co/rows?" + q, headers=UA)
        try:
            page = json.loads(urllib.request.urlopen(req, timeout=60).read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise SystemExit(f"Hugging Face rate limit (429) while reading {dataset}: wait some minutes and rerun. "
                                 "Already-fetched tasks are cached and won't be fetched again.")
            raise
        rows += [r["row"] for r in page["rows"]]
        time.sleep(2)  # be gentle with the public API
        if len(page["rows"]) < 100:
            break
    return rows


def balanced(gold_by_idx, n, seed):
    """n row indices, as even as possible across the gold labels (scores and booleans count as labels too)."""
    by = defaultdict(list)
    for i, g in gold_by_idx.items():
        by[g].append(i)
    rng = random.Random(seed)
    for v in by.values():
        rng.shuffle(v)
    pick, labels = [], sorted(by, key=str)
    while len(pick) < n and any(by.values()):
        for g in labels:
            if by[g] and len(pick) < n:
                pick.append(by[g].pop())
    return sorted(pick)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--new", action="store_true", help="pick a new sample and rewrite tools/jev_eval_manifest.json")
    ap.add_argument("--cached-only", action="store_true", help="don't contact Hugging Face: build from the tasks already fetched")
    a = ap.parse_args()
    manifest = {} if a.new or not MANIFEST.exists() else json.loads(MANIFEST.read_text("utf-8"))
    manifest.pop("_about", None)
    items = []
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for name, dataset, config, split, qtype, read, question in SPECS:
        idx = manifest.get(name)
        cache = OUT.parent / f"rows-{name}.json"  # fetched rows, so a rerun after a rate limit skips finished tasks
        need = (max(idx) + 1) if idx else WINDOW
        rows = json.loads(cache.read_text("utf-8")) if cache.exists() else []
        if len(rows) < need:
            if a.cached_only:
                print(f"{name:13} not fetched yet, skipped (--cached-only)", flush=True)
                continue
            rows = fetch(dataset, config, split, need)
            cache.write_text(json.dumps(rows, ensure_ascii=False), "utf-8")
        if not idx:
            idx = balanced({i: read(r)[1] for i, r in enumerate(rows)}, PER_TASK, seed=f"jev-{name}")
            manifest[name] = idx
            MANIFEST.write_text(json.dumps({"_about": "row indices per task, used by tools/jev_eval_build.py",
                                            **{k: v for k, v in manifest.items() if k != "_about"}},
                                           separators=(",", ":")), "utf-8")
        for i in idx:
            state, gold = read(rows[i])
            items.append({"id": f"{name}-{i}", "task": name, "type": qtype, "dataset": dataset, "row": i,
                          "state": state, "question": question, "gold": gold})
        golds = defaultdict(int)
        for it in items:
            if it["task"] == name:
                golds[str(it["gold"])] += 1
        print(f"{name:13} {dataset:34} {len(idx)} items  labels {dict(golds)}", flush=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False), "utf-8")
    print(f"\n{len(items)} items -> {OUT}")


if __name__ == "__main__":
    main()
