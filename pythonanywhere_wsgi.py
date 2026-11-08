#!/usr/bin/env python3
"""Marketing Empire — PythonAnywhere WSGI entry (instant endpoints ONLY).

This is the deployed half of the split (Nov 8, 2026):
  * Frontend: GitHub Pages (static web/static/), API_BASE points here.
  * Backend: this file on PythonAnywhere Beginner (free, no card).
  * Video: NOT here. Video jobs stay a bench job (Kokoro + ffmpeg need
    torch, which cannot fit PythonAnywhere's 512 MB disk). A POST to
    /api/video answers 404 with a plain message — it never invents a job.

PythonAnywhere free web apps are WSGI only: no http.server, no own web
server, no background thread. This file is the WSGI callable
``application``. It REUSES the bench server's functions — it does not
re-implement them:

  * server._trends / server._campaign / server._empire_plan /
    server._dashboard  — imported from web/server/server.py, the same
    code the bench smoke tests verified (SMOKE-TEST.md).
  * empire.build_post / empire.check_copy / empire.load_products —
    reached through those helpers; the CLI (empire.py) stays the engine.

CRITICAL: this module must import and run with NO torch / Kokoro /
trend-pulse / PIL installed. empire.py imports all of those LAZILY
(inside the functions that need them), and cmd_trend falls back to a
stdlib RSS fetch when trend-pulse is absent — so a bare-stdlib
interpreter is enough. Proven by the clean-venv test in
SPLIT-BUILD-REPORT.md (venv with stdlib only; every endpoint hit live).

One known side effect of importing server.py: it starts its video-worker
thread at module level. In this app the thread sits idle forever — there
is no /api/video route, so nothing is ever queued. Harmless, and
server.py is left untouched on purpose (the proven bench server is not
edited to serve this file).

CORS: the frontend lives on github.io, a different origin, so every
response carries Access-Control-Allow-Origin: * and OPTIONS preflights
answer 204 — the same policy as the bench server.

Deploy (see SPLIT-BUILD-REPORT.md for the full steps): copy the whole
build directory to the PythonAnywhere account, create a Beginner web
app (manual config, Python 3.12), point its WSGI file at this file, and
reload. No environment variables, no secrets, no keys are needed.
"""
from __future__ import annotations

import io
import json
import os
import sys
import traceback
from urllib.parse import parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
_SERVER_DIR = os.path.join(HERE, "web", "server")
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

import server  # noqa: E402  (bench server: helpers reused, worker thread idle)

VIDEO_OFF_MESSAGE = (
    "Videos are made on request, not on this server. "
    "Ask Ting in the ARTISY community, or visit "
    "https://shop.artistrystore.com — finished sample videos are on the "
    "front page."
)

CORS_HEADERS = [
    ("Access-Control-Allow-Origin", "*"),
    ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
    ("Access-Control-Allow-Headers", "Content-Type"),
]


def _respond(start_response, status, obj):
    """Send a JSON body (obj=None sends an empty body, e.g. 204)."""
    if obj is None:
        body = b""
    else:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"),
               ("Content-Length", str(len(body)))] + CORS_HEADERS
    start_response(status, headers)
    return [body]


def _read_json(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    raw = environ["wsgi.input"].read(length) if length > 0 else b""
    if not raw:
        return {}
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ValueError("request body is not valid JSON")
    if not isinstance(obj, dict):
        raise ValueError("request body must be a JSON object")
    return obj


def application(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/") or "/"
    query = parse_qs(environ.get("QUERY_STRING", ""))
    try:
        # CORS preflight (the Pages frontend is a different origin).
        if method == "OPTIONS":
            return _respond(start_response, "204 No Content", None)

        if method == "GET" and path == "/api/health":
            return _respond(start_response, "200 OK", {"ok": True})

        if method == "GET" and path == "/api/products":
            with open(os.path.join(HERE, "products.json"),
                      encoding="utf-8") as f:
                data = json.load(f)
            return _respond(start_response, "200 OK",
                            {"store": data.get("store", server.STORE_URL),
                             "products": data["products"]})

        if method == "GET" and path == "/api/trends":
            try:
                n = int(query.get("n", ["12"])[0])
            except ValueError:
                return _respond(start_response, "400 Bad Request",
                                {"error": "n must be an integer"})
            n = max(1, min(n, 50))
            items, sources, fresh = server._trends(n)
            return _respond(start_response, "200 OK",
                            {"trends": items, "sources": sources,
                             "fresh": fresh, "count": len(items)})

        if method == "GET" and path == "/api/dashboard":
            return _respond(start_response, "200 OK", server._dashboard())

        if method == "POST" and path == "/api/campaign":
            body = _read_json(environ)
            product = (body.get("product") or "").strip()
            angle = (body.get("angle") or "").strip()
            platforms = body.get("platforms") or []
            if not product or not angle or not platforms:
                return _respond(start_response, "400 Bad Request",
                                {"error": "product, angle and platforms[] are required"})
            if not isinstance(platforms, list):
                return _respond(start_response, "400 Bad Request",
                                {"error": "platforms must be a list"})
            platforms = [str(p).strip().lower() for p in platforms
                         if str(p).strip()]
            products = server.empire.load_products()
            if product not in products:
                return _respond(start_response, "400 Bad Request",
                                {"error": f"unknown product {product!r}"})
            bad = [p for p in platforms if p not in server.empire.PLATFORMS]
            if bad:
                return _respond(start_response, "400 Bad Request",
                                {"error": f"unknown platform(s): {bad}; available: "
                                          f"{', '.join(server.empire.PLATFORMS)}"})
            try:
                result = server._campaign(product, angle, platforms,
                                          body.get("niche") or "",
                                          body.get("audience") or "")
            except ValueError as exc:
                return _respond(start_response, "400 Bad Request",
                                {"error": f"BLOCKED: {exc}"})
            return _respond(start_response, "200 OK", result)

        if method == "POST" and path == "/api/empire":
            body = _read_json(environ)
            story = (body.get("story") or "").strip()
            niche = (body.get("niche") or "").strip()
            audience = (body.get("audience") or "").strip()
            if not story or not niche or not audience:
                return _respond(start_response, "400 Bad Request",
                                {"error": "story, niche and audience are required"})
            try:
                result = server._empire_plan(story, niche, audience)
            except ValueError as exc:
                return _respond(start_response, "400 Bad Request",
                                {"error": f"BLOCKED: {exc}"})
            return _respond(start_response, "200 OK", result)

        # Video is NOT served here — answer honestly, never invent a job.
        if method == "POST" and path == "/api/video":
            return _respond(start_response, "404 Not Found",
                            {"error": VIDEO_OFF_MESSAGE})
        if path.startswith("/api/jobs/") or path.startswith("/api/download/"):
            return _respond(start_response, "404 Not Found",
                            {"error": "Not available on this server. "
                                     + VIDEO_OFF_MESSAGE})

        return _respond(start_response, "404 Not Found",
                        {"error": "unknown route"})
    except ValueError as exc:
        return _respond(start_response, "400 Bad Request", {"error": str(exc)})
    except Exception as exc:  # noqa: BLE001 — a 500 must never leak a traceback
        traceback.print_exc()
        return _respond(start_response, "500 Internal Server Error",
                        {"error": f"server error: {exc}"[:500]})
