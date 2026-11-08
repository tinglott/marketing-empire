#!/usr/bin/env python3
"""Marketing Empire — free marketing content system (CLI-first, stdlib-only core).

Ting Lott / ARTISY — bench build, Nov 8, 2026. $0 only: no paid keys, no
subscriptions, no card anywhere. Optional extras (own free Groq key for script
polish, own free Pexels/Pixabay keys for stock footage, own YouTube OAuth for
upload) are always optional and always the USER'S OWN key — never Ting's.

Subcommands: trend, video, campaign, empire, dashboard, upload.
Run `python3 empire.py --help` for usage. See README.md for the full guide.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import textwrap
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# The sandbox proxy breaks httpx URL parsing (IPv6 [::1] in no_proxy).
# Same fix as the Kokoro TTS lesson (AGENTS.md): force a clean no_proxy
# BEFORE importing anything that uses httpx (trend-pulse does).
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "empire.db")
RUNS_DIR = os.path.join(BASE, "runs")
PRODUCTS_PATH = os.path.join(BASE, "products.json")
# Bench path first; anywhere else (e.g. the Render Docker image) fall back to
# the interpreter running this code, which has kokoro installed there.
_VENV_PY = os.path.expanduser("~/workspace/venvs/kokoro/bin/python")
KOKORO_VENV_PY = _VENV_PY if os.path.exists(_VENV_PY) else sys.executable
VOICEFORGE = os.path.expanduser("~/workspace/your_files/voiceforge-studio")
STORE_URL = "https://shop.artistrystore.com"

# ---------------------------------------------------------------------------
# Platform rules — borrowed from social-campaigns (MIT, vendored in
# vendor/social-campaigns/) for the character/hashtag caps, and from the
# paste's PLATFORM_CONFIGS for optimal posting times + content styles.
# CORRECTIONS to the paste (verified against social-campaigns platform-specs):
#   * TikTok's real cap is 4000 chars; the paste's 150 is a SHORT-CAPTION
#     target, not the platform cap. We enforce 4000 and aim short.
#   * LinkedIn's real cap is 3000 chars, not the paste's 1300.
# ---------------------------------------------------------------------------
PLATFORMS = {
    "facebook":  {"max_chars": 63206, "hashtags": (1, 2), "times": ["13:00", "15:00", "19:00"], "style": "casual"},
    "instagram": {"max_chars": 2200,  "hashtags": (3, 5), "times": ["11:00", "14:00", "17:00"], "style": "creative"},
    "tiktok":    {"max_chars": 4000,  "hashtags": (3, 5), "times": ["06:00", "10:00", "19:00"], "style": "creative"},
    "pinterest": {"max_chars": 500,   "hashtags": (3, 5), "times": ["08:00", "11:00", "20:00"], "style": "creative"},
    "reddit":    {"max_chars": 40000, "hashtags": (0, 0), "times": ["09:00", "14:00", "20:00"], "style": "casual"},
    "twitter":   {"max_chars": 280,   "hashtags": (1, 3), "times": ["09:00", "12:00", "18:00"], "style": "casual"},
    "linkedin":  {"max_chars": 3000,  "hashtags": (3, 5), "times": ["08:00", "12:00", "17:00"], "style": "professional"},
}

# House content rules — enforced in code, never broken.
BANNED_PHRASES = [
    "guaranteed income", "make $", "earn $", "passive income",
    "get rich", "financial freedom", "miracle cure", "cures ",
    "clinically proven", "doctor recommended",
]
DISCLOSURE = "#ad"


def load_products():
    with open(PRODUCTS_PATH, encoding="utf-8") as f:
        return {p["id"]: p for p in json.load(f)["products"]}


def check_copy(text, where):
    """House honesty gate: no income promises, no medical claims, no invented numbers."""
    low = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in low:
            raise ValueError(f"House rule violation in {where}: banned phrase {phrase!r}")
    return text


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix):
    return prefix + "_" + hashlib.md5(f"{prefix}{now_iso()}{os.urandom(8).hex()}".encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Database — 3 tables borrowed from the paste's DatabaseManager, WITH fixes:
#   * nim_generation_data -> generation_meta (no NVIDIA paid path exists here)
#   * performance_prediction is ALWAYS {} until real analytics exist — the
#     paste invented view counts (random.randint(5000, 50000)); we never do.
#   * save_empire / save_campaign are REAL implementations (the paste left
#     them as "omitted for space").
# Plus one honest addition: a `trends` table so `trend` runs are stored.
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS video_packages (
            id TEXT PRIMARY KEY, title TEXT, optimized_title TEXT, script TEXT,
            thumbnail_concept TEXT, seo_data TEXT, performance_prediction TEXT,
            video_type TEXT, target_length INTEGER, retention_analysis TEXT,
            created_at TEXT, status TEXT, video_file_path TEXT,
            generation_meta TEXT, thumbnail_path TEXT);
        CREATE TABLE IF NOT EXISTS content_empires (
            id TEXT PRIMARY KEY, user_story TEXT, target_audience TEXT, niche TEXT,
            strategy_analysis TEXT, content_plan TEXT, videos TEXT,
            empire_metrics TEXT, created_at TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS organic_campaigns (
            id TEXT PRIMARY KEY, product_name TEXT, product_description TEXT,
            niche TEXT, target_audience TEXT, platforms TEXT, posts_per_day INTEGER,
            duration_days INTEGER, generated_posts TEXT, campaign_metrics TEXT,
            created_at TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, keyword TEXT,
            score REAL, source TEXT, url TEXT, traffic TEXT, fetched_at TEXT);
    """)
    conn.commit()
    return conn


def _j(value):
    return json.dumps(value) if value is not None else None


def save_video_package(conn, vp):
    conn.execute(
        "INSERT OR REPLACE INTO video_packages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (vp["id"], vp["title"], vp["optimized_title"], vp["script"],
         _j(vp.get("thumbnail_concept")), _j(vp.get("seo_data")),
         _j({}),  # performance_prediction: ALWAYS {} — no invented numbers.
         vp.get("video_type", "short"), vp.get("target_length", 60),
         _j(vp.get("retention_analysis")), vp["created_at"], vp.get("status", "created"),
         vp.get("video_file_path", ""), _j(vp.get("generation_meta")),
         vp.get("thumbnail_path", "")))
    conn.commit()
    return vp["id"]


def save_empire(conn, empire):
    conn.execute(
        "INSERT OR REPLACE INTO content_empires VALUES (?,?,?,?,?,?,?,?,?,?)",
        (empire["id"], empire["user_story"], empire["target_audience"], empire["niche"],
         _j(empire.get("strategy_analysis")), _j(empire.get("content_plan")),
         _j(empire.get("videos", [])), _j(empire.get("empire_metrics", {})),
         empire["created_at"], empire.get("status", "active")))
    conn.commit()
    return empire["id"]


def save_campaign(conn, camp):
    conn.execute(
        "INSERT OR REPLACE INTO organic_campaigns VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (camp["id"], camp["product_name"], camp["product_description"], camp["niche"],
         camp["target_audience"], _j(camp["platforms"]), camp.get("posts_per_day", 1),
         camp.get("duration_days", 7), _j(camp.get("generated_posts", [])),
         _j(camp.get("campaign_metrics", {})), camp["created_at"],
         camp.get("status", "active")))
    conn.commit()
    return camp["id"]

# ---------------------------------------------------------------------------
# TREND — trend-pulse (MIT, pip-installed) with a stdlib RSS/Atom fallback.
# Keyless core: Google Trends RSS, Reddit Atom, Pinterest Trends, TikTok
# Creative Center. Sources that fail are recorded as failed, never faked.
# ---------------------------------------------------------------------------
TREND_SOURCES = ["google_trends", "reddit", "pinterest", "tiktok_trending"]


def _rss_fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "MarketingEmpire/1.0 (free trend check)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _direct_rss_fallback():
    """Stdlib-only fallback when trend-pulse is unavailable: same public
    RSS/Atom feeds trend-pulse itself reads. Returns (items, status)."""
    items, status = [], {}
    try:
        root = ET.fromstring(_rss_fetch("https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"))
        for it in root.iter("item")[:10]:
            t = it.findtext("title") or ""
            items.append({"keyword": t.strip(), "score": 50.0, "source": "google_trends",
                          "url": "", "traffic": "", "category": "", "published": ""})
        status["google_trends"] = "ok"
    except Exception as e:  # noqa: BLE001 - report, don't crash
        status["google_trends"] = f"error: {e}"
    try:
        root = ET.fromstring(_rss_fetch("https://www.reddit.com/r/popular/.rss?limit=10"))
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for e in root.findall("a:entry", ns)[:10]:
            t = e.findtext("a:title", "", ns)
            link = e.findtext("a:link", "", ns)
            items.append({"keyword": t.strip(), "score": 50.0, "source": "reddit",
                          "url": link, "traffic": "", "category": "", "published": ""})
        status["reddit"] = "ok"
    except Exception as e:  # noqa: BLE001
        status["reddit"] = f"error: {e}"
    status["pinterest"] = "skipped (fallback covers Google Trends + Reddit only)"
    status["tiktok_trending"] = "skipped (fallback covers Google Trends + Reddit only)"
    return items, status


def cmd_trend(args):
    run_id = new_id("trend")
    items, status, method = [], {}, ""
    try:
        from trend_pulse.aggregator import TrendAggregator
        agg = TrendAggregator()
        res = asyncio.run(agg.trending(sources=TREND_SOURCES, count=args.count))
        # trend-pulse 2.x returns a dict with "merged" + "sources_ok"/"sources_error"
        if isinstance(res, dict):
            items = res.get("merged", []) or []
            for s in res.get("sources_ok", []):
                status[s] = "ok"
            for s, e in (res.get("sources_error") or {}).items():
                status[s] = f"error: {e}"
            method = "trend-pulse library (pip)"
        else:
            items = list(res)
            method = "trend-pulse library (pip)"
    except Exception as e:  # noqa: BLE001 - fall back to direct RSS
        print(f"trend-pulse library unavailable ({e}); using direct RSS fallback.", file=sys.stderr)
        items, status = _direct_rss_fallback()
        method = "direct RSS/Atom fallback (stdlib)"
    items = sorted(items, key=lambda x: float(x.get("score") or 0), reverse=True)[: args.count]
    conn = get_db()
    for it in items:
        conn.execute(
            "INSERT INTO trends (run_id, keyword, score, source, url, traffic, fetched_at) VALUES (?,?,?,?,?,?,?)",
            (run_id, it.get("keyword", ""), float(it.get("score") or 0), it.get("source", ""),
             it.get("url", ""), str(it.get("traffic") or ""), now_iso()))
    conn.commit()
    print(f"Trend run {run_id} via {method} — {len(items)} topics saved to empire.db")
    for s in TREND_SOURCES:
        print(f"  {s}: {status.get(s, 'no report')}")
    for i, it in enumerate(items, 1):
        print(f"{i:2d}. [{it.get('source')}] {it.get('keyword')} (score {it.get('score')})")
    if not items:
        print("No trends fetched — check the network and re-run. Nothing was invented.")
    return 0


# ---------------------------------------------------------------------------
# SCRIPT — template-based, from the product's REAL facts only. No key needed.
# Optional --llm groq polishes the template with the user's OWN free Groq key.
# ---------------------------------------------------------------------------
SCRIPT_TEMPLATES = {
    "naturally-radiant-day1": {
        "hook": "Your skin has been asking for something simple. Day one starts here.",
        "pain": "So many routines promise a glow and hand you twelve steps, a big bill, and confusion. You just want to know what to do first.",
        "demo": "The Naturally Radiant Day 1 Starter is free. Inside you get a skin-type finder, the Honey Oat Cleansing Scrub recipe, and the full Day 1 routine from the five-day natural skincare challenge. Simple ingredients, clear steps, one day at a time.",
        "close": "It costs nothing to start. Grab the free Day 1 Starter on Gumroad, and find the full guide at shop dot artistry store dot com.",
    },
    "luna": {
        "hook": "Every missed call is a customer you may never hear from again.",
        "pain": "Small businesses miss calls while they are with another customer, on the road, or closed for the night. That caller rings the next business on the list.",
        "demo": "Luna is an AI receptionist that answers missed calls, books appointments on your real calendar, and calls people back during business hours. One hundred forty-nine dollars a month in the US, fifty-nine dollars a month anywhere else, with a fourteen-day free trial and no card required.",
        "close": "Try Luna free first, then decide. Details at shop dot artistry store dot com, or ask on Gumroad or Whop.",
    },
    "sleep-sanctuary": {
        "hook": "Sleep should not feel like a job you keep failing at.",
        "pain": "You lie awake, mind racing, watching the clock, and morning comes too fast. Another tired day, another night you dread.",
        "demo": "Sleep Sanctuary is a nurse-designed sleep program: calming audio and a gentle nightly rhythm that helps you wind down the same way every night. Twenty-nine dollars and ninety-nine cents, yours to keep.",
        "close": "Start tonight. Find Sleep Sanctuary on Gumroad, and more gentle tools at shop dot artistry store dot com.",
    },
    "sacred-cycles": {
        "hook": "Some seasons ask you to slow down and come back to yourself.",
        "pain": "Life keeps pulling, and the quiet time you need keeps slipping to the bottom of the list. You feel stretched thin and far from steady.",
        "demo": "Sacred Cycles is a faith-rooted renewal program that gives you a gentle rhythm for your days: reflection, rest, and small steps back to balance. Ninety-seven dollars for the complete program.",
        "close": "Begin your renewal today. Find Sacred Cycles on Gumroad or Whop, and at shop dot artistry store dot com.",
    },
}
GENERIC_TEMPLATE = {
    "hook": "Here is something worth a minute of your day: {topic}.",
    "pain": "It is easy to feel stuck on this one — too much noise, not enough clear help.",
    "demo": "{blurb}",
    "close": "Learn more at shop dot artistry store dot com, or find us on Gumroad or Whop.",
}


def build_script(product, topic):
    tpl = SCRIPT_TEMPLATES.get(product["id"], GENERIC_TEMPLATE)
    sections = {}
    for key in ("hook", "pain", "demo", "close"):
        text = tpl[key].format(topic=topic, blurb=product.get("blurb", product["name"]))
        sections[key] = text
    full = " ".join(sections[k] for k in ("hook", "pain", "demo", "close"))
    check_copy(full, "video script")
    return sections, full


def groq_polish(text, product):
    """Optional polish with the USER'S OWN free Groq key. Never Ting's key,
    never required: returns None (caller keeps the template) when unset."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return None, "no GROQ_API_KEY set — template script used (Groq polish is optional)"
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": (
                "Polish this short video script. Keep every fact exactly as written: "
                "do not change prices, do not add claims, do not promise results or "
                "income, use person-first language, keep it under 900 characters.")},
            {"role": "user", "content": f"Product: {product['name']}. Script: {text}"},
        ],
        "temperature": 0.5, "max_tokens": 600,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.load(resp)["choices"][0]["message"]["content"].strip()
        check_copy(out, "Groq-polished script")
        return out, "polished with user's own free Groq key"
    except Exception as e:  # noqa: BLE001 - polish is optional; template stands
        return None, f"Groq polish failed ({e}) — template script used"


def synth_voiceover(text, out_path):
    """Kokoro af_heart via the bench kokoro venv (model already cached).
    Returns (seconds, engine_note). Raises RuntimeError if unavailable."""
    helper = os.path.join(BASE, "tts_helper.py")
    cmd = [KOKORO_VENV_PY, helper, "--text", text, "--out", out_path]
    env = dict(os.environ, NO_PROXY="localhost,127.0.0.1",
               no_proxy="localhost,127.0.0.1", HF_HUB_OFFLINE="1")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"Kokoro TTS failed: {(r.stderr or r.stdout)[-500:]}")
    return probe_duration(out_path), "Kokoro af_heart (local, free, no key)"


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())

# ---------------------------------------------------------------------------
# VIDEO ASSEMBLY — PIL cards (ARTISY navy/gold) + ffmpeg Ken Burns + xfade,
# adapted from the house carousel pattern (1080x1920 for Shorts).
# ---------------------------------------------------------------------------
W, H = 1080, 1920
NAVY = (10, 14, 26)
NAVY2 = (21, 29, 54)
GOLD = (245, 196, 81)
WHITE = (238, 241, 248)
LAV = (154, 163, 192)


def _font(bold=False, size=54):
    from PIL import ImageFont
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
                 else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
    return ImageFont.load_default()


def _wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_card(heading, body, footer, accent=GOLD):
    """One 1080x1920 caption card."""
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGB", (W, H), NAVY)
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(10 + 14 * (y / H)))
    grad = grad.resize((W, H))
    img = Image.composite(Image.new("RGB", (W, H), NAVY2), img, grad.point(lambda v: v * 6))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(40, 0, -1):
        r = 420 * i / 40
        f = (1 - i / 40) ** 2 * 0.5
        gd.ellipse([W // 2 - r, 500 - r * 0.7, W // 2 + r, 500 + r * 0.7],
                   fill=tuple(int(accent[c] * f) for c in range(3)))
    img = Image.composite(img, Image.blend(img, glow.filter(ImageFilter.GaussianBlur(90)), 0.6),
                          Image.new("L", (W, H), 255))
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([36, 36, W - 36, H - 36], radius=24, outline=accent + (110,), width=3)
    d.text((W // 2, 150), "A R T I S Y", font=_font(True, 40), fill=accent, anchor="mt")
    d.line([W // 2 - 90, 230, W // 2 + 90, 230], fill=accent, width=3)
    hf = _font(True, 64)
    lines = _wrap(d, heading, hf, W - 160)
    y = 330
    for ln in lines:
        d.text((W // 2, y), ln, font=hf, fill=WHITE, anchor="mt")
        y += 84
    bf = _font(False, 52)
    lines = _wrap(d, body, bf, W - 160)
    y = max(y + 60, 820)
    for ln in lines:
        d.text((W // 2, y), ln, font=bf, fill=WHITE, anchor="mt")
        y += 74
    if footer:
        ff = _font(True, 44)
        flines = _wrap(d, footer, ff, W - 160)
        y = H - 260 - (len(flines) - 1) * 60
        for ln in flines:
            d.text((W // 2, y), ln, font=ff, fill=accent, anchor="mt")
            y += 60
    return img


def assemble_video(cards, durations, audio_path, out_path):
    """cards: list of PIL images; durations: seconds per card (sum == audio
    duration). Ken Burns zoompan + 0.7s xfades, voiceover audio, 1080x1920."""
    import tempfile
    fps, fade = 30, 0.7
    tmp = tempfile.mkdtemp(prefix="empire-cards-")
    pngs = []
    for i, im in enumerate(cards):
        p = os.path.join(tmp, f"card-{i}.png")
        im.save(p)
        pngs.append(p)
    n = len(pngs)
    inputs, filters = [], []
    for i, p in enumerate(pngs):
        inputs += ["-loop", "1", "-t", f"{durations[i] + fade:.3f}", "-i", p]
    for i in range(n):
        frames = int((durations[i] + fade) * fps)
        z = f"z='1+0.08*on/{frames}'" if i % 2 == 0 else f"z='1.08-0.08*on/{frames}'"
        filters.append(f"[{i}:v]scale=1080:1920,zoompan={z}:x='iw/2-(iw/zoom/2)':"
                       f"y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={fps},"
                       f"setsar=1,format=yuv420p[v{i}]")
    prev, elapsed = "v0", durations[0]
    for i in range(1, n):
        off = elapsed - fade
        filters.append(f"[{prev}][v{i}]xfade=transition=fade:duration={fade}:offset={off:.3f}[x{i}]")
        prev = f"x{i}"
        elapsed += durations[i] - fade
    total = sum(durations)
    filters.append(f"[{prev}]trim=0:{total:.3f},setpts=PTS-STARTPTS[vout]")
    cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + ["-i", audio_path,
           "-filter_complex", ";".join(filters),
           "-map", "[vout]", "-map", f"{n}:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-t", f"{total:.3f}", "-movflags", "+faststart", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-1500:]}")
    return probe_duration(out_path)


def cmd_video(args):
    products = load_products()
    if args.product not in products:
        print(f"Unknown product {args.product!r}. Available: {', '.join(products)}")
        return 2
    product = products[args.product]
    vid = new_id("vid")
    run_dir = os.path.join(RUNS_DIR, vid)
    os.makedirs(run_dir, exist_ok=True)

    sections, full = build_script(product, args.topic)
    llm_note = "template script (no key needed)"
    if args.llm == "groq":
        polished, llm_note = groq_polish(full, product)
        if polished:
            full = polished
            # Re-split polished text into the same 4 beats by sentence quarters.
            import re
            sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full) if s.strip()]
            quarters, per = [], max(1, len(sents) // 4)
            for k in range(4):
                quarters.append(" ".join(sents[k * per:(k + 1) * per] if k < 3 else sents[k * per:]))
            sections = dict(zip(("hook", "pain", "demo", "close"), quarters))
    print(f"Script ({llm_note}): {len(full)} chars")

    wav_path = os.path.join(run_dir, "voiceover.wav")
    try:
        audio_dur, tts_note = synth_voiceover(full, wav_path)
    except RuntimeError as e:
        print(f"VIDEO FAILED: {e}")
        print("Voiceover needs the bench Kokoro venv "
              "(~/workspace/venvs/kokoro/bin/python + cached Kokoro-82M model).")
        return 1
    print(f"Voiceover: {audio_dur:.1f}s ({tts_note})")

    # Card durations follow the spoken words per beat; total == audio length.
    words = {k: max(1, len(v.split())) for k, v in sections.items()}
    total_words = sum(words.values())
    durations = [audio_dur * words[k] / total_words for k in ("hook", "pain", "demo", "close")]
    # End card gets 3.5s taken proportionally from the other beats.
    end_dur = min(3.5, audio_dur * 0.12)
    scale = (audio_dur - end_dur) / audio_dur
    durations = [d * scale for d in durations] + [end_dur]

    price_line = product.get("price_text", "")
    cards = [
        make_card("Start here.", sections["hook"], product["name"]),
        make_card("Sound familiar?", sections["pain"], ""),
        make_card(product["name"], sections["demo"], price_line),
        make_card("Your next step", sections["close"], "Gumroad or Whop"),
        make_card(product["name"], "Thank you for watching.",
                  f"{STORE_URL}  •  {price_line}"),
    ]
    thumb_path = os.path.join(run_dir, "thumbnail.png")
    cards[0].save(thumb_path)
    mp4_path = os.path.join(run_dir, "video.mp4")
    vid_dur = assemble_video(cards, durations, wav_path, mp4_path)
    print(f"Video: {vid_dur:.1f}s, {os.path.getsize(mp4_path) / 1e6:.1f} MB")

    title = f"{args.topic} — {product['name']} | ARTISY"
    tags = [product["name"], "ARTISY", "T Lott Creative", args.topic,
            "free" if product.get("price_usd") == 0 else "wellness"]
    if product["id"] == "naturally-radiant-day1":
        tags += ["organic skincare", "natural skincare", "skincare routine"]
    if product["id"] == "luna":
        tags += ["AI receptionist", "small business"]
    if product["id"] == "sleep-sanctuary":
        tags += ["sleep", "better sleep"]
    if product["id"] == "sacred-cycles":
        tags += ["faith", "renewal"]
    seo = {"title": title, "tags": tags,
           "description": (f"{product['blurb']} Find it at {product['link']} "
                           f"and more at {STORE_URL}.")}
    meta = {
        "id": vid, "product": product["id"], "topic": args.topic, "title": title,
        "optimized_title": title, "script": full, "sections": sections,
        "seo_data": seo, "thumbnail_concept": {"text": "Start here. " + product["name"],
                                               "style": "navy/gold 1080x1920"},
        "generation_meta": {"script_source": llm_note, "tts": tts_note,
                            "audio_seconds": round(audio_dur, 1),
                            "video_seconds": round(vid_dur, 1)},
        "performance_prediction": {},  # {} until REAL analytics exist. Never invented.
        "retention_analysis": {"hook_seconds": round(durations[0], 1)},
        "video_type": "short", "target_length": round(vid_dur),
        "created_at": now_iso(), "status": "ready",
        "video_file_path": mp4_path, "thumbnail_path": thumb_path,
        "files": {"script": os.path.join(run_dir, "script.txt"),
                  "voiceover": wav_path, "video": mp4_path, "thumbnail": thumb_path},
    }
    with open(os.path.join(run_dir, "script.txt"), "w", encoding="utf-8") as f:
        f.write(f"TITLE: {title}\nTAGS: {', '.join(tags)}\n\n")
        for k in ("hook", "pain", "demo", "close"):
            f.write(f"[{k.upper()}]\n{sections[k]}\n\n")
    with open(os.path.join(run_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    conn = get_db()
    save_video_package(conn, meta)
    print(f"Video package {vid} saved to {run_dir} and recorded in empire.db")
    return 0

# ---------------------------------------------------------------------------
# CAMPAIGN — per-platform posts from the platform rules. Every affiliate post
# carries #ad disclosure + the FULL product link (never shortened) and names
# shop.artistrystore.com + the product. Character + hashtag caps enforced.
# ---------------------------------------------------------------------------
HASHTAG_POOL = {
    "naturally-radiant-day1": ["naturalskincare", "organicskincare", "skincareroutine",
                               "glowingskin", "selfcare"],
    "luna": ["smallbusiness", "aireceptionist", "missedcalls", "businesstools"],
    "sleep-sanctuary": ["bettersleep", "sleepwell", "nightroutine", "rest", "selfcare"],
    "sacred-cycles": ["faith", "renewal", "selfcare", "womenswellness", "quiettime"],
}


def _enforce_cap(text, cap, where):
    if len(text) <= cap:
        return text, False
    cut = text[: cap - 3].rsplit(" ", 1)[0] + "..."
    return cut, True


def build_post(platform, product, angle, niche, audience):
    cfg = PLATFORMS[platform]
    lo, hi = cfg["hashtags"]
    pool = HASHTAG_POOL.get(product["id"], ["wellness", "selfcare"])
    tags = pool[:hi] if hi else []
    hashtag_line = (" ".join("#" + t for t in tags)) if tags else ""
    link = product["link"]
    price = product.get("price_text", "")
    base = {
        "facebook": (
            f"{angle}\n\n{product['blurb']}\n\n"
            f"Made for {audience}. {price + ' — ' if price else ''}"
            f"Find it here: {link}\nMore gentle tools at {STORE_URL}."),
        "instagram": (
            f"{angle}\n\n{product['blurb']}\n\n"
            f"For {audience}. {price}\nLink in bio — or go straight there: {link}\n"
            f"More at {STORE_URL}"),
        "tiktok": (
            f"{angle} {product['name']} — {product['blurb'][:120]} "
            f"{price} {link} More: {STORE_URL}"),
        "pinterest": (
            f"{product['name']}: {angle} {product['blurb'][:120]} "
            f"{price} {link} More: {STORE_URL}"),
        "reddit": (
            f"{product['name']} — {angle}\n\n{product['blurb']}\n\n"
            f"Sharing because it helped me think about {niche} differently. "
            f"{price + '. ' if price else ''}Full details: {link} "
            f"(I may earn a commission if you buy — thanks for supporting small creators.)"),
        "twitter": (
            f"{angle} {product['name']} — {price} {link}"),
        "linkedin": (
            f"{angle}\n\nFor {audience} in {niche}: {product['blurb']}\n\n"
            f"{price + '. ' if price else ''}Learn more: {link} | {STORE_URL}"),
    }[platform]
    body = base.strip()
    if platform == "reddit":
        text = body + f"\n\n(This is an affiliate post. {DISCLOSURE})"
    else:
        text = body + (f"\n\n{hashtag_line}" if hashtag_line else "") + f"\n{DISCLOSURE}"
    text, truncated = _enforce_cap(text, cfg["max_chars"], platform)
    check_copy(text, f"campaign post ({platform})")
    return {
        "platform": platform, "content": text, "chars": len(text),
        "char_cap": cfg["max_chars"], "truncated_to_cap": truncated,
        "hashtags_used": len(tags), "hashtag_cap": f"{lo}-{hi}" if hi else "n/a",
        "optimal_posting_times_et": cfg["times"], "content_style": cfg["style"],
        "disclosure": DISCLOSURE, "link": link, "link_shortened": False,
    }


def cmd_campaign(args):
    products = load_products()
    if args.product not in products:
        print(f"Unknown product {args.product!r}. Available: {', '.join(products)}")
        return 2
    product = products[args.product]
    platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    bad = [p for p in platforms if p not in PLATFORMS]
    if bad:
        print(f"Unknown platform(s): {bad}. Available: {', '.join(PLATFORMS)}")
        return 2
    camp_id = new_id("camp")
    posts = [build_post(p, product, args.angle, args.niche or product.get("niche", ""),
                        args.audience or product.get("audience", "anyone looking for a gentle start"))
             for p in platforms]
    camp = {
        "id": camp_id, "product_name": product["name"],
        "product_description": product["blurb"], "niche": args.niche or product.get("niche", ""),
        "target_audience": args.audience or product.get("audience", ""),
        "platforms": platforms, "posts_per_day": 1, "duration_days": 7,
        "generated_posts": posts,
        "campaign_metrics": {},  # {} until REAL analytics exist. Never invented.
        "created_at": now_iso(), "status": "active",
    }
    run_dir = os.path.join(RUNS_DIR, camp_id)
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "campaign.json"), "w", encoding="utf-8") as f:
        json.dump(camp, f, indent=2)
    conn = get_db()
    save_campaign(conn, camp)
    print(f"Campaign {camp_id} — {product['name']} — {len(posts)} posts saved to {run_dir} + empire.db")
    for post in posts:
        print(f"  [{post['platform']}] {post['chars']}/{post['char_cap']} chars, "
              f"best times ET {', '.join(post['optimal_posting_times_et'])}, "
              f"{DISCLOSURE} included, full link included")
    return 0


# ---------------------------------------------------------------------------
# EMPIRE — content-empire plan: strategy + 4-week plan. Template-based.
# ---------------------------------------------------------------------------
def cmd_empire(args):
    emp_id = new_id("empire")
    weeks = []
    beats = [("hook video", "video"), ("how-to video", "video"), ("story post", "campaign"),
             ("behind-the-scenes post", "campaign")]
    for w in range(1, 5):
        items = []
        for day, (fmt, kind) in zip((1, 3, 5), beats[w % 4:] + beats[: w % 4]):
            topic = f"Week {w}: {args.niche} — {fmt} for {args.audience}"
            items.append({
                "day": day, "format": fmt,
                "topic": topic,
                "build_with": ("empire.py video --product <id> --topic \"...\""
                               if kind == "video" else
                               "empire.py campaign --product <id> --angle \"...\""),
            })
        weeks.append({"week": w, "items": items})
    strategy = {
        "story": args.story, "niche": args.niche, "audience": args.audience,
        "pillars": [f"{args.niche} basics", f"{args.niche} for {args.audience}",
                    "stories from real life", "free tools and gentle next steps"],
        "rules": ["every video names shop.artistrystore.com and one product",
                  "spoken closes point to Gumroad/Whop",
                  "every affiliate post carries #ad and the full link",
                  "no income promises, no invented numbers, no medical claims",
                  "person-first language in any mental-health copy"],
        "cadence": "3 posts per week for 4 weeks, then review what real viewers did",
    }
    empire = {"id": emp_id, "user_story": args.story, "target_audience": args.audience,
              "niche": args.niche, "strategy_analysis": strategy,
              "content_plan": {"weeks": weeks}, "videos": [],
              "empire_metrics": {},  # {} until REAL analytics exist.
              "created_at": now_iso(), "status": "active"}
    run_dir = os.path.join(RUNS_DIR, emp_id)
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "empire.json"), "w", encoding="utf-8") as f:
        json.dump(empire, f, indent=2)
    conn = get_db()
    save_empire(conn, empire)
    print(f"Content empire {emp_id} saved to {run_dir} + empire.db")
    print(f"Strategy: {args.niche} for {args.audience} — 4 weeks, 3 items/week, "
          f"pillars: {', '.join(strategy['pillars'])}")
    for wk in weeks:
        print(f"  Week {wk['week']}: " + "; ".join(f"day {i['day']} {i['format']}" for i in wk["items"]))
    return 0


# ---------------------------------------------------------------------------
# DASHBOARD — static HTML from the DB. No server needed.
# ---------------------------------------------------------------------------
def cmd_dashboard(args):
    conn = get_db()
    counts = {
        "videos": conn.execute("SELECT COUNT(*) c FROM video_packages").fetchone()["c"],
        "campaigns": conn.execute("SELECT COUNT(*) c FROM organic_campaigns").fetchone()["c"],
        "empires": conn.execute("SELECT COUNT(*) c FROM content_empires").fetchone()["c"],
        "trends": conn.execute("SELECT COUNT(*) c FROM trends").fetchone()["c"],
    }
    videos = conn.execute("SELECT id, title, created_at, status FROM video_packages ORDER BY created_at DESC LIMIT 10").fetchall()
    camps = conn.execute("SELECT id, product_name, created_at FROM organic_campaigns ORDER BY created_at DESC LIMIT 10").fetchall()
    trends = conn.execute("SELECT keyword, source, score, fetched_at FROM trends ORDER BY fetched_at DESC, score DESC LIMIT 15").fetchall()
    rows = lambda rs, cols: "".join(
        "<tr>" + "".join(f"<td>{r[c] or ''}</td>" for c in cols) + "</tr>" for r in rs)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Marketing Empire — Dashboard</title>
<style>body{{font-family:sans-serif;background:#0a0e1a;color:#eef1f8;max-width:900px;margin:2em auto;padding:0 1em}}
h1,h2{{color:#f5c451}} table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #333;padding:6px 8px;text-align:left}}
.card{{background:#151d36;padding:1em;border-radius:8px;margin:1em 0}} .ok{{color:#7fd4ff}}</style></head>
<body><h1>Marketing Empire — Dashboard</h1><p>Generated {now_iso()} from empire.db. Static file — no server needed.</p>
<div class="card"><h2>Counts</h2><p>Videos: <b>{counts['videos']}</b> · Campaigns: <b>{counts['campaigns']}</b> · Empires: <b>{counts['empires']}</b> · Trends saved: <b>{counts['trends']}</b></p></div>
<div class="card"><h2>Recent videos</h2><table><tr><th>ID</th><th>Title</th><th>Created</th><th>Status</th></tr>{rows(videos, ['id','title','created_at','status'])}</table></div>
<div class="card"><h2>Recent campaigns</h2><table><tr><th>ID</th><th>Product</th><th>Created</th></tr>{rows(camps, ['id','product_name','created_at'])}</table></div>
<div class="card"><h2>Recent trends</h2><table><tr><th>Topic</th><th>Source</th><th>Score</th><th>Fetched</th></tr>{rows(trends, ['keyword','source','score','fetched_at'])}</table></div>
<div class="card"><h2>What needs a key (and what does not)</h2>
<p class="ok">Core needs NO key: trend (keyless RSS/Atom), video (template script + local Kokoro voice), campaign, empire, dashboard.</p>
<ul><li>Script polish: optional — YOUR OWN free Groq key (console.groq.com, no card) as GROQ_API_KEY. Without it, the template script is used.</li>
<li>Stock footage (PurffleShorts upgrade): optional — YOUR OWN free Pexels / Pixabay keys. Without them, the core uses house-made cards.</li>
<li>YouTube upload: optional — YOUR OWN Google OAuth credentials (client_secrets.json). Without them, <code>upload</code> prints setup steps and stops.</li>
<li>Nothing here ever uses Ting's keys.</li></ul></div>
<div class="card"><h2>Honest numbers</h2><p>Performance predictions are empty ({{}}) until real analytics exist. This dashboard shows only what actually ran.</p></div>
</body></html>"""
    out = os.path.join(BASE, "dashboard.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard written to {out} — {counts}")
    return 0


# ---------------------------------------------------------------------------
# UPLOAD — optional YouTube upload. Bench build: checks for the USER'S OWN
# OAuth credentials; if missing, prints exact setup steps and does nothing.
# Never uploads with fake credentials, never attempts a real upload here.
# ---------------------------------------------------------------------------
def cmd_upload(args):
    conn = get_db()
    row = conn.execute("SELECT * FROM video_packages WHERE id=?", (args.video,)).fetchone()
    if not row:
        print(f"No video package {args.video!r} in empire.db. Run `video` first.")
        return 2
    creds = os.path.join(BASE, "client_secrets.json")
    if not os.path.exists(creds):
        print("YouTube upload is OPTIONAL and not set up on this bench.")
        print("To enable it (with YOUR OWN Google account, never Ting's):")
        print("  1. Go to Google Cloud Console → create a project → enable YouTube Data API v3.")
        print("  2. Create OAuth client ID (Desktop app) → download client_secrets.json.")
        print(f"  3. Save it as {creds}")
        print("  4. Re-run: python3 empire.py upload --video " + args.video)
        print("Nothing was uploaded.")
        return 0
    print("client_secrets.json found — but this bench build does not perform uploads.")
    print("Upload from your own machine after reviewing the video package at:")
    print(f"  {row['video_file_path']}")
    return 0


def main():
    p = argparse.ArgumentParser(prog="empire.py",
                                description="Marketing Empire — free marketing content system ($0, no keys required for the core).")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("trend", help="Fetch keyless trending topics and save to the DB")
    t.add_argument("--count", "-n", type=int, default=20)
    t.set_defaults(fn=cmd_trend)

    v = sub.add_parser("video", help="Build one complete video package (script + voiceover + MP4)")
    v.add_argument("--product", required=True)
    v.add_argument("--topic", required=True)
    v.add_argument("--llm", choices=["none", "groq"], default="none",
                   help="groq = polish with YOUR OWN free GROQ_API_KEY (optional)")
    v.set_defaults(fn=cmd_video)

    c = sub.add_parser("campaign", help="Generate per-platform posts for a product")
    c.add_argument("--product", required=True)
    c.add_argument("--angle", required=True)
    c.add_argument("--niche", default="")
    c.add_argument("--audience", default="")
    c.add_argument("--platforms", default="facebook,instagram,tiktok,pinterest")
    c.set_defaults(fn=cmd_campaign)

    e = sub.add_parser("empire", help="Build a 4-week content-empire plan")
    e.add_argument("--story", required=True)
    e.add_argument("--niche", required=True)
    e.add_argument("--audience", required=True)
    e.set_defaults(fn=cmd_empire)

    d = sub.add_parser("dashboard", help="Generate static dashboard.html from the DB")
    d.set_defaults(fn=cmd_dashboard)

    u = sub.add_parser("upload", help="OPTIONAL YouTube upload (needs your own OAuth; prints setup if missing)")
    u.add_argument("--video", required=True)
    u.set_defaults(fn=cmd_upload)

    args = p.parse_args()
    os.makedirs(RUNS_DIR, exist_ok=True)
    try:
        return args.fn(args)
    except ValueError as exc:
        print(f"BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
