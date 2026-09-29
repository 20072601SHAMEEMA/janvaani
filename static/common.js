// Shared helpers for JanVaani pages
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => Number(n).toLocaleString("en-IN");

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

// Minimal, safe Markdown (escape first, then bold/italic/bullets/paragraphs)
function md(src) {
  const lines = esc(src).split(/\r?\n/);
  let html = "", inList = false;
  const inline = (t) => t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/(^|\W)_(.+?)_(\W|$)/g, "$1<em>$2</em>$3")
    .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  for (const raw of lines) {
    const l = raw.trim();
    const m = l.match(/^[-*•]\s+(.*)/);
    if (m) { if (!inList) { html += "<ul>"; inList = true; } html += `<li>${inline(m[1])}</li>`; continue; }
    if (inList) { html += "</ul>"; inList = false; }
    if (!l) continue;
    const h = l.match(/^#{1,4}\s+(.*)/);
    html += h ? `<p><strong>${inline(h[1])}</strong></p>` : `<p>${inline(l)}</p>`;
  }
  if (inList) html += "</ul>";
  return html;
}

function ago(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  if (s < 86400) return Math.floor(s / 3600) + "h ago";
  return Math.floor(s / 86400) + "d ago";
}

function setAiBadge(mode) {
  const b = document.getElementById("aiBadge");
  if (!b) return;
  b.classList.toggle("live", mode === "gemini");
  b.lastElementChild.textContent = mode === "gemini" ? "Gemini live" : "Offline demo mode";
  b.title = mode === "gemini" ? "Requests are analysed by Google Gemini" : "Set GEMINI_API_KEY to enable Gemini";
}
