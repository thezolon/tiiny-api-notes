"""Download models to your Tiiny from a script, and know when they're done.

    python tools/download_models.py hexgrad/Kokoro-82M k2-fsa/OmniVoice
    python tools/download_models.py --cli C:/path/tiiny.exe vllm-sr/d3-edge

The Tiiny CLI (v0.0.5) starts downloads fine but never returns when run from a script, even after the download has
finished. This starts `tiiny download <id>` for each model in turn, watches the device's own download status
(GET /api/v1/models/?including_downloading=true) until it says `downloaded`, then stops the CLI. Shows progress and
the model's size; skips models already downloaded. The Tiiny downloads over its own Wi-Fi (it needs internet), so
mind your data on a phone hotspot. Needs TIINY_URL / TIINY_KEY and the CLI signed in.
"""
import argparse
import subprocess
import sys
import time
import urllib.parse

import api_test as at
from cli_compare import find_cli


def status(t, mid):
    rows = t.ok("GET", "/api/v1/models/?including_downloading=true")
    rows = rows.get("data", rows) if isinstance(rows, dict) else rows
    m = next((m for m in rows if m.get("id") == mid), None)
    return (m.get("status"), m.get("progress")) if m else (None, None)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("models", nargs="+", help="model ids, as in docs/MODELS.md")
    ap.add_argument("--cli")
    ap.add_argument("--timeout", type=int, default=7200, help="seconds to wait per model (default 2 hours)")
    a = ap.parse_args()
    url, key = at.device()
    t = at.Tiiny(url, key)
    exe = find_cli(a.cli)
    addr = urllib.parse.urlparse(url).hostname
    store = t.ok("GET", "/api/v1/models/online_models")
    store = {m.get("model_id"): m for m in (store if isinstance(store, list) else store.get("data", store))}
    failed = []
    for mid in a.models:
        if mid not in store:
            print(f"{mid}: not in the Model Store, skipped", flush=True)
            failed.append(mid)
            continue
        size = max((g.get("size") or 0 for g in store[mid].get("tags") or []), default=0) / 1e9
        if status(t, mid)[0] == "downloaded":
            print(f"{mid}: already downloaded", flush=True)
            continue
        print(f"{mid}: downloading {size:.1f} GB", flush=True)
        p = subprocess.Popen([exe, "--device-address", addr, "-y", "download", mid],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0, last, state = time.time(), None, (None, None)
        try:
            while time.time() - t0 < a.timeout:
                state = status(t, mid)
                if state != last and state[1] is not None:
                    print(f"  {time.time() - t0:5.0f} s  {state[0]} {state[1]:.0f}%", flush=True)
                    last = state
                if state[0] == "downloaded":
                    break
                if p.poll() is not None and p.returncode != 0 and state[0] is None:
                    break  # the CLI refused (e.g. no network) and nothing started
                time.sleep(10)
        finally:
            if p.poll() is None:
                p.kill()
        if state[0] == "downloaded":
            print(f"  done in {time.time() - t0:.0f} s", flush=True)
        else:
            print(f"  NOT finished (status {state[0]}, CLI exit {p.returncode}); check `tiiny downloads ls`", flush=True)
            failed.append(mid)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
