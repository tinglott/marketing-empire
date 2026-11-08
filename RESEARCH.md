# Marketing Empire Build — Research log (Nov 8, 2026)

## Paste-named repos — verified from source (agent f0eaf685, Nov 8)

### 1. darkzOGx/youtube-automation-agent — USABLE (with caveats)
- URL: https://github.com/darkzOGx/youtube-automation-agent
- License: MIT — verified in file. Opening line: "MIT License" / "Copyright (c) 2025 YouTube Automation Agent Contributors" — "Permission is hereby granted, free of charge, to any person obtaining a copy of this software…"
- Completeness: substantial and real. Files read: index.js (89 KB, 1,885 lines, node --check OK), agents/script-writer-agent.js (783 lines), schedules/daily-automation.js (678 lines), package.json (v2.11.0), .env.example, README.md, docs/providers.md. 7 agent modules, database/db.js (110 KB), dashboard/ (109 KB app.js), test.js (193 KB), CI running npm ci + lint + npm test. Zero TODO/FIXME/"not implemented" in core files checked. Honest guard: content is NOT scheduled when only placeholder assets were produced.
- What it does: research → script → narration/visuals → real MP4 (local slideshow) → SEO → schedule/upload → learning loop, 7 agents + dashboard at localhost:3456. Publishing is APPROVAL-GATED, not fully autonomous (videos wait in a Pipeline for fact/media-rights review). Scheduler: generation daily 06:00, publishing queue every 15 min, analytics 09:00.
- Free-run: core $0, no card. Needs Node 18.17+ and one text-provider key — Gemini free tier (AI Studio, no card) covers text + narration; local slideshow video is the free default; YouTube Data API v3 OAuth is free. Caveats: Gemini image model needs billing (without it, slides fall back to gradients/built-in thumbnails); ElevenLabs, OpenAI, Replicate/Seedance, MiniMax, Kling, Wan are paid/optional; YouTube OAuth in Testing mode expires after 7 days. No Pixabay/Freesound anywhere in the code.
- Use in this build: reference architecture (agent chain + approval gate + scheduler shape) and possibly its local-slideshow video approach. NOT adopted wholesale — house already has Kokoro TTS + ffmpeg slideshow; Node dependency is extra weight for affiliates.

### 2. PrintN/YouTube-Automation-Bot — NOT-FOUND
- GET api.github.com/repos/PrintN/YouTube-Automation-Bot → 404. User PrintN itself is also 404. GitHub code search for it returns 0 results. Paste's claim (Pixabay/Freesound + GitHub Actions scheduling) cannot be confirmed — treat as invented or pointing at a deleted/renamed/private repo. Do not cite.

### 3. ChaituRajSagar/gemini-youtube-automation — PARTIAL (do NOT use as MIT)
- URL (renamed): https://github.com/ChaitanyaEswarRajeshJakki/gemini-youtube-automation (old owner URL 301-redirects). 377 stars.
- License: NONE — GitHub API reports license: null; LICENSE and LICENSE.md both 404. Yet the README displays a green "license-MIT" badge and says "MIT License. See [LICENSE](LICENSE) for details" pointing at a nonexistent file. All-rights-reserved by default — reuse/modification is NOT actually licensed.
- Completeness: complete for its narrow job (main.py, src/generator.py, src/uploader.py, requirements.txt, GitHub Actions cron 0 7 * * *, tests/test_uploader.py — all py_compile clean, zero TODO/FIXME). Pipeline: Gemini 20-lesson curriculum → 1 lesson/run → Gemini script (7–8 slides + Short + hashtags) → gTTS narration → Pexels background image (or solid colour) → MoviePy/PIL slide video + vertical Short → YouTube upload.
- Limits: single hard-coded series ("AI for Developers", YOUR_NAME = "Chaitanya"), uploads public by default. Pinned old deps (moviepy==1.0.3, Pillow==9.5.0), needs ffmpeg + ImageMagick.
- Free-run: $0 core (Gemini free tier, gTTS free with retry/throttling, Pexels free key optional with solid-colour fallback, YouTube OAuth free).
- Use in this build: DO NOT copy code (no license). The PATTERN is instructive only: gTTS as a free narration fallback and Pexels free-key images with solid-colour fallback.

### 4. cporter202/automate-faceless-content — REJECT
- URL: https://github.com/cporter202/automate-faceless-content — 3,240 stars.
- License: NONE. No LICENSE file; README §License is only "provided as-is for educational purposes. ViralWave Studio is a third-party service with its own terms and conditions." — a disclaimer, not a license.
- Completeness: NO CODE AT ALL. Full tree: 130 Markdown files + 2 PNGs, zero .py/.js/.json files. It is a course + marketing funnel for ViralWave Studio (viralwavestudio.com), a third-party SaaS, promising "monetized in 2–3 weeks" and "$1,000+/month in passive income", pushing a free trial + promo code WELCOME15 and a $10/mo "AI Playbook". The idea→scheduled-post flow exists only inside that paid product.
- Use in this build: NONE. Do not cite as a tool or trend.

## Still pending (Nov 8, ~10:35 AM)
- Faceless-video MIT shortlist (agent bf5168bb) — running.
- Campaign/post-generation + trending MIT shortlist (agent d2a14eca) — running.

## Faceless video generation — verified MIT shortlist (agent bf5168bb, Nov 8)

Method: GitHub/web search, then direct verification via raw.githubusercontent.com (LICENSE) + GitHub API file tree; core code files read. Not run. 2 of 7 candidates passed all three checks (MIT + complete + free-run).

### 1. PurffleShorts — RECOMMENDED FIRST
- URL: https://github.com/Chamanrajragu/purffle-shorts
- License: MIT verified. "MIT License / Copyright (c) 2025 Purffle / Permission is hereby granted, free of charge, to any person obtaining a copy" (raw.githubusercontent.com/.../main/LICENSE; GitHub API agrees).
- What it does: Topic/URL/document/Reddit → LLM script + rubric "Script Doctor" review → voiceover → per-scene Pexels/Pixabay stock footage (or local media/, Ken Burns on photos) → word-level burned-in captions → ffmpeg render → optional YouTube/TikTok/Instagram publish. Clips podcasts into Shorts. Accepts a supplied script file (--script), so house scripts bypass the LLM entirely.
- Completeness: PASS. 112 files. Read: purffle_shorts/pipeline.py (750 lines, 0 TODO), tts.py (507), media.py (426), render.py (473), timing.py, llm.py (350), cli.py (592). pipeline.py Studio.make() is a real orchestrator (topic → script → review → voice → footage → captions → render → check → upload); _speak() tries the chosen engine then falls back to free EdgeTTS. timing.py has real word-timing (estimate_timings, anchored_timings, caption_chunks, srt); render.py has real compose()/render_video() plus pick_cover()/extract_frame() for thumbnails. No stubs on core path.
- Free-run: PASS (one free-key caveat). README: "purffle-shorts demo renders a sample Short with no keys" (built-in script, free neural voice, generated backgrounds). Default TTS is EdgeTTS — "320+ free Microsoft neural voices in 75 languages, with word-level timestamps. No key needed" — and tts.py has a native _kokoro() engine, so house Kokoro/af_heart plugs in. LLM can be local Ollama/LM Studio (no key) or a free-tier key (Groq/Gemini/OpenRouter). Stock footage needs a FREE Pexels and/or Pixabay API key; without one, scenes fall back to gradients/local media. Paid engines (OpenAI TTS, ElevenLabs) are optional and fall back to EdgeTTS on failure.
- Gap it fills: stock-clip fetching/scored matching, word-level caption timing, thumbnail/cover picking, script grading, multi-language publishing. Lightest, most house-shaped.

### 2. MoneyPrinterTurbo — RECOMMENDED SECOND
- URL: https://github.com/harry0703/MoneyPrinterTurbo
- License: MIT verified. "MIT License / Copyright (c) 2024 Harry / Permission is hereby granted, free of charge, to any person obtaining a copy" (raw.githubusercontent.com/.../main/LICENSE).
- What it does: Topic/keyword (or supplied custom script) → LLM script → Pexels/Pixabay/Coverr stock footage or local media → TTS voiceover → styled subtitles + background music → MoviePy/ffmpeg HD render (1080x1920 / 1920x1080 / 1080x1080), with a WebUI.
- Completeness: PASS. 474 files, largest/most mature. Read: app/services/voice.py (3,950 lines, 0 TODO), llm.py (1,440), video.py (2,188), material.py (3,359), subtitle.py (350), config/config.py (729). Real functions throughout (video.py generate_video() line 1610, combine_videos(), render_image_zoom_video(), codec-fallback rendering). No stubs/TODOs on core path.
- Free-run: PASS (heavier setup). LLM supports Ollama (llm.py:360-363: api_key = "ollama", local base URL) plus free-tier providers. TTS: "Use Edge TTS (free, no API key required), Azure Speech, … Kokoro, …" — voice.py:293 sets KOKORO_DEFAULT_VOICE = "af_heart" (the house voice is its Kokoro default). Stock footage is Pexels/Pixabay (free API keys). Paid providers (OpenAI, ElevenLabs, MiniMax, etc.) are optional extras.
- Gap it fills: same stock-footage + caption + assembly gaps, plus a WebUI (easier for the 9 affiliates than a CLI) and native Kokoro/af_heart support. Caveats: much bigger and sponsor-heavy (many paid-provider integrations to ignore); #1 is the cleaner first try.

### FAILED / NOT RECOMMENDED (faceless video)
- FreeFaceless (nils44344/FreeFaceless): UNVERIFIABLE — repo 404 on GitHub API for main and master; LICENSE 404. May have been deleted/privatised. Do not use.
- ShortGPT (RayVentura/ShortGPT, stable branch): MIT verified, code complete (EdgeTTS real), but FAILS free-run/stale: config only knows OPENAI_API_KEY, GEMINI_API_KEY, ELEVENLABS_API_KEY, PEXELS_API_KEY — no Ollama/local LLM — and installation-notes.md requires a .env with all four keys. Last push Feb 10, 2025.
- zero-dollar-studio (TheNoumanDev/zero-dollar-studio): MIT verified, code real (Remotion + Chatterbox + Whisper), but FAILS as a standalone free-run tool: it is a set of Claude Code/Codex/Gemini-CLI skills, not a script→video program; README requires macOS on Apple Silicon, ~8 GB local models, and an AI coding agent on its normal (paid) plan. Remotion separately licensed (free only for individuals/companies ≤3 people).
- Beatsheet (Richadaf/faceless-youtube-video): MIT verified, but INCOMPLETE vs the brief: audio → slideshow only. No script writing, no TTS — supply your own voiceover, paste word-timings into an LLM prompt by hand, generate every frame manually. Windows/PowerShell-only. Only duplicates the Ken Burns slideshow the house already has.
- MoneyPrinterV2 (FujiwaraChoki/MoneyPrinterV2) and OpenMontage: AGPL-3.0, not MIT — excluded. GoMotion skill (gomotionai/gomotion-skill): MIT code but requires a paid Go Motion API key — excluded on free-run.

## Still pending (Nov 8, ~10:36 AM)
- Campaign/post-generation + trending MIT shortlist (agent d2a14eca) — running.

## Campaign/post generation + trending — verified MIT shortlist (agent d2a14eca, Nov 8)

Blanket finding: NO candidate covers FTC/affiliate disclosure rules — house rules must be added on top of any pick.

### (a) Multi-platform campaign / post generation

#### 1. social-campaigns — ADOPT FOR GENERATION
- URL: https://github.com/mrsahilbeniwal/social-campaigns
- License: MIT — "MIT License / Copyright (c) 2026 Sahil Beniwal / Permission is hereby granted, free of charge, to any person obtaining a copy" (LICENSE file, fetched raw).
- What it does: an AI-assistant skill (prompt pack, not an app) running a 6-phase campaign workflow — brand scan, competitor research, strategy, then per-platform post generation — with approval gates between phases. Modes: full campaign, launch, refresh, single post, competitor spy, repurpose.
- Completeness: PASS. Files read: SKILL.md (539 lines), references/platform-specs.md (166 lines — complete per-platform tables: IG 2,200 chars / 5–15 hashtags, LinkedIn 3,000 / 3–5, X 280 / 1–3, Facebook 63,206 / 1–2, TikTok 4,000 / 3–5, Pinterest pin dims + SEO notes, plus image sizes for all six), references/prompt-templates.md (300 lines, 8 template types), plus caption-frameworks.md, campaign-types.md, content-pillars.md, creative-brief-guide.md, install.sh/install.ps1. Grep for TODO/FIXME/placeholder/stub: zero hits. No disclosure/FTC/affiliate language anywhere — real gap, filled by house rules.
- Free-run: PASS. Pure Markdown prompts; no code, no API keys, no service. Runs inside an AI coding assistant (house already runs Muse).
- Gap it fills: the only candidate that is actually generation templates with per-platform limits and hashtag caps for all six platforms (FB, IG, TikTok, Pinterest, X, LinkedIn). Reddit is not covered.

#### 2. LightPost — qualified #3 (scheduler only, NOT a generator)
- URL: https://github.com/brainstormity/LightPost
- License: MIT — "MIT License / Copyright (c) 2026 LightPost contributors / Permission is hereby granted, free of charge, to any person obtaining a copy" (LICENSE file, fetched raw).
- What it does: self-hosted scheduler/publisher — one Python process + SQLite, web dashboard, write once and publish/schedule to multiple accounts. Per-platform character limits enforced in the composer (X 280, Instagram 2,200 in providers.py).
- Completeness: PASS with a scope cut. Files read: lightpost/providers.py (72 KB — real publish_facebook, publish_linkedin, publish_x, publish_meta, publish_telegram), app.py (30 KB), jobs.py, store.py, large test suite. BUT README's own platform table lists TikTok, Pinterest, and Google Business Profile as "Under development" — two core channels not shippable. It also generates nothing; it publishes copy you write.
- Free-run: PASS. .env.example has no API keys — only host/port, admin password, encryption key, Meta Graph version. Platform access via the user's own free developer/OAuth credentials; no paid service.
- Gap: self-hosted multi-account scheduling incl. YouTube, Bluesky, Telegram, Discord. Partly duplicates the toolkit's schedulers; misses TikTok/Pinterest. Watch, don't adopt for those channels.

### (b) Trending topic discovery

#### 1. trend-pulse — ADOPT FOR TRENDS (first)
- URL: https://github.com/claude-world/trend-pulse
- License: MIT — "MIT License / Copyright (c) 2026 Claude World / Permission is hereby granted, free of charge, to any person obtaining a copy" (LICENSE file, fetched raw).
- What it does: trending-topics aggregator — 20 built-in sources + plugin sources, as CLI, Python library, MCP server, and web dashboard. Sources include Google Trends (RSS), Reddit (Atom), Hacker News, GitHub Trending, plus plugin sources for Pinterest Trends, TikTok (Creative Center), YouTube Trending, X, Threads, LinkedIn.
- Completeness: PASS. Files read in full: sources/google_trends.py (79 lines — real RSS parse, traffic-to-score normalization), sources/reddit.py (84 lines — real Atom parse, rank-based scoring, docstring noting Reddit's .json endpoint now 403s unauthenticated so it uses RSS), plugins/sources/pinterest.py (104 lines — real call to trends.pinterest.com/top_trends_filtered/ with US fallback on 400), plugins/sources/tiktok_trending.py (169 lines, Creative Center public endpoint), aggregator.py (196 lines). Grep for TODO/FIXME/NotImplemented/stub: zero hits. Tests, CI, Dockerfile, examples.
- Free-run: PASS. .env.example states "Every value is optional; sources and features that need a missing credential are skipped gracefully." All core sources requires_auth = False. Optional paid keys (Anthropic L2 judge, YouTube Data API, X bearer) only unlock extras. Rate limits: Google Trends RSS unlimited, Reddit ~1 req/min anonymous.
- Gap it fills: the single biggest missing piece — one free command returning trending topics from Google, Reddit, Pinterest, TikTok with no keys. The Pinterest Trends plugin directly serves the Pinterest playbook.

#### 2. trendspyg — ADOPT FOR TRENDS (second, Google Trends depth)
- URL: https://github.com/flack0x/trendspyg (PyPI: pip install trendspyg)
- License: MIT — "MIT License / Copyright (c) 2025 AM / Permission is hereby granted, free of charge, to any person obtaining a copy" (LICENSE file, fetched raw; PyPI also lists MIT).
- What it does: Python library + CLI + MCP server for Google Trends — real-time trending topics (RSS path), ~480 current trends (CSV path), keyword interest-over-time / related queries / by-region (Explore path, pytrends-compatible TrendReq). Successor to pytrends, archived April 17, 2025.
- Completeness: PASS. Files checked: trendspyg/rss_downloader.py (41 KB), downloader.py (28 KB), cli.py (29 KB), compat/request.py (27 KB), explore/_engine.py (30 KB), __init__.py (exports incl. __license__ = "MIT"), large mocked test suite, live-contract CI, CHANGELOG (57 KB), written stability contract. No stubs in the RSS module.
- Free-run: PASS with a caveat. RSS and CSV paths run with no key (documented "fast path" / "full path"). Explore path has a _cookies.py module — keyword-over-time may need a Google session cookie in some environments; trend discovery does not.
- Gap: depth on Google Trends — keyword comparison, interest over time, 125 countries / 20 categories — where trend-pulse only gives the headline RSS list. Complements #1. Google-Trends-only.

#### 3. gtrends-cli — ADOPT FOR TRENDS (third, creator-simple CLI)
- URL: https://github.com/Nao-30/google-trends-cli (PyPI: gtrends-cli)
- License: MIT — "MIT License / Copyright (c) 2025 Nao-30 / Permission is hereby granted, free of charge, to any person obtaining a copy" (LICENSE file, fetched raw; PyPI also lists MIT).
- What it does: Google Trends CLI + FastAPI HTTP service explicitly built for content creators: trending searches, related queries, suggestions, geo breakdown, growth, "opportunities", content-creator category presets (books, arts, fiction, culture, news).
- Completeness: PASS (minor hygiene sloppiness). Files checked: src/gtrends_core/config.py (TrendsClient wrapping the trendspy library), services/trending_service.py (12.7 KB — throttling, IP-based region detection with fallback, DataFrame→model conversion), 6 more services, 9 CLI commands, 7 API routers, formatters, tests. Sloppy artifacts: a committed .env (22 bytes), a .bak file, a 1-byte add_exceptions.py — cosmetic, not core-path stubs.
- Free-run: PASS. No API key anywhere in the code path; talks to Google Trends through the trendspy library. Caveat: this repo was verified, not the trendspy dependency itself — if it breaks, the CLI breaks with it.
- Gap: most creator-shaped Google Trends tool — "opportunities" and category presets map closest to Ting's lanes (books/faith/arts). Simplest to hand to affiliates (gtrends trending → list).

### FAILED VERIFICATION (campaign/trending — do not adopt as-is)
- mon928/ai-content-factory — README claims MIT, but the actual LICENSE file fetched raw is GNU AGPL-3.0. License FAIL.
- Chukwuebuka-2003/buildpost — MIT confirmed, code complete, but free-run FAIL: AIService.__init__ raises ValueError unless an LLM API key is present — core cannot run with zero keys. Wrong shape too (input is git commits; only Twitter/LinkedIn/Dev.to).
- rushindrasinha/youtube-shorts-pipeline — MIT confirmed, topics engine real, but PARTIAL/fragile: Google Trends source depends on pytrends (archived April 2025); Reddit source hits unauthenticated .json endpoints (now 403); auto_pick needs Claude; main purpose is a video pipeline needing LLM keys.
- celeryhq/simplified-cli — MIT in metadata, but requires a SIMPLIFIED_API_KEY for a paid SaaS. Free-run FAIL.
- vanman2024/ayrshare-mcp — MIT, 75+ tools across 13 platforms, but every call goes through the Ayrshare API account (paid). Free-run FAIL.
- mvanhorn/last30days-skill — MIT confirmed, verified complete, NOT shortlisted (not failed): 202 KB Python engine with keyless floor (Reddit, Hacker News, Polymarket keyless; YouTube via yt-dlp, no key) and velocity-ranked discovery. Heavy agent skill (Python 3.12+, setup wizard, X/YouTube/TikTok need keys or browser cookies) — overkill next to trend-pulse/gtrends-cli. Second look only if deep multi-source research briefs are wanted later.
- affectionatec/niche-radar-alpha — spec document only (v0.2.0-alpha); no implementation. Not usable.
