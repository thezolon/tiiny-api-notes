"""List the voices of each text-to-speech model on your Tiiny, and check one works through the API.

    python tools/tts_voices.py            # every TTS model you've downloaded
    python tools/tts_voices.py --model microsoft/VibeVoice-Realtime-0.5B

Needs TIINY_URL / TIINY_KEY (as for api_test.py) and a Wi-Fi/LAN address: the voice list comes from each model's own
port, which the USB link blocks. For every TTS model: load it, read its speakers, send `/v1/audio/speech` once with
voice "alloy" (what OpenAI clients send by default) and once with the model's first speaker, then unload it.
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

import api_test as at


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", help="one model id instead of all downloaded TTS models")
    a = ap.parse_args()
    t = at.Tiiny(*at.device())
    have = t.ok("GET", "/api/v1/models/?including_downloading=false")
    have = have.get("data", have) if isinstance(have, dict) else have
    models = [a.model] if a.model else sorted(m["id"] for m in have if m.get("type") == "Text-to-Speech")
    if not models:
        sys.exit("No text-to-speech models downloaded.")
    host = urllib.parse.urlparse(t.url).hostname
    before = set(t.running())
    for mid in models:
        try:
            t.load(mid)
            port = t.running()[mid]["port"]
            try:
                cap = json.loads(urllib.request.urlopen(f"http://{host}:{port}/v1/capabilities", timeout=10).read())
            except OSError:
                sys.exit(f"Can't reach the model's own port {port}: use a Wi-Fi/LAN address for TIINY_URL, not USB.")
            speakers = cap.get("supported_speakers") or []
            body = {"model": mid, "input": "Hello from my Tiiny. This is a speech test.", "response_format": "wav",
                    "language": "en"}

            def say(**extra):  # some models fail the first request after a load: retry once
                code = t.call("POST", "/v1/audio/speech", {**body, **extra}, raw=True, timeout=300)[0]
                return code if code < 300 else t.call("POST", "/v1/audio/speech", {**body, **extra}, raw=True, timeout=300)[0]

            lines = [f"  voice 'alloy' (OpenAI default): HTTP {say(voice='alloy')}"]
            if cap.get("support_voice_design"):
                lines.append(f"  voice design, \"instruct\": \"A calm, warm female voice.\": "
                             f"HTTP {say(instruct='A calm, warm female voice.')}")
            elif cap.get("support_custom_voice") and speakers:
                pick = next((s for s in speakers if s.lower().startswith("en")), speakers[0])
                lines.append(f"  voice '{pick}': HTTP {say(voice=pick)}")
            else:
                lines.append("  no preset voices: clone only (send ref_audio + ref_text, see the audio-tts check)")
            if cap.get("support_voice_clone"):
                lines.append("  also: voice cloning (ref_audio + ref_text)")
            if speakers and cap.get("support_custom_voice") and not cap.get("support_voice_design"):
                lines.append(f"  speakers ({len(speakers)}): {', '.join(speakers)}")
            print(f"\n{mid}\n" + "\n".join(lines), flush=True)
        finally:
            if mid not in before:
                t.ok("POST", f"/api/v1/models/{urllib.parse.quote(mid, safe='')}/stop", {}, timeout=180)


if __name__ == "__main__":
    main()
