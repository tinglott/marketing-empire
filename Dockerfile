# syntax=docker/dockerfile:1
# Marketing Empire — Render Free Docker backend.
#
# Build context: the marketing-empire-build/ directory (this file lives at
# its root). Nothing outside that directory is copied in.
#   docker build -t marketing-empire .
#   docker run -e PORT=8000 -p 8000:8000 marketing-empire
# On Render: create a Free "Web Service" from the repo, Environment: Docker,
# Root Directory: the directory holding this file. Render sets PORT at runtime;
# no card, no secret, no key is needed for the build or the run.
#
# What runs here: web/server/server.py (stdlib http.server) importing the CLI
# engine empire.py — the same code proven on the bench (video job renders in
# ~2 min: Kokoro TTS + ffmpeg). The frontend (web/static/) is served from
# here too for single-service testing; the recommended split puts the
# frontend on GitHub Pages and points its API_BASE at this service's URL.
#
# KNOWN UNKNOWNS (decided only by the live Render deploy, see HOSTING.md):
# - Render Free gives 512 MB RAM. Kokoro + torch has NOT been proven to fit.
#   If the container OOMs on the first live render, video stays a bench job.
# - Render Free has no persistent disk: runs/ and empire.db vanish on
#   restart. The API answers 404 honestly in that case; it never invents files.
# - The container sleeps after 15 min idle on Render Free; first request
#   after a quiet spell waits ~30-60 s for wake.
#
# Provenance note: kokoro_tts.py is a byte-identical vendored copy of the
# house VoiceForge wrapper (~/workspace/your_files/voiceforge-studio/
# kokoro_tts.py, sha256 ba67134c8e61588863ac7568de73e35543fcca585aa1eb5a76ba51675533cfb0).
# It is copied, not modified, so the Docker image stays self-contained: the
# bench's tts_helper.py inserts the VoiceForge directory into sys.path, but
# that directory does not exist in the image — the script's own directory
# (/app) is sys.path[0], so the vendored copy next to tts_helper.py resolves.
# If VoiceForge's wrapper ever changes, re-copy it and update the sha above.

FROM python:3.12-slim

# Keep the image lean and the logs unbuffered; put the Hugging Face cache
# inside /app so the pre-downloaded Kokoro model is a visible image layer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/hf-cache \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# ffmpeg (video assembly + ffprobe) and the fonts the caption cards use.
# empire.py tries DejaVu first, then Liberation, then PIL's built-in font.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# torch CPU-only FIRST. PyPI's default torch wheel is the multi-GB CUDA build;
# this service is CPU-only, so torch comes from PyTorch's CPU index.
# (requirements.txt also pins torch==2.14.1; pip sees it already satisfied
# and skips re-installing it from PyPI — verified with the `packaging`
# specifier rules on the bench.)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.14.1 \
    && pip install --no-cache-dir -r /app/requirements.txt

# The app: CLI engine + TTS helper + vendored VoiceForge wrapper + products,
# the backend server, and the static frontend.
COPY empire.py tts_helper.py kokoro_tts.py products.json /app/
COPY web/server/server.py /app/web/server/server.py
COPY web/static/ /app/web/static/

# Pre-download the Kokoro-82M model (~315 MB on disk) at BUILD time, so the
# first affiliate video never waits on a download — and so a missing model
# fails the build loudly instead of failing a job at runtime. The espeak-ng
# library ships inside the espeakng-loader wheel; nothing else downloads.
# HF_HOME above puts the cache at /app/hf-cache inside the image.
RUN python -c "import kokoro_tts; kokoro_tts.synthesize('Marketing Empire warm-up.', voice='af_heart'); print('Kokoro warm-up OK')"

WORKDIR /app/web/server

# Render routes to $PORT (set by Render at runtime, overriding the ENV above).
EXPOSE 8000

# Same command as the bench: `python3 server.py` from web/server/.
CMD ["python3", "server.py"]
