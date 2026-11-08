# Marketing Empire — backend smoke test (bench, Nov 8, 2026)

Server: `~/workspace/marketing-empire-build/web/server/server.py`
(stdlib only — `http.server` + `sqlite3` + `threading`; Flask 3.1.3 is
installed on the bench but deliberately NOT used, for portability).
Started with `PORT=8000 python3 server.py`, bound to `127.0.0.1:8000`.
No deploy, no publish, no tunnel, no purchase. Server stopped after the
tests; restart with the same command.

## Results

| # | Endpoint | Result |
|---|---|---|
| 1 | `GET /api/health` | **200** `{"ok": true}` |
| 2 | `GET /api/products` | **200** — store `https://shop.artistrystore.com` + all 4 products (naturally-radiant-day1 FREE, luna $149/$59 mo, sleep-sanctuary $29.99, sacred-cycles $97) with verified links/prices from `products.json` |
| 3 | `GET /api/trends?n=12` | **200** — 12 topics, **fresh=true**, ~6.5 s. Per-source status reported honestly: `google_trends: ok`, `pinterest: ok`, `reddit: error: 429 Too Many Requests` (rate-limited at that moment, not faked), `tiktok_trending: no report`. 12 new rows saved to `empire.db` (trends total 12 → 24 over the session) |
| 4 | `POST /api/campaign` (naturally-radiant-day1, 4 platforms) | **200** — `camp_63a4423fc0eb`, 4 posts: Facebook 586, Instagram 627, TikTok 381, Pinterest 380 chars — all inside caps. Every post verified in the response: `#ad`, full Gumroad link `https://tlott12.gumroad.com/l/peowl`, `shop.artistrystore.com`, product name |
| 5 | `POST /api/empire` | **200** — `empire_7bdfe3cd4a18`, full 4-week plan (3 items/week, pillars, house rules) |
| 6 | `POST /api/campaign` unknown product | **400** `{"error": "unknown product 'nope'"}` |
| 7 | `POST /api/campaign` banned phrase ("guaranteed income") | **400** `BLOCKED: House rule violation in campaign angle: banned phrase 'guaranteed income'` — `check_copy()` enforced server-side |
| 8 | `GET /api/jobs/vid_nope` | **404** `unknown job` |
| 9 | `GET /api/download/vid_937feab5bd04/thumbnail` (pre-existing CLI video) | **200** — 48,342 bytes, PNG 1080×1920, matches the CLI output |
| 10 | `GET /api/download/.../../../etc/passwd` (`--path-as-is`) | **400** `bad download path` — traversal rejected; only `video/script/thumbnail/voiceover` are ever served, filename fixed by allowlist |
| 11 | `POST /api/video` naturally-radiant-day1 "Day 1 organic skincare routine" | **202** `{"job_id": "vid_a4f092428448"}` immediately; polled `GET /api/jobs/<id>` → `queued → working (20% voiceover → 70% ffmpeg) → ready` in **~2 min 16 s** (TTS ~100 s, ffmpeg ~30 s). Files in `runs/vid_a4f092428448/`: `video.mp4` 5.6 MB, `voiceover.wav` 1.6 MB, `thumbnail.png` 48 KB, `script.txt`, `meta.json`. ffprobe: **1080×1920, h264 + AAC, 33.9 s**. Script verified: names the product, close names Gumroad + "shop dot artistry store dot com". `meta.json`: `performance_prediction: {}`, `script_source: template script (no key needed)`, `tts: Kokoro af_heart`. DB: `jobs` row `ready`, `video_packages` row `ready` |
| 12 | `GET /api/download/vid_a4f092428448/video` | **200** — 5,838,945 bytes, byte-identical to the disk file (`cmp` match) |
| 13 | `GET /api/download/vid_a4f092428448/voiceover` | **200** — 1,627,244 bytes |
| 14 | `POST /api/video` sleep-sanctuary with a **fake** `groq_key` (`gsk_FAKEKEY_N0TREAL_98765`) | **202** → job `vid_c62826d8bdce` → **ready** in ~106 s (Groq polish failed on the fake key, template script used — the honest fallback). **Key-leak check: `grep -r FAKEKEY` over `empire.db`, all 5 job files, and the server log returned 0 matches everywhere** — the key was in-memory only and is gone |
| 15 | `GET /api/dashboard` (final) | **200** — counts `{videos: 2→3, campaigns: 3, empires: 2, trends: 24, jobs: 2}` (counts grew as the smoke tests themselves created rows; videos 3 after the fake-key job) |

## Notes / gaps found while testing

- `GET /api/trends` does a live fetch inline (~6.5 s this run; Reddit
  429'd). If all sources fail at once it falls back to saved rows with
  `fresh: false`. A slow source could make the call take up to ~60 s;
  acceptable for affiliates, flagged for the deploy step (a background
  refresh would be nicer, not required).
- Video render time on the bench: **~2–2.5 min per video**, single
  worker, jobs in order. Two affiliates submitting at once queue, they
  do not run in parallel — by design (Kokoro + ffmpeg are CPU-heavy).
- The `jobs` table lives in the CLI's `empire.db`; a host with
  ephemeral disk (Render free) loses jobs + `runs/` on restart. The API
  then answers `404 unknown job` honestly rather than inventing files.
  See `HOSTING.md` for the full hosting verdict.

## Parent-agent browser click-through + fix (Nov 8, ~11:20 AM)

Real-browser check (headless Chromium via CDP, stdlib-only client) found and fixed one bug the curl checks could not see: `index.html` references `style.css` and `app.js` relatively, but the server only served files under `/static/` — so in a real browser the page loaded unstyled with empty product dropdowns and dead buttons (`GET /app.js 404`, `GET /style.css 404`). Fix in `server.py` do_GET: root-level bare filenames that exist in STATIC_DIR are now served too (same traversal guard). Re-verified live: title correct, 4 sections, product dropdown populated with all 4 real products, "Server: connected ✓", zero console errors, trends button clicked → 12 real topics rendered with per-source status (TikTok "no report"). Screenshot: `web/preview-home.png`. Server stopped afterwards; port 8000 closed.
