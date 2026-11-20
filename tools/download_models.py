"""Download models to your Tiiny from a script, and know when they're done. Also lists and installs model updates.

    python tools/download_models.py hexgrad/Kokoro-82M k2-fsa/OmniVoice
    python tools/download_models.py --updates            # list installed models with an update waiting, then pick
    python tools/download_models.py --updates --all -y   # update every one of them, no questions
    python tools/download_models.py --update hexgrad/Kokoro-82M openbmb/VoxCPM2

Uses only the device API, so no Tiiny CLI is needed (works the same on Windows, macOS and Linux):
POST /api/v1/models/<id>/download starts a download, GET /api/v1/models/?including_downloading=true shows its
progress until `downloaded` (or `error`, e.g. when the Tiiny has no internet). The Tiiny downloads over its own Wi-Fi,
so mind your data on a phone hotspot. Needs TIINY_URL / TIINY_KEY.

Updates: there is no update call, so an update is DELETE /api/v1/models/<id> followed by a fresh download, one model at
a time (parallel downloads slow each other down). Which models have one waiting comes from the device's `need_update`
flag; the store's version number is not the build a download installs, so don't compare those. If a download fails
after the delete, the model is missing until you download it again (rerun the same command). Loaded models are
unloaded first.
"""
import argparse
import sys
import time
import urllib.parse

import api_test as at


def installed(t):
    rows = t.ok("GET", "/api/v1/models/?including_downloading=true")
    return rows.get("data", rows) if isinstance(rows, dict) else rows


def status(t, mid):
    m = next((m for m in installed(t) if m.get("id") == mid), None)
    return (m.get("status"), m.get("progress")) if m else (None, None)


def download(t, mid, size, timeout):
    """Start the download on the device and wait until it says downloaded. True when it finished."""
    t0, last, state, started = time.time(), None, (None, None), False
    if status(t, mid)[0] == "downloading":  # already under way (the app, or an earlier run): just wait for it
        print(f"{mid}: already downloading ({size:.1f} GB), waiting for it", flush=True)
        started = True
    else:
        print(f"{mid}: downloading {size:.1f} GB", flush=True)
        code, res = t.call("POST", f"/api/v1/models/{mid}/download", b"", timeout=60)
        if code >= 300:
            print(f"  the device refused: HTTP {code} {res}", flush=True)
            return False
    while time.time() - t0 < timeout:
        time.sleep(5)
        state = status(t, mid)
        started = started or state[0] == "downloading"
        if state != last and state[1] is not None:
            print(f"  {time.time() - t0:5.0f} s  {state[0]} {state[1]:.0f}%", flush=True)
            last = state
        if state[0] == "downloaded":
            print(f"  done in {time.time() - t0:.0f} s", flush=True)
            return True
        if state[0] == "error" and (started or time.time() - t0 > 30):
            print("  the device reports a download error (does the Tiiny have internet? `tiiny wifi status` or the "
                  "app shows it); rerun to try again", flush=True)
            return False
    print(f"  NOT finished after {timeout} s (status {state[0]}); rerun to try again", flush=True)
    return False


def size_gb(store_entry):
    return max((g.get("size") or 0 for g in (store_entry or {}).get("tags") or []), default=0) / 1e9


def outdated(t, store):
    """Installed models the device marks need_update, with their installed build and download size."""
    return [{"id": m["id"], "have": m.get("version"), "gb": size_gb(store.get(m["id"]))}
            for m in installed(t) if m.get("need_update") and m.get("status") == "downloaded"]


def ask(prompt):
    try:
        return input(prompt).strip().lower()
    except EOFError:  # no keyboard (piped or scheduled run): treat as "no"
        print()
        return ""


def pick(todo):
    """Ask which updates to install: all, none, or numbers like 1,3,5-7."""
    answer = ask("Update which? [all / numbers like 1,3,5-7 / Enter for none]: ")
    if answer in ("all", "a"):
        return todo
    chosen = set()
    for part in filter(None, answer.replace(" ", "").split(",")):
        lo, _, hi = part.partition("-")
        if not (lo.isdigit() and (not hi or hi.isdigit())):
            raise SystemExit(f"Didn't understand {part!r}; nothing was changed.")
        chosen.update(range(int(lo), int(hi or lo) + 1))
    return [m for i, m in enumerate(todo, 1) if i in chosen]


def update(t, todo, timeout):
    """Delete and download again, one model at a time. Returns the ids that didn't finish."""
    failed = []
    for n, m in enumerate(todo, 1):
        mid = m["id"]
        print(f"\n[{n}/{len(todo)}] {mid} (installed build {m['have'] or '?'})", flush=True)
        if mid in t.running():
            t.ok("POST", f"/api/v1/models/{urllib.parse.quote(mid, safe='')}/stop", {}, timeout=180)
            print("  unloaded it first", flush=True)
        code, res = t.call("DELETE", f"/api/v1/models/{mid}", timeout=120)
        if code >= 300:
            print(f"  delete failed (HTTP {code} {res}); left as it was", flush=True)
            failed.append(mid)
            continue
        if not download(t, mid, m["gb"], timeout):
            failed.append(mid)
            continue
        print(f"  now build {next((x.get('version') for x in installed(t) if x.get('id') == mid), '?')}", flush=True)
    return failed


def run_updates(a, t, store):
    waiting = outdated(t, store)
    if a.update:
        names = set(a.models)
        todo = [m for m in waiting if m["id"] in names]
        for mid in sorted(names - {m["id"] for m in todo}):
            print(f"{mid}: no update waiting (or not installed), skipped", flush=True)
    else:
        todo = waiting
    if not todo:
        print("No updates waiting. (The device reports none at all while it has no internet: check its Wi-Fi.)"
              if a.updates else "Nothing to update.")
        return []
    print(f"{len(todo)} model(s) with an update waiting:")
    for i, m in enumerate(todo, 1):
        print(f"  {i:2}. {m['id']:52} build {m['have'] or '?'}  {m['gb']:5.1f} GB")
    print(f"      total {sum(m['gb'] for m in todo):.1f} GB")
    if a.updates and not a.all:
        if a.yes or not sys.stdin.isatty():
            print("Add --all (and -y) to update them all, or use --update <ids>.")
            return []
        todo = pick(todo)
        if not todo:
            print("Nothing chosen; nothing was changed.")
            return []
    if not a.yes:
        gb = sum(m["gb"] for m in todo)
        ok = ask(f"Update {len(todo)} model(s), {gb:.1f} GB of downloads, one at a time? Each is deleted first, so "
                 "a failed download leaves it missing until you rerun. [y/N]: ")
        if ok not in ("y", "yes"):
            print("Nothing was changed.")
            return []
    failed = update(t, todo, a.timeout)
    print(f"\nUpdated {len(todo) - len(failed)} of {len(todo)}." + (f" Not done: {', '.join(failed)}" if failed else ""))
    return failed


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("models", nargs="*", help="model ids, as in docs/MODELS.md")
    ap.add_argument("--updates", action="store_true", help="list installed models with an update waiting, then pick")
    ap.add_argument("--update", action="store_true", help="update the models named (delete, then download again)")
    ap.add_argument("--all", action="store_true", help="with --updates: update every listed model")
    ap.add_argument("-y", "--yes", action="store_true", help="don't ask before updating")
    ap.add_argument("--timeout", type=int, default=7200, help="seconds to wait per model (default 2 hours)")
    a = ap.parse_args()
    if not (a.models or a.updates):
        ap.error("name the models to download, or use --updates")
    t = at.Tiiny(*at.device())
    if t.call("GET", "/api/v1/models/running", timeout=15)[0] == 502:
        raise SystemExit("The Tiiny looks locked after a restart: run `tiiny login` or open the TiinyOS app, then rerun.")
    store = t.ok("GET", "/api/v1/models/online_models")
    store = {m.get("model_id"): m for m in (store if isinstance(store, list) else store.get("data", store))}
    if a.updates or a.update:
        sys.exit(1 if run_updates(a, t, store) else 0)
    failed = []
    for mid in a.models:
        if mid not in store:
            print(f"{mid}: not in the Model Store, skipped", flush=True)
            failed.append(mid)
            continue
        if status(t, mid)[0] == "downloaded":
            print(f"{mid}: already downloaded", flush=True)
            continue
        if not download(t, mid, size_gb(store[mid]), a.timeout):
            failed.append(mid)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
