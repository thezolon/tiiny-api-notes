"""Can the Tiiny download a model over the USB cable with its Wi-Fi off?

    python tools/usb_download_test.py                    # uses hexgrad/Kokoro-82M (small), unless it's already downloaded
    python tools/usb_download_test.py --model <id> --cli C:/path/tiiny.exe

Run it from a PC connected by USB cable, with TIINY_URL set to the USB address (e.g. http://172.20.31.109). Uses the
Tiiny CLI (signed in) for the Wi-Fi switch and the download. Steps: note the Wi-Fi state, turn Wi-Fi OFF, start the
download, watch it for a few minutes, then ALWAYS clean up: delete the test model and turn Wi-Fi back on (and wait for
it to reconnect). Your PC needs internet if the download is to have any chance.
"""
import argparse
import re
import subprocess
import sys
import time
import urllib.parse

import api_test as at
from cli_compare import find_cli


def cli(exe, addr, *args, timeout=120):
    """Run the CLI; a hung command (e.g. one waiting on a terminal) counts as 'timeout' instead of raising."""
    try:
        p = subprocess.run([exe, "--device-address", addr, *args], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        return p.returncode, (p.stdout + "\n" + p.stderr).strip()
    except subprocess.TimeoutExpired as e:
        return "timeout", ((e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""))


def wifi(exe, addr):
    rc, o = cli(exe, addr, "wifi", "status")
    on = re.search(r"Enabled:\s*(\w+)", o)
    ssid = re.search(r"ConnectedSSID:\s*(\S*)", o)
    return (on.group(1).lower() == "true") if on else None, (ssid.group(1) if ssid else ""), o


def downloaded(exe, addr, model):
    return model in cli(exe, addr, "ls", "-d")[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="hexgrad/Kokoro-82M")
    ap.add_argument("--cli")
    ap.add_argument("--watch", type=int, default=240, help="seconds to watch the download (default 240)")
    a = ap.parse_args()
    url, _ = at.device()
    addr = urllib.parse.urlparse(url).hostname
    exe = find_cli(a.cli)
    if downloaded(exe, addr, a.model):
        sys.exit(f"{a.model} is already downloaded; pick another small model with --model (see docs/MODELS.md).")
    was_on, ssid, raw = wifi(exe, addr)
    if was_on is None:
        sys.exit(f"Couldn't read the Wi-Fi state through {addr}: {raw[-200:]}")
    print(f"Wi-Fi before: {'on' if was_on else 'off'}{' (connected)' if ssid else ''}", flush=True)
    result = "unknown"
    try:
        if was_on:
            rc, o = cli(exe, addr, "-y", "wifi", "off")
            time.sleep(10)
            now_on, now_ssid, _ = wifi(exe, addr)
            print(f"Wi-Fi off: rc {rc}, now {'on' if now_on else 'off'}{' (still connected!)' if now_ssid else ''}", flush=True)
            if now_on or now_ssid:
                result = "couldn't turn Wi-Fi off"
                return
        t0 = time.time()
        rc, o = cli(exe, addr, "-y", "download", a.model, timeout=a.watch)
        print(f"download command: rc {rc} after {time.time() - t0:.0f} s: {o[-300:]}", flush=True)
        if rc not in (0, "timeout"):  # refused outright (e.g. "Tiiny needs a network connection")
            result = f"REFUSED with Wi-Fi off: {o.strip()[-160:]}"
            return
        while time.time() - t0 < a.watch and not downloaded(exe, addr, a.model):
            print("  tasks:", cli(exe, addr, "downloads", "ls")[1].replace("\n", " | ")[-200:], flush=True)
            time.sleep(15)
        result = "DOWNLOADED over USB with Wi-Fi off" if downloaded(exe, addr, a.model) else "NOT downloaded with Wi-Fi off"
    finally:
        if not downloaded(exe, addr, a.model):
            cli(exe, addr, "-y", "downloads", "cancel", a.model)
        if downloaded(exe, addr, a.model):
            print("cleanup: removing the test model:", cli(exe, addr, "-y", "rm", a.model)[0], flush=True)
        if was_on:
            print("cleanup: Wi-Fi back on:", cli(exe, addr, "-y", "wifi", "on")[0], flush=True)
            for _ in range(12):
                time.sleep(10)
                on, ssid, _ = wifi(exe, addr)
                if on and ssid:
                    print("Wi-Fi reconnected.", flush=True)
                    break
            else:
                print("Wi-Fi is on but not reconnected yet; check `tiiny wifi status`.", flush=True)
        print("RESULT:", result, flush=True)


if __name__ == "__main__":
    main()
