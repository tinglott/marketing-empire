#!/usr/bin/env python3
"""Kokoro TTS helper — runs under the kokoro venv (~/workspace/venvs/kokoro/bin/python),
where the kokoro package + cached Kokoro-82M model live. Called by empire.py.
Usage: tts_helper.py --text "..." --out voiceover.wav [--voice af_heart] [--speed 1.0]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.expanduser("~/workspace/your_files/voiceforge-studio"))

import kokoro_tts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--voice", default="af_heart")
    p.add_argument("--speed", type=float, default=1.0)
    args = p.parse_args()
    if not kokoro_tts.is_available():
        print("Kokoro package not installed in this venv.", file=sys.stderr)
        return 1
    wav = kokoro_tts.synthesize(args.text, voice=args.voice, speed=args.speed)
    with open(args.out, "wb") as f:
        f.write(wav)
    print(f"Wrote {args.out} ({len(wav)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
