#!/usr/bin/env python3
"""Marketing Empire — web backend (bench build, Nov 8, 2026).

STDLIB-ONLY server (http.server + sqlite3 + threading + json). No Flask,
even though Flask 3.1.3 happens to be installed on this bench — stdlib keeps
the server portable to any plain-Python host (notably PythonAnywhere, which
is WSGI-shaped, and a Render Dockerfile build).

This is a WEB BACK DOOR to the CLI, not a second engine. Every piece of
generation logic is imported from ../empire.py and called, never copied:

  * build_script / groq_polish / synth_voiceover / make_card /
    assemble_video / save_video_package  — video jobs
  * build_post / save_campaign            — campaigns
  * cmd_trend / cmd_empire                — trends + empire plans (called with
    an argparse-style namespace; their stdout is captured and their JSON/DB
    output is read back, so the CLI stays the single source of truth)
  * check_copy / load_products            — house content rules + products

House rules enforced server-side (empire.check_copy + post-hoc checks):
  * every video names shop.artistrystore.com + a real product; spoken closes
    point to Gumroad/Whop (verified on the finished script — a violation
    fails the job honestly, it is never silently fixed-and-shipped);
  * every campaign post carries #ad + the FULL product link (never
    shortened) + the store URL;
  * no income promises, no medical claims, no invented numbers
    (performance predictions stay {} — the server never invents them);
  * person-first language is checked by check_copy's banned-phrase list.

Video jobs are ASYNC: POST /api/video returns a job_id at once (202) and a
single worker thread renders jobs in order (Kokoro TTS + ffmpeg take
~1-2 min per video; the house rhythm is create-today-harvest-tomorrow).
Job state lives in a `jobs` table in empire.db; results reuse the CLI's
own tables (video_packages / organic_campaigns / content_empires / trends)
and runs/<id>/ files.

GROQ KEY HANDLING: an optional per-request `groq_key` is used IN MEMORY
ONLY for that one video job — it is set as an environment variable inside
the single worker thread for the duration of that job's polish call and
deleted in a `finally` block. It is NEVER written to disk, the DB, or any
log, and request bodies are never logged. Without it, the template script
is used and the job says so.

Run on the bench:
    python3 server.py            # listens on 127.0.0.1:8000 by default
    PORT=8000 python3 server.py  # or set PORT / HOST explicitly
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import queue
import re
import sqlite3
import sys
import threading
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

# --- import the CLI engine (never re-implement it) ---------------------------
BUILD_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

import empire  # noqa: E402  (the CLI core: build_script, build_post, ...)

BASE = BUILD_DIR
DB_PATH = empire.DB_PATH
RUNS_DIR = empire.RUNS_DIR
STORE_URL = empire.STORE_URL
STATIC_DIR = os.path.join(BASE, "web", "static")

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

# Files a download URL may ever serve, and their on-disk names in runs/<id>/.
ALLOWED_FILES = {
    "video": "video.mp4",
    "script": "script.txt",
    "thumbnail": "thumbnail.png",
    "voiceover": "voiceover.wav",
}
MIME = {"video.mp4": "video/mp4", "script.txt": "text/plain; charset=utf-8",
        "thumbnail.png": "image/png", "voiceover.wav": "audio/wav"}

# ---------------------------------------------------------------------------
# Jobs store (SQLite `jobs` table in the CLI's own empire.db)
# ---------------------------------------------------------------------------
_db_lock = threading.Lock()


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, kind TEXT, status TEXT,
            product TEXT, topic TEXT, progress TEXT,
            files TEXT, error TEXT, created_at TEXT, updated_at TEXT);
    """)
    conn.commit()
    return conn


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _job_create(job_id, kind, product="", topic=""):
    with _db_lock:
        conn = _db()
        try:
            conn.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
                (job_id, kind, "queued", product, topic, "queued",
                 json.dumps({}), "", _now(), _now()))
            conn.commit()
        finally:
            conn.close()


def _job_update(job_id, **fields):
    fields["updated_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in fields)
    with _db_lock:
        conn = _db()
        try:
            conn.execute(f"UPDATE jobs SET {sets} WHERE id=?",
                         (*fields.values(), job_id))
            conn.commit()
        finally:
            conn.close()


def _job_get(job_id):
    with _db_lock:
        conn = _db()
        try:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def _job_public(row):
    files = json.loads(row.get("files") or "{}")
    out = {"job_id": row["id"], "kind": row.get("kind", "video"),
           "status": row["status"], "progress": row.get("progress") or "",
           "created_at": row.get("created_at"), "updated_at": row.get("updated_at")}
    if files:
        out["files"] = files
    if row.get("error"):
        out["error"] = row["error"]
    if row.get("product"):
        out["product"] = row["product"]
    if row.get("topic"):
        out["topic"] = row["topic"]
    return out


# ---------------------------------------------------------------------------
# House-rule verification on finished output (fail honestly, never fix+ship)
# ---------------------------------------------------------------------------
def _verify_video_script(full, product):
    empire.check_copy(full, "video script")
    if STORE_URL not in full and "shop dot artistry store dot com" not in full:
        raise ValueError("House rule violation in video script: "
                         "script does not name shop.artistrystore.com")
    if product["name"] not in full and "Naturally Radiant" not in full:
        raise ValueError("House rule violation in video script: "
                         "script does not name the product")
    low = full.lower()
    if "gumroad" not in low and "whop" not in low:
        raise ValueError("House rule violation in video script: "
                         "spoken close does not point to Gumroad/Whop")


def _verify_post(post, product):
    text = post["content"]
    empire.check_copy(text, f"campaign post ({post['platform']})")
    if "#ad" not in text:
        raise ValueError(f"House rule violation in campaign post "
                         f"({post['platform']}): missing #ad disclosure")
    if product["link"] not in text:
        raise ValueError(f"House rule violation in campaign post "
                         f"({post['platform']}): missing full product link")
    if STORE_URL not in text:
        raise ValueError(f"House rule violation in campaign post "
                         f"({post['platform']}): missing shop.artistrystore.com")


# ---------------------------------------------------------------------------
# Video worker — one job at a time, in order. Orchestration only: every
# heavy step is an imported empire.py function (see module docstring).
# ---------------------------------------------------------------------------
_job_queue: "queue.Queue[dict]" = queue.Queue()


def _run_video_job(job):
    job_id = job["job_id"]
    product_id = job["product"]
    topic = job["topic"]
    groq_key = job.get("groq_key")  # in-memory only; never persisted/logged
    products = empire.load_products()
    product = products[product_id]
    run_dir = os.path.join(RUNS_DIR, job_id)
    os.makedirs(run_dir, exist_ok=True)

    def progress(pct, note):
        _job_update(job_id, status="working", progress=f"{pct}% — {note}")

    try:
        progress(5, "building script")
        sections, full = empire.build_script(product, topic)
        llm_note = "template script (no key needed)"
        if groq_key:
            # groq_polish reads GROQ_API_KEY from the environment. Set it
            # for this one worker-thread call only, then delete it — the key
            # never touches disk, the DB, or a log. Single worker thread, so
            # no other job can observe it mid-flight.
            old = os.environ.get("GROQ_API_KEY")
            os.environ["GROQ_API_KEY"] = groq_key
            try:
                polished, llm_note = empire.groq_polish(full, product)
            finally:
                if old is None:
                    os.environ.pop("GROQ_API_KEY", None)
                else:
                    os.environ["GROQ_API_KEY"] = old
            if polished:
                full = polished
                sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full) if s.strip()]
                quarters, per = [], max(1, len(sents) // 4)
                for k in range(4):
                    quarters.append(" ".join(sents[k * per:(k + 1) * per]
                                             if k < 3 else sents[k * per:]))
                sections = dict(zip(("hook", "pain", "demo", "close"), quarters))
        _verify_video_script(full, product)

        progress(20, "synthesising voiceover (Kokoro af_heart)")
        wav_path = os.path.join(run_dir, "voiceover.wav")
        audio_dur, tts_note = empire.synth_voiceover(full, wav_path)

        # Card durations follow the spoken words per beat; total == audio.
        words = {k: max(1, len(v.split())) for k, v in sections.items()}
        total_words = sum(words.values())
        durations = [audio_dur * words[k] / total_words
                     for k in ("hook", "pain", "demo", "close")]
        end_dur = min(3.5, audio_dur * 0.12)
        scale = (audio_dur - end_dur) / audio_dur
        durations = [d * scale for d in durations] + [end_dur]

        progress(55, "building caption cards")
        price_line = product.get("price_text", "")
        cards = [
            empire.make_card("Start here.", sections["hook"], product["name"]),
            empire.make_card("Sound familiar?", sections["pain"], ""),
            empire.make_card(product["name"], sections["demo"], price_line),
            empire.make_card("Your next step", sections["close"], "Gumroad or Whop"),
            empire.make_card(product["name"], "Thank you for watching.",
                             f"{STORE_URL}  •  {price_line}"),
        ]
        thumb_path = os.path.join(run_dir, "thumbnail.png")
        cards[0].save(thumb_path)
        mp4_path = os.path.join(run_dir, "video.mp4")

        progress(70, "assembling video (ffmpeg)")
        vid_dur = empire.assemble_video(cards, durations, wav_path, mp4_path)

        progress(90, "saving package")
        title = f"{topic} — {product['name']} | ARTISY"
        tags = [product["name"], "ARTISY", "T Lott Creative", topic,
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
            "id": job_id, "product": product["id"], "topic": topic, "title": title,
            "optimized_title": title, "script": full, "sections": sections,
            "seo_data": seo,
            "thumbnail_concept": {"text": "Start here. " + product["name"],
                                  "style": "navy/gold 1080x1920"},
            "generation_meta": {"script_source": llm_note, "tts": tts_note,
                                "audio_seconds": round(audio_dur, 1),
                                "video_seconds": round(vid_dur, 1)},
            "performance_prediction": {},  # {} until REAL analytics exist.
            "retention_analysis": {"hook_seconds": round(durations[0], 1)},
            "video_type": "short", "target_length": round(vid_dur),
            "created_at": _now(), "status": "ready",
            "video_file_path": mp4_path, "thumbnail_path": thumb_path,
            "files": {"script": os.path.join(run_dir, "script.txt"),
                      "voiceover": wav_path, "video": mp4_path,
                      "thumbnail": thumb_path},
        }
        with open(os.path.join(run_dir, "script.txt"), "w", encoding="utf-8") as f:
            f.write(f"TITLE: {title}\nTAGS: {', '.join(tags)}\n\n")
            for k in ("hook", "pain", "demo", "close"):
                f.write(f"[{k.upper()}]\n{sections[k]}\n\n")
        with open(os.path.join(run_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        conn = empire.get_db()
        try:
            empire.save_video_package(conn, meta)
        finally:
            conn.close()

        files = {k: f"/api/download/{job_id}/{k}" for k in ALLOWED_FILES}
        _job_update(job_id, status="ready", progress="100% — ready",
                    files=json.dumps(files))
    except Exception as exc:  # noqa: BLE001 — job failure must be reported, not crash the worker
        # Never include the groq key (or anything from the request body) in
        # the stored error. The exception text comes from our own code paths.
        msg = str(exc)[-500:]
        _job_update(job_id, status="failed", progress="failed", error=msg)
        print(f"[worker] job {job_id} FAILED: {msg}", file=sys.stderr)
    finally:
        job["groq_key"] = None  # drop the in-memory key as soon as the job ends


def _worker():
    while True:
        job = _job_queue.get()
        try:
            _job_update(job["job_id"], status="working", progress="0% — starting")
            _run_video_job(job)
        except Exception:  # noqa: BLE001 — worker must never die
            traceback.print_exc()
            _job_update(job["job_id"], status="failed",
                        progress="failed", error="worker error (see server log)")
        finally:
            _job_queue.task_done()


threading.Thread(target=_worker, daemon=True, name="video-worker").start()


# ---------------------------------------------------------------------------
# Sync endpoints — thin wrappers over empire.py (CLI stays the engine)
# ---------------------------------------------------------------------------
def _trends(n):
    """Fresh fetch when possible, else latest saved rows. Per-source status,
    never a faked source. Returns (items, sources, fresh)."""
    buf = io.StringIO()
    sources, fresh, items = {}, False, []
    try:
        with contextlib.redirect_stdout(buf):
            rc = empire.cmd_trend(SimpleNamespace(count=n))
        out = buf.getvalue()
        if rc == 0:
            for line in out.splitlines():
                m = re.match(r"\s{2}(\w+): (.+)", line)
                if m:
                    sources[m.group(1)] = m.group(2)
        # Read back exactly what the CLI just saved (latest run).
        conn = empire.get_db()
        try:
            rows = conn.execute(
                "SELECT keyword, source, score, url, fetched_at FROM trends "
                "ORDER BY fetched_at DESC, score DESC LIMIT ?", (n,)).fetchall()
            items = [{"topic": r["keyword"], "source": r["source"],
                      "score": r["score"], "url": r["url"] or None}
                     for r in rows]
        finally:
            conn.close()
        fresh = bool(items) and bool(sources) and any(
            str(v) == "ok" for v in sources.values())
    except Exception as exc:  # noqa: BLE001 — fall back to saved rows
        print(f"[trends] fresh fetch failed ({exc}); serving saved rows",
              file=sys.stderr)
        sources = {"fetch": f"error: {exc}"}
        fresh = False
    if not items:
        conn = empire.get_db()
        try:
            rows = conn.execute(
                "SELECT keyword, source, score, url, fetched_at FROM trends "
                "ORDER BY fetched_at DESC, score DESC LIMIT ?", (n,)).fetchall()
            items = [{"topic": r["keyword"], "source": r["source"],
                      "score": r["score"], "url": r["url"] or None}
                     for r in rows]
        finally:
            conn.close()
    return items, sources, fresh


def _campaign(product_id, angle, platforms, niche, audience):
    products = empire.load_products()
    product = products[product_id]
    niche = niche or product.get("niche", "")
    audience = audience or product.get("audience",
                                       "anyone looking for a gentle start")
    empire.check_copy(angle, "campaign angle")
    posts = []
    for p in platforms:
        post = empire.build_post(p, product, angle, niche, audience)
        _verify_post(post, product)
        posts.append(post)
    camp_id = empire.new_id("camp")
    camp = {
        "id": camp_id, "product_name": product["name"],
        "product_description": product["blurb"], "niche": niche,
        "target_audience": audience, "platforms": platforms,
        "posts_per_day": 1, "duration_days": 7,
        "generated_posts": posts,
        "campaign_metrics": {},  # {} until REAL analytics exist.
        "created_at": _now(), "status": "active",
    }
    run_dir = os.path.join(RUNS_DIR, camp_id)
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "campaign.json"), "w", encoding="utf-8") as f:
        json.dump(camp, f, indent=2)
    conn = empire.get_db()
    try:
        empire.save_campaign(conn, camp)
    finally:
        conn.close()
    return {"campaign_id": camp_id,
            "posts": [{"platform": p["platform"], "text": p["content"],
                       "chars": p["chars"], "cap": p["char_cap"],
                       "times_et": p["optimal_posting_times_et"]}
                      for p in posts]}


def _empire_plan(story, niche, audience):
    for text, where in ((story, "empire story"), (niche, "empire niche"),
                        (audience, "empire audience")):
        empire.check_copy(text, where)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = empire.cmd_empire(SimpleNamespace(story=story, niche=niche,
                                               audience=audience))
    out = buf.getvalue()
    if rc != 0:
        raise RuntimeError(f"empire plan failed: {out[-300:]}")
    m = re.search(r"Content empire (empire_[0-9a-f]+) saved", out)
    if not m:
        raise RuntimeError("empire plan ran but its id could not be read back")
    emp_id = m.group(1)
    with open(os.path.join(RUNS_DIR, emp_id, "empire.json"),
              encoding="utf-8") as f:
        plan = json.load(f)
    return {"empire_id": emp_id, "plan": plan}


def _dashboard():
    conn = empire.get_db()
    try:
        counts = {
            "videos": conn.execute("SELECT COUNT(*) c FROM video_packages").fetchone()["c"],
            "campaigns": conn.execute("SELECT COUNT(*) c FROM organic_campaigns").fetchone()["c"],
            "empires": conn.execute("SELECT COUNT(*) c FROM content_empires").fetchone()["c"],
            "trends": conn.execute("SELECT COUNT(*) c FROM trends").fetchone()["c"],
            "jobs": conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"]
                    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone() else 0,
        }
        videos = [dict(r) for r in conn.execute(
            "SELECT id, title, created_at, status FROM video_packages "
            "ORDER BY created_at DESC LIMIT 10").fetchall()]
        camps = [dict(r) for r in conn.execute(
            "SELECT id, product_name, product_name AS title, created_at FROM organic_campaigns "
            "ORDER BY created_at DESC LIMIT 10").fetchall()]
        trends = [dict(r) for r in conn.execute(
            "SELECT keyword AS topic, source, score, fetched_at FROM trends "
            "ORDER BY fetched_at DESC, score DESC LIMIT 15").fetchall()]
    finally:
        conn.close()
    return {"counts": counts, "recent_videos": videos,
            "recent_campaigns": camps, "recent_trends": trends}


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quiet, single-line access log
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    # -- helpers -------------------------------------------------------------
    def _send_json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status, message):
        self._send_json(status, {"error": message})

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            obj = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ValueError("request body is not valid JSON")
        if not isinstance(obj, dict):
            raise ValueError("request body must be a JSON object")
        return obj

    # -- routing ---------------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)
        try:
            if path == "/api/health":
                return self._send_json(200, {"ok": True})
            if path == "/api/products":
                with open(os.path.join(BASE, "products.json"),
                          encoding="utf-8") as f:
                    data = json.load(f)
                return self._send_json(200, {"store": data.get("store", STORE_URL),
                                             "products": data["products"]})
            if path == "/api/trends":
                try:
                    n = int(qs.get("n", ["12"])[0])
                except ValueError:
                    return self._send_error_json(400, "n must be an integer")
                n = max(1, min(n, 50))
                items, sources, fresh = _trends(n)
                return self._send_json(200, {"trends": items, "sources": sources,
                                             "fresh": fresh,
                                             "count": len(items)})
            if path == "/api/dashboard":
                return self._send_json(200, _dashboard())
            if path.startswith("/api/jobs/"):
                job_id = path[len("/api/jobs/"):]
                if not job_id or "/" in job_id:
                    return self._send_error_json(400, "bad job id")
                row = _job_get(job_id)
                if row is None:
                    return self._send_error_json(404, f"unknown job {job_id}")
                return self._send_json(200, _job_public(row))
            if path.startswith("/api/download/"):
                parts = path[len("/api/download/"):].split("/")
                if len(parts) != 2:
                    return self._send_error_json(400, "bad download path")
                job_id, name = parts
                if name not in ALLOWED_FILES:
                    return self._send_error_json(
                        404, "only video, script, thumbnail, voiceover may be downloaded")
                # Never serve arbitrary paths: filename is fixed by the
                # allowlist above and the job id must match a real job dir.
                if _job_get(job_id) is None and not os.path.isdir(
                        os.path.join(RUNS_DIR, job_id)):
                    return self._send_error_json(404, f"unknown job {job_id}")
                fpath = os.path.join(RUNS_DIR, job_id, ALLOWED_FILES[name])
                if not os.path.isfile(fpath):
                    return self._send_error_json(404, "file not ready yet")
                fname = ALLOWED_FILES[name]
                with open(fpath, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", MIME[fname])
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition",
                                 f'attachment; filename="{job_id}-{fname}"')
                self.end_headers()
                self.wfile.write(body)
                return
            if path in ("/", "/index.html"):
                index = os.path.join(STATIC_DIR, "index.html")
                if os.path.isfile(index):
                    with open(index, "rb") as f:
                        body = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                return self._send_json(200, {"ok": True,
                    "service": "Marketing Empire API",
                    "docs": "GET /api/health, /api/products, /api/trends, "
                            "/api/dashboard; POST /api/video, /api/campaign, "
                            "/api/empire"})
            if path.startswith("/static/") or (
                    path.startswith("/") and "/" not in path[1:]
                    and os.path.isfile(os.path.join(STATIC_DIR, path[1:]))):
                # Read-only convenience: serve the sibling frontend's files,
                # both under /static/ and at root (index.html references its
                # siblings relatively, so /app.js and /style.css must work).
                rel = path[len("/static/"):] if path.startswith("/static/") else path[1:]
                if ".." in rel or rel.startswith("/"):
                    return self._send_error_json(400, "bad static path")
                fpath = os.path.join(STATIC_DIR, rel)
                if not os.path.isfile(fpath):
                    return self._send_error_json(404, "static file not found")
                ctype = ("text/css" if fpath.endswith(".css")
                         else "application/javascript" if fpath.endswith(".js")
                         else "text/html; charset=utf-8" if fpath.endswith(".html")
                         else "application/octet-stream")
                with open(fpath, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            return self._send_error_json(404, "unknown route")
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            return self._send_error_json(500, f"server error: {exc}"[:500])

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/video":
                body = self._read_json()
                product = (body.get("product") or "").strip()
                topic = (body.get("topic") or "").strip()
                if not product or not topic:
                    return self._send_error_json(
                        400, "product and topic are required")
                products = empire.load_products()
                if product not in products:
                    return self._send_error_json(
                        400, f"unknown product {product!r}; "
                             f"available: {', '.join(products)}")
                empire.check_copy(topic, "video topic")
                job_id = empire.new_id("vid")
                _job_create(job_id, "video", product, topic)
                # groq_key travels in memory only: queued with the job dict,
                # never written to the DB (see _job_create — no key column),
                # never logged, cleared in _run_video_job's finally block.
                _job_queue.put({"job_id": job_id, "product": product,
                                "topic": topic,
                                "groq_key": (body.get("groq_key") or None)})
                return self._send_json(202, {"job_id": job_id})
            if path == "/api/campaign":
                body = self._read_json()
                product = (body.get("product") or "").strip()
                angle = (body.get("angle") or "").strip()
                platforms = body.get("platforms") or []
                if not product or not angle or not platforms:
                    return self._send_error_json(
                        400, "product, angle and platforms[] are required")
                if not isinstance(platforms, list):
                    return self._send_error_json(400, "platforms must be a list")
                platforms = [str(p).strip().lower() for p in platforms if str(p).strip()]
                products = empire.load_products()
                if product not in products:
                    return self._send_error_json(
                        400, f"unknown product {product!r}")
                bad = [p for p in platforms if p not in empire.PLATFORMS]
                if bad:
                    return self._send_error_json(
                        400, f"unknown platform(s): {bad}; available: "
                             f"{', '.join(empire.PLATFORMS)}")
                try:
                    result = _campaign(product, angle, platforms,
                                       body.get("niche") or "",
                                       body.get("audience") or "")
                except ValueError as exc:
                    return self._send_error_json(400, f"BLOCKED: {exc}")
                return self._send_json(200, result)
            if path == "/api/empire":
                body = self._read_json()
                story = (body.get("story") or "").strip()
                niche = (body.get("niche") or "").strip()
                audience = (body.get("audience") or "").strip()
                if not story or not niche or not audience:
                    return self._send_error_json(
                        400, "story, niche and audience are required")
                try:
                    result = _empire_plan(story, niche, audience)
                except ValueError as exc:
                    return self._send_error_json(400, f"BLOCKED: {exc}")
                return self._send_json(200, result)
            return self._send_error_json(404, "unknown route")
        except ValueError as exc:
            return self._send_error_json(400, str(exc))
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            return self._send_error_json(500, f"server error: {exc}"[:500])

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()


def main():
    # Create the jobs table up front so /api/dashboard works immediately.
    _db().close()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Marketing Empire API listening on http://{HOST}:{PORT}")
    print("  GET  /api/health /api/products /api/trends /api/dashboard")
    print("  POST /api/video (202 + job_id)  GET /api/jobs/<id>")
    print("  GET  /api/download/<job_id>/<video|script|thumbnail|voiceover>")
    print("  POST /api/campaign  POST /api/empire")
    print("  Engine: empire.py (imported, not copied). Video worker: 1 thread, in order.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")


if __name__ == "__main__":
    main()
