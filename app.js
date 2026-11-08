/* Marketing Empire — static frontend (GitHub Pages build).
 *
 * API_BASE — SET AT DEPLOY: the PythonAnywhere backend URL. The page
 * lives on GitHub Pages (tinglott.github.io) and the backend lives on
 * PythonAnywhere, so this MUST be the backend's full URL — same-origin
 * ("") only works when the backend itself serves the page (bench
 * testing). No trailing slash. Current value: the live backend once it
 * is deployed. If the backend is not up yet, the page falls back to the
 * saved product list and says so (see loadProducts / checkHealth).
 */
"use strict";

// DEPLOY: replace with the real PythonAnywhere web-app URL, e.g.
// "https://tinglott.pythonanywhere.com" — that is the account's default
// Beginner address (username tinglott). Keep the trailing slash off.
const API_BASE = "https://tinglott.pythonanywhere.com";

const SERVER_ERROR = "Could not reach the server — try again in a minute.";

/* Fallback copy of the 4 real products from products.json, used ONLY when
 * GET /api/products is unreachable. Prices/links copied verbatim. */
const FALLBACK_PRODUCTS = [
  {
    id: "naturally-radiant-day1",
    name: "Naturally Radiant: Day 1 Starter",
    price_text: "FREE",
    link: "https://tlott12.gumroad.com/l/peowl",
    blurb: "A free Day 1 starter from Naturally Radiant — The Complete Guide to Organic Skincare. Inside: a skin-type finder, the Honey Oat Cleansing Scrub recipe, and the Day 1 routine from the 5-Day Natural Skincare Challenge.",
    niche: "natural skincare",
    audience: "anyone starting a simple natural skincare routine"
  },
  {
    id: "luna",
    name: "Luna — AI Receptionist",
    price_text: "$149/month in the US, $59/month anywhere else — 14-day free trial, no card required",
    link: "https://shop.artistrystore.com",
    blurb: "Luna is Ting Lott's AI receptionist for small businesses: answers missed calls in a polite, professional voice, books appointments on the business's real Google Calendar, and calls people back during business hours.",
    niche: "small business AI",
    audience: "small business owners who miss calls"
  },
  {
    id: "sleep-sanctuary",
    name: "Sleep Sanctuary",
    price_text: "$29.99",
    link: "https://tlott12.gumroad.com/l/hwkanb",
    blurb: "A nurse-designed sleep program — calming audio and a gentle nightly rhythm to help you wind down.",
    niche: "sleep",
    audience: "adults who struggle to fall asleep and stay asleep"
  },
  {
    id: "sacred-cycles",
    name: "Sacred Cycles",
    price_text: "$97",
    link: "https://shop.artistrystore.com",
    blurb: "Sacred Cycles is a faith-rooted renewal program: a gentle rhythm of reflection, rest, and small steps back to balance.",
    niche: "faith and renewal",
    audience: "women, clinics and coaches looking for a faith-rooted renewal rhythm"
  }
];

const STORE_URL = "https://shop.artistrystore.com";

let products = [];          // current product list (API or fallback)

/* ---------- helpers ---------- */

function $(id) { return document.getElementById(id); }

function esc(text) {
  return String(text == null ? "" : text)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/* The one fetch helper every API call goes through. Network failure or a
 * non-JSON error body becomes the same plain-English message. */
async function apiFetch(path, options) {
  let res;
  try {
    res = await fetch(API_BASE + path, options);
  } catch (err) {
    throw new Error(SERVER_ERROR);
  }
  let data = null;
  try { data = await res.json(); } catch (err) { /* body may be empty */ }
  if (!res.ok) {
    const msg = (data && (data.error || data.detail || data.message)) || SERVER_ERROR;
    throw new Error(String(msg));
  }
  return data;
}

function productById(id) {
  return products.find(function (p) { return p.id === id; }) || null;
}

function fillProductSelect(select, list) {
  select.innerHTML = "";
  list.forEach(function (p) {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.name + " — " + p.price_text;
    select.appendChild(opt);
  });
}

function showProductDetail(selectId, detailId) {
  const p = productById($(selectId).value);
  if (!p) { $(detailId).textContent = ""; return; }
  $(detailId).innerHTML =
    "<strong>" + esc(p.name) + "</strong> · " + esc(p.price_text) +
    "<br>" + esc(p.blurb || "") +
    "<br><a href=\"" + esc(p.link) + "\" target=\"_blank\" rel=\"noopener\">" + esc(p.link) + "</a>";
}

/* ---------- products ---------- */

async function loadProducts() {
  try {
    const data = await apiFetch("/api/products");
    if (data && Array.isArray(data.products) && data.products.length > 0) {
      products = data.products;
    } else {
      throw new Error("empty");
    }
  } catch (err) {
    // API unreachable (or empty): use the hard-coded copy and SAY SO
    // via the server-status line (checkHealth). Prices may be out of
    // date — the store is the source of truth.
    products = FALLBACK_PRODUCTS.slice();
  }
  fillProductSelect($("campaign-product"), products);
  showProductDetail("campaign-product", "campaign-product-detail");
}

/* ---------- server status ---------- */

async function checkHealth() {
  const el = $("server-status");
  try {
    const data = await apiFetch("/api/health");
    if (data && data.ok) {
      el.textContent = "Server: connected ✓";
      el.classList.remove("bad");
    } else {
      el.textContent = "Server: answered, but not OK — some features may not work.";
      el.classList.add("bad");
    }
  } catch (err) {
    el.textContent = "Server: not reached — the page still shows the saved product list, but making posts and trends needs the server.";
    el.classList.add("bad");
  }
}

/* ---------- 1. SAMPLE VIDEOS ---------- */

/* Videos are made on request, not on this page. The sample videos
   in section 1 of index.html are plain <video> tags — no JavaScript
   makes videos here, and there is no make-video button to wire up.
   (The live video maker still runs on the bench: empire.py video.) */

/* ---------- 2. MAKE POSTS (campaign) ---------- */

function copyText(text, btn) {
  function done() { btn.textContent = "Copied ✓"; setTimeout(function () { btn.textContent = "Copy"; }, 2000); }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, btn, done); });
  } else {
    fallbackCopy(text, btn, done);
  }
}

function fallbackCopy(text, btn, done) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed"; ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand("copy"); done(); }
  catch (err) { btn.textContent = "Copy failed — select the text by hand"; }
  document.body.removeChild(ta);
}

async function makeCampaign() {
  const productId = $("campaign-product").value;
  const angle = $("campaign-angle").value.trim();
  const statusEl = $("campaign-status");
  const btn = $("make-posts-btn");

  const platforms = [];
  document.querySelectorAll("#campaign-section .platforms input[type=checkbox]:checked")
    .forEach(function (cb) { platforms.push(cb.value); });

  if (!productId) { statusEl.innerHTML = "<p class=\"error\">Please pick a product first.</p>"; return; }
  if (!angle) { statusEl.innerHTML = "<p class=\"error\">Please write your message (angle) first.</p>"; return; }
  if (platforms.length === 0) { statusEl.innerHTML = "<p class=\"error\">Please pick at least one platform.</p>"; return; }

  btn.disabled = true;
  $("campaign-posts").innerHTML = "";
  statusEl.innerHTML = "<p>Making your posts…</p>";

  const product = productById(productId);
  const body = { product: productId, angle: angle, platforms: platforms };
  if (product) {
    if (product.niche) body.niche = product.niche;
    if (product.audience) body.audience = product.audience;
  }

  try {
    const data = await apiFetch("/api/campaign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const posts = (data && data.posts) || [];
    if (posts.length === 0) {
      statusEl.innerHTML = "<p class=\"error\">The server returned no posts. Please try again.</p>";
    } else {
      statusEl.innerHTML = "<p class=\"ok\">Done — " + posts.length + " post" + (posts.length > 1 ? "s" : "") +
        " ready. Each one carries #ad and the full link. Read each one before you publish it.</p>";
      const wrap = $("campaign-posts");
      posts.forEach(function (post, i) {
        const card = document.createElement("div");
        card.className = "post-card";
        const platform = (post.platform || "Post").toString();
        const chars = (post.chars != null) ? post.chars : (post.text || "").length;
        const cap = (post.cap != null) ? post.cap : "?";
        card.innerHTML =
          "<h3>" + esc(platform.charAt(0).toUpperCase() + platform.slice(1)) + "</h3>" +
          "<p class=\"meta\">" + esc(chars) + " of " + esc(cap) + " characters" +
          (post.chars != null && post.cap != null && post.chars > post.cap
            ? " — over the limit, please shorten before posting" : "") + "</p>" +
          "<p class=\"post-text\">" + esc(post.text || "") + "</p>";
        const copyBtn = document.createElement("button");
        copyBtn.type = "button";
        copyBtn.className = "copy-btn";
        copyBtn.textContent = "Copy";
        copyBtn.addEventListener("click", function () { copyText(post.text || "", copyBtn); });
        card.appendChild(copyBtn);
        wrap.appendChild(card);
      });
    }
  } catch (err) {
    statusEl.innerHTML = "<p class=\"error\">" + esc(err.message) + "</p>";
  }
  btn.disabled = false;
}

/* ---------- 3. TRENDING NOW ---------- */

async function showTrends() {
  const statusEl = $("trends-status");
  const listEl = $("trends-list");
  const sourcesEl = $("trends-sources");
  const btn = $("show-trends-btn");
  btn.disabled = true;
  listEl.innerHTML = "";
  sourcesEl.textContent = "";
  statusEl.innerHTML = "<p>Checking what is trending…</p>";

  try {
    const data = await apiFetch("/api/trends?n=12");
    const trends = (data && data.trends) || [];
    if (trends.length === 0) {
      statusEl.innerHTML = "<p>No trending topics right now — every source returned nothing. Please try again later.</p>";
    } else {
      statusEl.innerHTML = "<p class=\"ok\">" + trends.length + " trending topic" + (trends.length > 1 ? "s" : "") + ":</p>";
      trends.forEach(function (t) {
        const li = document.createElement("li");
        let html = "<strong>" + esc(t.topic || "") + "</strong> " +
          "<span class=\"src\">(" + esc(t.source || "unknown source") + ")" +
          (t.score != null ? " · score <span class=\"score\">" + esc(t.score) + "</span>" : "") + "</span>";
        if (t.url) html += " <a href=\"" + esc(t.url) + "\" target=\"_blank\" rel=\"noopener\">source</a>";
        li.innerHTML = html;
        listEl.appendChild(li);
      });
    }
    // Report per-source honestly: name any source that returned nothing.
    const sources = (data && data.sources) || {};
    const names = Object.keys(sources);
    if (names.length > 0) {
      const parts = names.map(function (name) {
        const v = sources[name];
        const count = (v && typeof v === "object" && v.count != null) ? v.count
          : (typeof v === "number" ? v : null);
        if (count === 0) return name + ": returned nothing";
        if (count != null) return name + ": " + count + " topic" + (count === 1 ? "" : "s");
        return name + ": " + String(v);
      });
      sourcesEl.textContent = "Sources — " + parts.join(" · ");
    }
  } catch (err) {
    statusEl.innerHTML = "<p class=\"error\">" + esc(err.message) + "</p>";
  }
  btn.disabled = false;
}

/* ---------- 4. MY WORK (dashboard) ---------- */

function workItemHtml(item, kind) {
  const title = item.title || item.name || item.product || item.id || "(no title)";
  const when = item.created || item.created_at || item.date || "";
  let links = "";
  if (kind === "video" && item.id) {
    links = "<span class=\"links\">" +
      "<a href=\"" + esc(API_BASE + "/api/download/" + encodeURIComponent(item.id) + "/video") + "\" target=\"_blank\" rel=\"noopener\">Video</a>" +
      "<a href=\"" + esc(API_BASE + "/api/download/" + encodeURIComponent(item.id) + "/script") + "\" target=\"_blank\" rel=\"noopener\">Script</a>" +
      "<a href=\"" + esc(API_BASE + "/api/download/" + encodeURIComponent(item.id) + "/thumbnail") + "\" target=\"_blank\" rel=\"noopener\">Thumbnail</a>" +
      "</span>";
  }
  return "<li><strong>" + esc(title) + "</strong>" +
    (item.id ? " <span class=\"when\">" + esc(item.id) + "</span>" : "") +
    (when ? " <span class=\"when\">" + esc(when) + "</span>" : "") +
    (item.status ? " <span class=\"when\">" + esc(item.status) + "</span>" : "") +
    (links ? "<br>" + links : "") + "</li>";
}

async function loadDashboard() {
  const statusEl = $("dashboard-status");
  const btn = $("refresh-btn");
  btn.disabled = true;
  statusEl.innerHTML = "<p>Loading your work…</p>";

  try {
    const data = await apiFetch("/api/dashboard");
    const counts = (data && data.counts) || {};
    const c = function (k) { return (counts[k] != null) ? counts[k] : 0; };
    $("dashboard-counts").innerHTML =
      "<div class=\"count-box\"><span class=\"num\">" + esc(c("videos")) + "</span><span class=\"lbl\">Videos</span></div>" +
      "<div class=\"count-box\"><span class=\"num\">" + esc(c("campaigns")) + "</span><span class=\"lbl\">Campaigns</span></div>" +
      "<div class=\"count-box\"><span class=\"num\">" + esc(c("empires")) + "</span><span class=\"lbl\">Plans</span></div>" +
      "<div class=\"count-box\"><span class=\"num\">" + esc(c("trends")) + "</span><span class=\"lbl\">Trends</span></div>";
    statusEl.innerHTML = "";

    const videos = (data && data.recent_videos) || [];
    $("dashboard-videos").innerHTML = videos.length === 0
      ? "<p class=\"empty\">No videos made on this server yet — videos are made on request. See the samples at the top of the page.</p>"
      : "<ul class=\"work-list\">" + videos.map(function (v) { return workItemHtml(v, "video"); }).join("") + "</ul>";

    const campaigns = (data && data.recent_campaigns) || [];
    $("dashboard-campaigns").innerHTML = campaigns.length === 0
      ? "<p class=\"empty\">No campaigns yet — make your first posts above.</p>"
      : "<ul class=\"work-list\">" + campaigns.map(function (x) { return workItemHtml(x, "campaign"); }).join("") + "</ul>";

    const trends = (data && data.recent_trends) || [];
    $("dashboard-trends").innerHTML = trends.length === 0
      ? "<p class=\"empty\">No trends saved yet.</p>"
      : "<ul class=\"work-list\">" + trends.map(function (t) {
          return "<li><strong>" + esc(t.topic || "") + "</strong> <span class=\"when\">" +
            esc(t.source || "") + (t.score != null ? " · " + esc(t.score) : "") + "</span></li>";
        }).join("") + "</ul>";
  } catch (err) {
    statusEl.innerHTML = "<p class=\"error\">" + esc(err.message) + "</p>";
  }
  btn.disabled = false;
}

/* ---------- wire up ---------- */

$("campaign-product").addEventListener("change", function () { showProductDetail("campaign-product", "campaign-product-detail"); });
$("make-posts-btn").addEventListener("click", makeCampaign);
$("show-trends-btn").addEventListener("click", showTrends);
$("refresh-btn").addEventListener("click", loadDashboard);

loadProducts();
checkHealth();
loadDashboard();
