# Marketing Empire — the honest version

A **free** marketing content system for Ting Lott / ARTISY and his affiliates.
CLI-first, stdlib-only core, no server, no paid keys, no subscriptions, no card
anywhere, ever. Bench build, Nov 8, 2026. **Bench only: nothing here deploys,
publishes, posts, or sends anything anywhere.**

## What it does

| Command | What it builds | Key needed? |
|---|---|---|
| `trend` | Trending topics (Google Trends RSS, Reddit Atom, Pinterest Trends, TikTok Creative Center), ranked + saved to the DB | **No** |
| `video` | One complete Shorts package: template script → Kokoro `af_heart` voiceover → 1080×1920 MP4 with Ken Burns + burned-in caption cards + end card | **No** |
| `campaign` | Per-platform posts (Facebook, Instagram, TikTok, Pinterest, + Reddit/X/LinkedIn) with caps, hashtag caps, best times, `#ad`, full link | **No** |
| `empire` | Content-empire plan: strategy + 4-week content plan | **No** |
| `dashboard` | Static `dashboard.html` from the SQLite DB — open it in a browser | **No** |
| `upload` | OPTIONAL YouTube upload — checks for YOUR OWN OAuth file; without it, prints setup steps and does nothing | Your own OAuth only |

## How to run

```bash
cd ~/workspace/marketing-empire-build

# 1. Trends (keyless)
python3 empire.py trend -n 12

# 2. One video package (Naturally Radiant Day 1 Starter — free product)
python3 empire.py video --product naturally-radiant-day1 --topic "Day 1 organic skincare routine"

# 3. Multi-platform campaign
python3 empire.py campaign --product naturally-radiant-day1 \
  --angle "Day 1 of your natural skincare routine starts with one simple scrub." \
  --platforms facebook,instagram,tiktok,pinterest

# 4. Content-empire plan
python3 empire.py empire --story "A nurse helping people find gentle, simple routines." \
  --niche "natural skincare" --audience "busy adults starting skincare"

# 5. Dashboard
python3 empire.py dashboard   # then open dashboard.html in a browser

# 6. Upload (optional — needs your own OAuth; see below)
python3 empire.py upload --video vid_<id>
```

Outputs land in `runs/<id>/` (script, voiceover WAV, MP4, thumbnail, meta/campaign JSON)
and in `empire.db` (SQLite: `video_packages`, `content_empires`,
`organic_campaigns`, plus an added `trends` table).

### Requirements

- Python 3.12, `ffmpeg`, `PIL` (all present on this bench).
- `trend-pulse` (MIT) for `trend`: `pip install --break-system-packages trend-pulse`.
  If that is unavailable, `trend` falls back to direct Google Trends RSS + Reddit
  Atom fetches with the standard library.
- Kokoro voiceover runs through the bench venv `~/workspace/venvs/kokoro/bin/python`
  (Kokoro-82M model already cached there) via `tts_helper.py`. If Kokoro is not
  available, `video` fails with a plain message instead of faking audio.

## How affiliates use it

1. **Core needs nothing from you.** Trend, video, campaign, empire, dashboard
   all run with zero keys.
2. **Optional script polish:** set YOUR OWN free Groq key and pass `--llm groq`:
   get a key at console.groq.com (free tier, no card), then
   `GROQ_API_KEY=gsk_... python3 empire.py video --product <id> --topic "..." --llm groq`.
   Without the key, the template script is used and the tool says so.
3. **Optional stock footage (PurffleShorts upgrade):** see
   `docs/purffleshorts.md`. Needs YOUR OWN free Pexels and/or Pixabay API keys;
   without them it falls back to gradients/local media. The core video command
   does NOT depend on it.
4. **Never use Ting's keys.** If a step asks for a key, it is always your own free one.
5. **Before you post anything:** read it once. The tool enforces the house rules
   below in code, but you are the last check.

## Content rules (enforced in code)

- Every video names `shop.artistrystore.com` and at least one product; spoken
  closes point to Gumroad/Whop.
- Every affiliate post carries `#ad` disclosure and the FULL product link
  (never shortened).
- No income promises. No invented numbers — performance predictions are stored
  as `{}` until real analytics exist. No medical claims. Person-first language
  in any mental-health copy.
- Prices and facts come only from `products.json`, where every product records
  its source file. Nothing is invented.

## Platform rules (borrowed, with corrections)

- Character + hashtag caps from **social-campaigns** (MIT, vendored in
  `vendor/social-campaigns/`): IG 2200, LinkedIn 3000, X 280, Facebook 63206,
  TikTok 4000, Pinterest 500, Reddit 40000; hashtags IG/TikTok 3–5, LinkedIn 3–5,
  X 1–3, Facebook 1–2.
- Optimal posting times + content styles from the paste's PLATFORM_CONFIGS,
  **corrected**: TikTok's real cap is 4000 (the paste's 150 is a short-caption
  target, not the cap); LinkedIn's real cap is 3000, not the paste's 1300.
- social-campaigns has NO disclosure language — the house `#ad` rule fills that gap.

## What this does NOT do

- No YouTube upload without YOUR OWN OAuth credentials (`client_secrets.json`).
  The `upload` command prints setup steps and stops if they are missing.
- No invented performance predictions, view counts, or income claims — ever.
- No paid-key paths: the paste's NVIDIA NIM integration was removed
  (`nim_generation_data` → `generation_meta`); there is no paid LLM in this build.
- No posting, scheduling, or sending — it generates content; a human posts it.
- No DALL-E thumbnails, no MoviePy placeholders, no fake audio (the paste's
  ContentForge snippet faked narration with a 100-byte blob — this build uses
  real Kokoro audio or fails honestly).
- Reddit was blocked (403) from this bench on one earlier check and worked on
  the next run; source failures are reported per source, never papered over.

## Products (`products.json`)

Only real products with verified prices. One correction: the build brief said
Sleep Sanctuary was $39.99, but Ting's own verified catalog prices it **$29.99**
— $29.99 is used. Luna $149/mo US / $59/mo overseas (LUNA-FACT-SHEET.md).
Sacred Cycles $97 (JVZoo 458553, Nov 3 launch). Naturally Radiant Day 1 Starter
FREE (live Gumroad page verified Nov 8, 2026).

## Verified run (Nov 8, 2026 — this bench, real outputs)

- **Trend:** `python3 empire.py trend -n 12` → 12 topics saved; google_trends OK,
  reddit OK, pinterest OK, tiktok_trending returned no items (reported, not faked).
  Run `trend_175ec467eb72`. (First attempt failed on the sandbox proxy bug
  `Invalid port: ':1]'`; fixed by forcing `NO_PROXY=localhost,127.0.0.1` in
  `empire.py`, the same fix as the Kokoro lesson.)
- **Video:** `python3 empire.py video --product naturally-radiant-day1 --topic "Day 1 organic skincare routine"`
  → package `vid_937feab5bd04`, 33.9 s, 1080×1920, h264 + AAC, 5.8 MB.
  Files: `runs/vid_937feab5bd04/` (script.txt, voiceover.wav, video.mp4, thumbnail.png, meta.json).
  Play-check: ffprobe 33.9 s; blackdetect — no black frames ≥0.5 s;
  volumedetect mean −26.0 dB, max −6.3 dB; faster-whisper (base) transcript
  matches the script word for word, including the spoken close naming Gumroad
  and shop.artistrystore.com.
- **Campaign:** `camp_bfb3981f4b46` — 4 posts (Facebook 586, Instagram 627,
  TikTok 381, Pinterest 380 chars — all inside caps). Verified in the JSON:
  every post carries `#ad`, the full Gumroad link, `shop.artistrystore.com`,
  and the product name. (First campaign run's Pinterest post lacked the shop
  mention — caught in verification, fixed in code, campaign re-run.)
- **Empire:** `empire_8171506784c9` — 4-week plan, 3 items/week.
- **Dashboard:** `dashboard.html` — counts 1 video, 2 campaigns, 1 empire, 12 trends.
- **Upload:** `upload --video vid_937feab5bd04` → prints setup steps, exits 0,
  nothing uploaded (no credentials on the bench).
- **DB check:** `performance_prediction` stored as `{}` and `campaign_metrics`
  as `{}` — verified by direct SQLite read.

## Sources and licences

- **trend-pulse** — https://github.com/claude-world/trend-pulse — MIT.
  License quote (verified by reading the LICENSE file, Nov 8, 2026):
  "MIT License / Copyright (c) 2026 Claude World / Permission is hereby
  granted, free of charge, to any person obtaining a copy of this software…"
  Full copy: `vendor/trend-pulse-LICENSE.txt`. Installed via pip (2.1.0).
- **social-campaigns** — https://github.com/mrsahilbeniwal/social-campaigns — MIT.
  "MIT License / Copyright (c) 2026 Sahil Beniwal / Permission is hereby
  granted, free of charge, to any person obtaining a copy…"
  Vendored references: `vendor/social-campaigns/` (platform-specs.md,
  prompt-templates.md, LICENSE).
- **PurffleShorts** (optional upgrade engine) —
  https://github.com/Chamanrajragu/purffle-shorts — MIT.
  "MIT License / Copyright (c) 2025 Purffle / Permission is hereby granted,
  free of charge, to any person obtaining a copy…" See `docs/purffleshorts.md`.
- **darkzOGx/youtube-automation-agent** — reference architecture only
  (agent chain + approval gate). Not adopted wholesale.
- **NOT used:** the paste-named PrintN repo (404, does not exist),
  ChaituRajSagar/gemini-youtube-automation (no LICENSE despite the README
  claiming MIT), cporter202/automate-faceless-content (no code, SaaS funnel),
  ai-content-factory (AGPL despite README claiming MIT), ShortGPT (stale,
  key-gated). Full verification log: `RESEARCH.md`.

## What still needs Ting

- **Nothing for the core.** Trend, video, campaign, empire, and dashboard all
  run with no key and no action from Ting.
- Optional, only if he wants them: his own free Groq key for script polish
  (each affiliate uses their own — Ting's key is never used); his own YouTube
  OAuth if he ever wants the `upload` command live; a decision on whether
  affiliates should use PurffleShorts stock footage (needs their own free
  Pexels/Pixabay keys).
