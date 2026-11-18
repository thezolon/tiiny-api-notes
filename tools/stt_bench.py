"""Benchmark the Tiiny's speech-to-text models: word error rate and speed on a fixed public test set.

    python tools/stt_bench.py                         # every downloaded speech-to-text model
    python tools/stt_bench.py --model openai/Whisper-large-v3-turbo --limit 10
    python tools/stt_bench.py --md docs/STT.md        # also write the results page

Test set: the 73 clips of LibriSpeech's small "dummy" split (read English audiobook speech, CC-BY-4.0), fetched
once from Hugging Face's public dataset API into snapshots/stt-eval/ (git-ignored) and converted to 16 kHz mono WAV
with ffmpeg (needed on PATH), then sent to POST /v1/audio/transcriptions. Reports word error rate (after lower-casing and removing punctuation; lower is better), speed as seconds
of audio per second of processing, and the median time per clip. Needs TIINY_URL / TIINY_KEY. Stops if a model has
an update waiting (--allow-outdated to run anyway). Models the run loaded are unloaded afterwards.
"""
import argparse
import json
import re
import shutil
import statistics
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import api_test as at

HERE = Path(__file__).parent
CACHE = HERE.parent / "snapshots" / "stt-eval"
DATASET = ("hf-internal-testing/librispeech_asr_dummy", "clean", "validation")
UA = {"User-Agent": "tiiny-api-notes-stt-bench/1.0"}
WORDS = {"mr": "mister", "mrs": "missus", "dr": "doctor", "st": "saint"}  # spoken forms LibriSpeech writes out


def build():
    """Fetch the clips and transcripts once (2 requests for the list, then one per clip, paced)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    index = CACHE / "clips.json"
    if index.exists():
        return json.loads(index.read_text("utf-8"))
    q = urllib.parse.urlencode({"dataset": DATASET[0], "config": DATASET[1], "split": DATASET[2], "offset": 0, "length": 100})
    try:
        rows = json.loads(urllib.request.urlopen(urllib.request.Request(
            "https://datasets-server.huggingface.co/rows?" + q, headers=UA), timeout=60).read())["rows"]
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Hugging Face answered {e.code}: try again in a few minutes.")
    clips = []
    for r in rows:
        row = r["row"]
        path = CACHE / f"{row['id']}.flac"
        if not path.exists():
            try:
                path.write_bytes(urllib.request.urlopen(urllib.request.Request(row["audio"][0]["src"], headers=UA),
                                                        timeout=60).read())
            except urllib.error.HTTPError as e:
                raise SystemExit(f"Hugging Face answered {e.code} while downloading audio: rerun later "
                                 "(clips already fetched are kept).")
            time.sleep(0.5)
        clips.append({"id": row["id"], "file": path.name, "text": row["text"]})
    index.write_text(json.dumps(clips), "utf-8")
    return clips


def flac_seconds(data):
    """Duration from the FLAC STREAMINFO block: sample rate (20 bits) and total samples (36 bits)."""
    if data[:4] != b"fLaC":
        return None
    info = data[8:8 + 34]
    rate = (info[10] << 12) | (info[11] << 4) | (info[12] >> 4)
    total = ((info[13] & 0x0F) << 32) | int.from_bytes(info[14:18], "big")
    return total / rate if rate else None


def norm(text):
    words = re.sub(r"[^a-z0-9' ]+", " ", (text or "").lower().replace("-", " ")).split()
    return [WORDS.get(w.strip("'"), w.strip("'")) for w in words if w.strip("'")]


def wer_counts(ref, hyp):
    """(edits, reference words): word-level Levenshtein distance."""
    r, h = norm(ref), norm(hyp)
    prev = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        cur = [i] + [0] * len(h)
        for j, hw in enumerate(h, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rw != hw))
        prev = cur
    return prev[-1], len(r)


def to_wav(flac):
    ff = shutil.which("ffmpeg")
    if not ff:
        return None
    p = subprocess.run([ff, "-v", "quiet", "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"],
                       input=flac, capture_output=True, timeout=60)
    return p.stdout or None


def transcribe(t, model, name, data, ctype):
    body, mp = at.multipart({"model": model, "language": "en", "response_format": "json"}, {"file": (name, data, ctype)})
    t0 = time.time()
    try:
        code, res = t.call("POST", "/v1/audio/transcriptions", body, ctype=mp, timeout=120)
    except OSError as e:  # includes timeouts
        return 599, None, time.time() - t0, f"no answer ({e})"
    text = (res.get("text") if isinstance(res, dict) else None) if code < 300 else None
    return code, text, time.time() - t0, (None if code < 300 else json.dumps(res)[:160])


def wav_for(clip):
    """16 kHz mono WAV of a clip, converted once with ffmpeg and cached (FLAC can hang the request: see docs/STT.md)."""
    path = CACHE / clip["file"].replace(".flac", ".wav")
    if not path.exists():
        wav = to_wav((CACHE / clip["file"]).read_bytes())
        if not wav:
            raise SystemExit("Needs ffmpeg on PATH to convert the test clips to WAV (https://ffmpeg.org).")
        path.write_bytes(wav)
    return path.name, path.read_bytes()


def run_model(t, model, clips):
    rows = []
    for c in clips:
        secs = flac_seconds((CACHE / c["file"]).read_bytes())
        name, data = wav_for(c)
        code, text, dt, err = transcribe(t, model, name, data, "audio/wav")
        edits, words = wer_counts(c["text"], text) if text is not None else (None, len(norm(c["text"])))
        rows.append({"id": c["id"], "audio_s": secs, "seconds": dt, "edits": edits, "words": words, "error": err,
                     "text": text})
    ok = [r for r in rows if r["edits"] is not None]
    out = {"clips": len(rows), "errors": len(rows) - len(ok), "rows": rows}
    if ok:
        out["wer"] = sum(r["edits"] for r in ok) / sum(r["words"] for r in ok)
        audio = sum(r["audio_s"] or 0 for r in ok)
        out["speed_x"] = audio / sum(r["seconds"] for r in ok) if audio else None
        out["p50_s"] = statistics.median(r["seconds"] for r in ok)
        out["audio_minutes"] = audio / 60
    first = next((r["error"] for r in rows if r["error"]), None)
    if first:
        out["first_error"] = first
    return out


def write_md(path, report):
    out = ["# Speech to text on the Tiiny: accuracy and speed", "",
           f"Generated by `python tools/stt_bench.py --md docs/STT.md` on {report['when']}, TiinyOS {report['tiiny_os']}: "
           f"{report['clips']} clips ({report['audio_minutes']:.1f} minutes) of read English speech from LibriSpeech "
           "(Hugging Face `hf-internal-testing/librispeech_asr_dummy`, CC-BY-4.0), sent one at a time to "
           "`POST /v1/audio/transcriptions` with `language: en`. Model versions: "
           + ", ".join(f"`{k}` {v.get('version')}" for k, v in report["model_versions"].items()) + ".", "",
           "**Word error rate** = words wrong, missing or extra, per word of the real transcript (after lower-casing "
           "and removing punctuation): lower is better, 5% means about one word in twenty. **Speed** = seconds of "
           "audio per second of processing (10x = a minute of speech in 6 seconds).", "",
           "| model | word error rate | speed | median per clip | errors |", "|---|---|---|---|---|"]
    for m, r in sorted(report["models"].items(), key=lambda kv: kv[1].get("wer", 9)):
        wer = f"{r['wer'] * 100:.1f}%" if "wer" in r else "-"
        speed = f"{r['speed_x']:.1f}x" if r.get("speed_x") else "-"
        p50 = f"{r['p50_s']:.2f} s" if "p50_s" in r else "-"
        out.append(f"| `{m}` | {wer} | {speed} | {p50} | {r['errors']}"
                   + (f" ({r['first_error']})" if r.get("first_error") else "") + " |")
    out += ["", "## Things to know", "",
            "- **Send WAV, not FLAC.** A FLAC upload gets no answer at all from any of these models (no error, the "
            "request just hangs; tested 2026-11-18 on all six, 60 s each). The same clip as 16 kHz mono WAV comes back "
            "in about a second. Convert first, e.g. `ffmpeg -i in.flac -ac 1 -ar 16000 out.wav`."]
    for m, r in sorted(report["models"].items()):
        ph = [x for x in r.get("rows", []) if re.search(r"(thank you[.!]?\s*){2,}$", x.get("text") or "", re.I)]
        if ph:
            out.append(f"- **`{m}` sometimes adds words that aren't there:** {len(ph)} of {r['clips']} clips ended in "
                       "a made-up \"Thank you. Thank you. Thank you.\" (a known Whisper habit on the silence at the end "
                       "of a clip); that accounts for part of its error rate. Trim trailing silence or check the end "
                       "of its transcripts.")
    out += ["- Some models occasionally run two words together where sentences join (\"burkettFoster\"), counted "
            "as errors here.", "",
            "Clean, read English is the easy case: expect higher error rates on noisy audio, accents, several "
            "speakers or other languages. Run it on your own Tiiny with `python tools/stt_bench.py` (needs ffmpeg)."]
    Path(path).write_text("\n".join(out) + "\n", "utf-8", newline="\n")
    print(f"wrote {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", action="append", help="model id (repeatable); default: every downloaded ASR model")
    ap.add_argument("--limit", type=int, help="first N clips only (quick check)")
    ap.add_argument("--md", help="also write the results page (e.g. docs/STT.md)")
    ap.add_argument("--allow-outdated", action="store_true")
    a = ap.parse_args()
    clips = build()[:a.limit] if a.limit else build()
    t = at.Tiiny(*at.device())
    if t.call("GET", "/api/v1/models/running", timeout=15)[0] == 502:
        raise SystemExit("The Tiiny looks locked after a restart: run `tiiny login` or open the TiinyOS app, then rerun.")
    have = t.ok("GET", "/api/v1/models/?including_downloading=false")
    have = have.get("data", have) if isinstance(have, dict) else have
    models = a.model or sorted(m["id"] for m in have if m.get("type") == "ASR")
    versions = at.require_current(t, models, a.allow_outdated)
    audio_min = sum(flac_seconds((CACHE / c["file"]).read_bytes()) or 0 for c in clips) / 60
    report = {"when": time.strftime("%Y-%m-%d"), "tiiny_os": t.ok("GET", "/api/v1/sys/device_info").get("tiiny_os"),
              "clips": len(clips), "audio_minutes": audio_min, "model_versions": versions, "models": {}}
    before = set(t.running())
    out_dir = HERE.parent / "snapshots" / f"stt-bench-{time.strftime('%Y%m%d-%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        for model in models:
            for other in set(t.running()) - {model}:
                t.ok("POST", f"/api/v1/models/{urllib.parse.quote(other, safe='')}/stop", {}, timeout=180)
            t.load(model)
            r = run_model(t, model, clips)
            report["models"][model] = r
            print(f"{model:45} WER {r.get('wer', 0) * 100:5.1f}%  speed {r.get('speed_x') or 0:5.1f}x  "
                  f"p50 {r.get('p50_s', 0):.2f} s  errors {r['errors']}"
                  + (f"  ({r['first_error']})" if r.get("first_error") else ""), flush=True)
    finally:
        for model in set(t.running()) - before:
            t.ok("POST", f"/api/v1/models/{urllib.parse.quote(model, safe='')}/stop", {}, timeout=180)
        (out_dir / "report.json").write_text(json.dumps(report, indent=1), "utf-8")
        print(f"Report: {out_dir / 'report.json'}")
    if a.md:
        write_md(a.md, report)


if __name__ == "__main__":
    main()
