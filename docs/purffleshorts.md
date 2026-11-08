# PurffleShorts — optional upgrade engine (NOT a core dependency)

PurffleShorts (https://github.com/Chamanrajragu/purffle-shorts, MIT —
"MIT License / Copyright (c) 2025 Purffle / Permission is hereby granted, free
of charge, to any person obtaining a copy…", LICENSE re-read Nov 8, 2026)
is the documented OPTIONAL upgrade for the core `video` command. It adds what
the core does not do: per-scene stock-footage matching, word-level burned-in
captions, thumbnail/cover picking, and a script-grading "Script Doctor".

## Bench verification (Nov 8, 2026)

- Cloned to /tmp/ps (git clone --depth 1, main branch).
- `~/workspace/venvs/kokoro/bin/python -m purffle_shorts --help` → **exit 0**,
  full subcommand list (`run, make, clip, plan, ideas, stats, mcp, demo,
  upload, auth, doctor, providers, history, voices, studio`).
- `import purffle_shorts` → **OK**.
- NOT installed via pip: there is no `purffle-shorts` package on PyPI
  ("No matching distribution found"). Install from the cloned repo
  (`pip install -e .` in the clone) — not done here, because the core does
  not need it and no end-to-end PurffleShorts render was run on this bench.
- Native Kokoro engine exists in its `tts.py` (`_kokoro()`), so the house
  `af_heart` voice plugs in; default TTS is free EdgeTTS (no key).

## When to use it

Use PurffleShorts when a video wants real stock footage behind the voiceover
instead of the core's house-made navy/gold cards, or word-by-word captions
instead of the core's per-beat caption cards. Feed it a house script file
(`--script`) so the house script bypasses its LLM entirely.

## What it needs (all optional, all the affiliate's own)

- Stock footage: YOUR OWN free Pexels and/or Pixabay API keys. Without one,
  scenes fall back to gradients / local media — same as the core.
- Script writing: local Ollama/LM Studio (no key) or a free-tier key
  (Groq/Gemini/OpenRouter). House scripts bypass this entirely.
- Publishing (YouTube/TikTok/Instagram): the affiliate's own OAuth, same as
  the core's `upload` rule.

## What it does NOT change

The core `video` command never depends on PurffleShorts. If PurffleShorts is
absent, broken, or keyless, the core still builds a complete video package.
