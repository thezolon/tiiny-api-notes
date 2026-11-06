"""Write docs/MODELS.md: every model in the Tiiny Model Store, from the device's own catalogue.

Uses GET /api/v1/models/online_models (the list TiinyOS's Model Store shows). Only the store's facts go in the file:
nothing about your device (which models you downloaded or run), no likes, no descriptions.

Usage:  python tools/model_list.py           (device from TIINY_URL / TIINY_KEY, else TiinyOS's config on this PC)
        python tools/model_list.py --cached  (rebuild from the last fetch, e.g. after editing model_licenses.json)
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "MODELS.md"
# Licenses, read by hand from each model's Hugging Face repo (or its base model's): see the file for sources
LICENSES = json.loads((ROOT / "tools" / "model_licenses.json").read_text("utf-8"))
LICENSES_CHECKED = "2026-11-06"
HEADER = "| model | params | NPU | size | context | can do | license |"
# Store types, grouped the way people ask about them
GROUPS = [
    ("Chat with vision", ["Image-Text-to-Text"]),
    ("Chat (text only)", ["Text Generation"]),
    ("Image creation and editing", ["Text-to-Image", "Image-to-Image"]),
    ("Reading text in images (OCR)", ["Image-to-Text"]),
    ("Speech to text", ["ASR"]),
    ("Text to speech", ["Text-to-Speech"]),
    ("Music", ["Music Generation"]),
    ("3D", ["Image-to-3D"]),
    ("Video", ["Text-to-Video", "Image-to-Video"]),
    ("Embeddings (for search and the vault)", ["Text Embedding"]),
    ("Rerankers", ["Text Reranking"]),
    ("Classifiers (Jev / System One, `POST /v1/systemone`)", ["Text Classification"]),
]


def device():
    url, key = os.environ.get("TIINY_URL"), os.environ.get("TIINY_KEY")
    if not (url and key):
        try:
            c = json.loads((Path.home() / ".local" / "tiiny" / "config.json").read_text("utf-8"))
            url = url or "http://" + c["deviceAddress"]
            key = key or c["account"]["authKey"]
        except (OSError, ValueError, KeyError):
            sys.exit("Set TIINY_URL and TIINY_KEY (TiinyOS → Settings → API Key).")
    return url.rstrip("/"), key


def fetch(base, key):
    req = urllib.request.Request(base + "/api/v1/models/online_models", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"The device answered {e.code}." + (" Check the API key." if e.code in (401, 403) else ""))


def gb(n):
    return f"{n / 1e9:.1f} GB" if n else "?"


def ctx(n):
    return f"{n // 1024}K" if n and n >= 1024 else (str(n) if n else "")


def what_it_does(m):
    bits = list(m.get("supported") or [])
    if "Image" in (m.get("input") or "") and m.get("type") in ("Image-Text-to-Text",):
        bits.insert(0, "Vision")
    t = m.get("thinking") or {}
    if isinstance(t, dict) and t.get("supported") and "Reasoning" not in bits:
        bits.append("Thinking" + (" (toggle)" if t.get("toggleable") else ""))
    return ", ".join(dict.fromkeys(bits))


def license_cell(mid):
    lic = LICENSES.get(mid)
    if not lic:
        return "not checked"
    text = f"[{lic['license']}](https://huggingface.co/{lic['source']})" if lic.get("source") else lic["license"]
    return text + (" ⚠" if lic.get("limit") else "")


def row(m):
    size = max((t.get("size") or 0 for t in m.get("tags") or []), default=0)
    return (f"| `{m.get('model_id')}` | {m.get('params') or ''} | {m.get('npu_usage')}% | {gb(size)} | "
            f"{ctx(m.get('context_window'))} | {what_it_does(m)} | {license_cell(m.get('model_id'))} |")


def limits(store):
    ids = [m.get("model_id") for m in store]
    region = [i for i in ids if LICENSES.get(i, {}).get("region")]
    other = [i for i in ids if LICENSES.get(i, {}).get("limit") and i not in region]
    lines = [f"## Licenses with limits (checked {LICENSES_CHECKED})", "",
             "Most models are Apache-2.0 or MIT. These are the exceptions (⚠ in the tables). This is a summary of each "
             "license as published, not legal advice: read the license itself before relying on a model.", ""]
    lines += ["**Not licensed in some regions:**", ""]
    lines += [f"- `{i}`: {LICENSES[i]['limit']} ({LICENSES[i]['license']} license)" for i in region] + [""]
    lines += ["**Other limits:**", ""]
    lines += [f"- `{i}`: {LICENSES[i]['limit']} ({LICENSES[i]['license']})" for i in other] + [""]
    lines += ["Models built on another model (Tiiny's \"Turbo\" builds, LoRAs) link to the base model's license. "
              "Licenses ending in `?` come from the likely source repo, not a confirmed one.", ""]
    return lines


def main():
    cache = ROOT / "snapshots" / "online_models.json"  # git-ignored; lets --cached rebuild without the device
    if "--cached" in sys.argv:
        saved = json.loads(cache.read_text("utf-8"))
        store, today = saved["store"], saved["date"]
    else:
        store = fetch(*device())
        today = datetime.date.today().isoformat()
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps({"date": today, "store": store}), "utf-8")
    lines = [
        "# Models in the Tiiny Model Store", "",
        f"All {len(store)} models the Model Store offered on {today}, read from the device's own catalogue "
        "(`GET /api/v1/models/online_models`). Regenerate with `python tools/model_list.py`.", "",
        "- **NPU** = share of the Tiiny's NPU memory the model takes when loaded. Models that add up to more than 100% "
        "can't be loaded together; TiinyOS (or the API's `unload_candidate`) tells you what has to go.",
        "- **Size** = download size. **Context** = the longest prompt + reply it takes, in tokens.",
        "- Use any loaded chat model from other apps with the model name `default` (see [RECIPES.md](RECIPES.md)).", "",
    ] + limits(store)
    seen = set()
    for title, types in GROUPS:
        group = sorted((m for m in store if m.get("type") in types), key=lambda m: (m.get("npu_usage") or 0, m.get("model_id")))
        if not group:
            continue
        seen.update(m.get("model_id") for m in group)
        lines += [f"## {title} ({len(group)})", "", HEADER, "|---|---|---|---|---|---|---|"]
        lines += [row(m) for m in group] + [""]
    rest = [m for m in store if m.get("model_id") not in seen]
    if rest:
        lines += [f"## Other ({len(rest)})", "", HEADER, "|---|---|---|---|---|---|---|"]
        lines += [row(m) for m in sorted(rest, key=lambda m: m.get("model_id"))] + [""]
    OUT.write_text("\n".join(lines), "utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(store)} models")


if __name__ == "__main__":
    main()
