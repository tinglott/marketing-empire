# Marketing Empire — Hosting verdict (Nov 8, 2026)

Bench research by the backend agent. **Nothing here is deployed.** Ting
reviews before any public deploy. Every claim below is marked
**verified** (read in an official doc or measured on this bench this
session), **secondary** (a reputable summary, not the official doc), or
**assumed / not verified** (an inference — do not build on it without a
live test).

## Verdict in one paragraph

**Recommended free route: split hosting.**

- **Frontend** (`web/static/`) on **GitHub Pages** — free, static-only,
  proven for exactly this job.
- **Backend** (`web/server/server.py`) on **Render Free** as a Docker web
  service — the only free host found that allows a long-running Python
  process + a Dockerfile (so ffmpeg + Kokoro can be installed) + a
  background worker, with no card required.
- **Video renders as a queued job** (already built into the API):
  POST returns a `job_id` at once; the worker renders in order; the
  affiliate polls `GET /api/jobs/<id>` and downloads when `ready`.
  Instant features (trends / script / campaign / empire plan) are served
  live. This matches the house render rhythm: create today,
  harvest tomorrow.

**The one honest unknown: Render's free tier gives 512 MB RAM, and
Kokoro + torch has NOT been proven to fit in 512 MB.** The bench venv is
6.0 GB on disk (torch alone 1.2 GB, Hugging Face cache 1.9 GB). That is a
disk figure, not a RAM figure — render-time RAM was not measured this
session. Before anyone promises affiliates video rendering on Render,
someone must deploy the Docker image there and run one real video job
end to end. If it OOMs, the fallback is: instant features live on
Render/PythonAnywhere, video stays a bench job (or HF PRO at $9/mo —
a Ting decision, not a recommendation under the $0 rule).

## Per-host findings

### GitHub Pages — frontend only. VERDICT: use for the static site.

- Static files only. No server-side code of any kind (no Python, no
  Node, no database, no env vars at runtime, no background jobs).
  **Verified** in multiple 2026 summaries of GitHub's own docs; the
  official docs page itself was not opened this session (**secondary**).
- Limits: published site ≤ 1 GB, soft bandwidth 100 GB/month, ~10 builds
  per hour (**secondary**).
- Usage policy: GitHub says Pages is "not intended for or allowed to be
  used as a free web-hosting service to run your online business,
  e-commerce site, or any other website that is primarily directed at
  either facilitating commercial transactions or providing commercial
  software as a service (SaaS)" (**secondary** — quoted from summaries
  of the policy). Our frontend is a free tool page for affiliates, not a
  checkout — but this is a real policy line Ting should know, and a
  reason the *store* itself never lives here.
- **Can it do:** serve `web/static/` (already built by the sibling
  agent) at `tinglott.github.io/...` or a custom domain.
- **Cannot do:** any API endpoint, any video render, any job queue, any
  secret (a Groq key in browser JS would be public).

### Vercel Hobby (free) — instant API only, NOT video. VERDICT: backup for the frontend + instant endpoints.

- **Verified** (Vercel official docs, via examples.vercel.com mirror,
  last updated 2026-08-24): with Fluid compute (default for new
  projects since Apr 23, 2025), Hobby functions run **300 s default and
  300 s maximum**, 2 GB / 1 vCPU, and cannot be extended. Older
  third-party pages still saying "10 seconds" describe the pre-Fluid
  limits — outdated.
- **Verified** (same docs): no persistent disk; functions are
  short-lived per-request invocations — there is no background worker
  process on Hobby. A queued video job has nowhere to run.
- Hobby is licensed for **non-commercial personal use only**
  (**secondary**, multiple 2026 sources). Marketing Empire serves
  Ting's business affiliates — that alone makes Hobby the wrong home
  for the business backend, even before the technical limits.
- Hobby monthly caps include ~4 h active CPU and 1 M invocations
  (**secondary**); exceeding a cap can pause the feature for ~30 days.
- Kokoro: the bench Kokoro venv is **6.0 GB on disk (measured)**,
  torch alone 1.2 GB — orders of magnitude above any serverless
  function size limit. Kokoro cannot be bundled into a Vercel function.
  ffmpeg is not part of the Vercel Python runtime (**assumed** — not
  verified against Vercel's runtime docs this session; the size argument
  already rules it out).
- **Can it do:** serve the static frontend, and serve the instant
  endpoints (`/api/trends`, `/api/campaign`, `/api/empire`) — all fast,
  well inside 300 s.
- **Cannot do:** video rendering (Kokoro + ffmpeg), background job
  queue, persistent `runs/` files, commercial use under Hobby terms.
- Note for Ting: his `tinglott@gmail.com` Vercel account is STOPPED by
  his own word (Oct 31) — any Vercel use would be the samanlott / zigg1
  account, and only if he reverses nothing. Not needed for the
  recommended route.

### PythonAnywhere Beginner (free) — instant API only, maybe. VERDICT: fallback, not the video host.

- **Verified-ish** (multiple 2026 pricing summaries + PA's own Jan 2026
  blog): Beginner = 1 web app at `<username>.pythonanywhere.com`,
  **100 CPU-seconds/day**, **512 MB storage**, no custom domain,
  outbound internet restricted to an allowlist.
- **Verified** (PA blog, Jan 2026): from Jan 2026, scheduled tasks and
  MySQL moved to the paid Developer tier for new free accounts, and
  **unused free web apps expire after 1 month** (was 3 months).
  Community support only for free accounts.
- ffmpeg: a PythonAnywhere staff forum reply (Jan 2021) says "ffmpeg is
  installed on PythonAnywhere… for all users and is on the path."
  **Secondary, and 5 years old** — the current system image ("haggis")
  was not verified this session. Treat as "probably present, must be
  checked on the live account."
- Kokoro: **assumed to fail** — installing torch + the Kokoro model
  into 512 MB of storage is implausible (bench venv alone is 6.0 GB),
  and no free-tier GPU/CPU headroom exists for it. Not verified by
  attempting it; nobody should attempt it without Ting's activation.
- CPU budget: one bench video render takes ~1–2 min of mostly-CPU work
  (Kokoro TTS + ffmpeg). At 100 CPU-sec/day that is roughly **one video
  per day, if nothing else runs** — an estimate, not a measurement.
  The instant endpoints (trend fetch, campaign text) cost seconds.
- Account note: an account under **tinglott exists but is NOT
  activated**. Activation needs Ting's own tap. **Do NOT attempt it
  from the bench** (per the task brief and the house rule: Ting does
  identity steps himself).
- **Can it do:** host this stdlib server (WSGI-shaped) for instant
  features; no sleep (unlike Render), real 512 MB disk so SQLite
  survives restarts.
- **Cannot do (honestly):** video rendering at any useful volume;
  background worker on free tier; custom domain; arbitrary outbound
  calls (Groq polish + trend RSS must be on the allowlist — not
  verified).

### Hugging Face Spaces — technically capable, NOT free for this. VERDICT: blocked by PRO.

- **Verified** (official HF docs, read Nov 8, 2026,
  huggingface.co/docs/hub/spaces-overview): "Static Spaces are free
  for everyone. Gradio and Docker Spaces run on compute and require a
  paid plan to create: PRO for personal accounts, Team or Enterprise
  for organizations. Free personal accounts in good standing can still
  host up to 2 Gradio Spaces running on ZeroGPU."
- **Verified** (same docs): CPU Basic hardware is 2 vCPU / 16 GB RAM /
  50 GB **ephemeral** disk, $0/hour — but creating a compute Space on
  it requires the paid plan. Free hardware "will go to sleep and stop
  executing after a period of time if unused."
- **Secondary** (multiple Sep–Oct 2026 reports): creating a Docker
  Space on a free account now fails with `402 Payment Required`;
  PRO is $9/month (price **not verified** on HF's pricing page this
  session).
- A Docker Space *could* apt-install ffmpeg and run Kokoro on 16 GB
  RAM (the pattern is proven in other public Docker Spaces), and its
  disk is ephemeral, so finished videos would still need prompt
  download. But the $9/mo gate means it is **not a $0 route**, and
  ZeroGPU (the free exception) is Gradio-only — our server is not a
  Gradio app.
- **Can it do:** everything, technically — if someone pays PRO.
- **Cannot do:** free Docker hosting. Do not present HF Spaces as the
  free video host.

### Render Free (extra host, researched because the four named hosts all fail video) — VERDICT: recommended backend.

- **Secondary** (Render docs as summarised Oct 2026 + multiple 2026
  comparisons): Free web service = **750 instance-hours/month**,
  **512 MB RAM / 0.1 CPU**, sleeps after **15 min idle**, wakes in
  ~30–60 s on the next request. No persistent disk (files written at
  runtime vanish on redeploy/restart). Render's own docs say "Do not
  use them for production applications." No card required to create a
  free service. No non-commercial-use ban was found in the sources
  read (**not verified** against Render's ToS this session).
- Dockerfile support is first-class: ffmpeg (`apt-get install ffmpeg`)
  and Python deps install at build time — this is the only free route
  where the *whole* bench stack (Python + ffmpeg + Kokoro + PIL) can
  plausibly be reproduced.
- **Can it do:** run this exact server (long-lived process, worker
  thread, SQLite, job queue) behind a stable public HTTPS URL.
- **Cannot do / risks (honest):**
  - **512 MB RAM vs Kokoro is UNPROVEN** (see verdict). One live test
    render decides it.
  - Sleeps after 15 idle min: first visitor after a quiet spell waits
    ~1 min; a video job submitted while asleep starts after wake.
  - Ephemeral disk: a finished `video.mp4` must be downloaded
    promptly; a restart wipes `runs/` and the SQLite DB unless
    persistent storage is added (paid) or files are pushed elsewhere.
    Job rows survive only as long as the disk does — the API reports
    `failed`/`not found` honestly if a restart wipes them; it never
    invents a file.
  - 750 h/month covers one always-on service (a month is 744 h), but
    only just; a second free service would share the pool.
  - Free Postgres expires (30–90 days per sources) — we use SQLite,
    so this does not apply.

## What Ting must do himself (per step)

| Step | Who | What |
|---|---|---|
| GitHub Pages frontend | Ting (or Ziggy with his go-word) | Publish the repo / enable Pages; nothing secret needed. |
| Render backend | Ting | Create the Render account (GitHub sign-in), create the free web service from the repo, confirm the deploy. No card. Then one live test video render to settle the 512 MB question. |
| PythonAnywhere (fallback only) | **Ting only** | Activate the existing tinglott account himself (email tap). Nobody on the bench touches activation. |
| Hugging Face PRO | Ting decides | Only if the Render RAM test fails and he wants HF instead: $9/mo (unverified price) — his call, not assumed. |
| Vercel | Nobody | Not used under the recommended route. tinglott@gmail.com Vercel stays stopped. |
| Groq keys | Each affiliate | Their OWN free key at console.groq.com, pasted per video request. Never Ting's key, never stored. |

## What the bench build can / cannot prove

- **Proven on the bench (this session):** the stdlib server runs;
  every endpoint below returns real data; a real video job renders
  end-to-end (Kokoro + ffmpeg) and its files download. See
  `SMOKE-TEST.md` in this directory for status codes and outputs.
- **Cannot be proven from the bench:** any host's live limits (RAM,
  sleep, ffmpeg presence, allowlists, PRO gating). Those are claims
  from docs/summaries above, marked as such. The Render 512 MB
  question is decided only by a live deploy + one real render.
- **Not attempted, by design:** no deploy, no publish, no account
  activation (PythonAnywhere), no tunnel (ngrok and friends are proven
  impossible from this bench), no purchase, no key use.

## Recommended architecture (for the deploy step, when Ting says go)

```
Affiliate browser
  → GitHub Pages (web/static/ — HTML/CSS/JS, house palette)
  → Render Free Docker (web/server/server.py + Dockerfile + requirements)
      ├─ GET  /api/products /api/trends /api/dashboard   (live, fast)
      ├─ POST /api/campaign /api/empire                  (live, fast)
      ├─ POST /api/video → {job_id}  (202, queued)
      ├─ GET  /api/jobs/<id>          (queued/working/ready/failed)
      └─ GET  /api/download/<id>/<file> (video/script/thumbnail/voiceover)
```

Still to build before deploy (not this agent's job, flagged for the
parent): a `Dockerfile` + `requirements.txt` for Render (python:3.12
base, `apt-get install ffmpeg`, pip install kokoro + torch CPU +
Pillow + trend-pulse, copy empire.py/products.json/server.py), and a
note that the Kokoro model (~300 MB-class download, exact size
unverified) must be fetched at build time or first boot, not baked
into the repo. The server already serves `../static/` at `/` and
`/static/` for single-service testing, but the recommended split keeps
the frontend on Pages.

## Sources (checked Nov 8, 2026)

- Vercel Functions limits / max duration (official docs mirror,
  updated 2026-08-24): Hobby Fluid 300 s default/max, 2 GB/1 vCPU.
- Hugging Face Spaces Overview (official docs, read Nov 8, 2026):
  Gradio/Docker require PRO; static free; CPU Basic 2 vCPU/16 GB,
  50 GB ephemeral; free hardware sleeps.
- PythonAnywhere: Jan 2026 blog (free-account changes: scheduled
  tasks/MySQL to Developer, unused apps expire after 1 month);
  staff forum Jan 2021 ("ffmpeg is installed for all users");
  2026 pricing summaries (100 CPU-sec/day, 512 MB, 1 app).
- GitHub Pages limits + usage policy (2026 summaries of GitHub docs:
  1 GB site, 100 GB/mo soft bandwidth, static only, no commercial
  SaaS use).
- Render free tier (Oct 2026 docs summaries + 2026 comparisons:
  750 h/mo, 15-min sleep, 512 MB/0.1 CPU, no persistent disk,
  "do not use for production", Dockerfile support, no card).
- Bench measurements: Kokoro venv 6.0 GB on disk, torch 1.2 GB,
  Hugging Face cache 1.9 GB (`du -sh`, Nov 8, 2026).
