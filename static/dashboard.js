const COMP_COLORS = { demand: "var(--c-demand)", gap: "var(--c-gap)", reach: "var(--c-reach)" };
const COMP_LABELS = { demand: "Citizen demand", gap: "Gap (NFHS-5)", reach: "Population (Census 2011)" };
const EXAMPLES = [
  "Which 10 districts have the lowest sanitation coverage?",
  "Which districts in Bihar have the most urgent requests?",
  "How many requests came in each language?",
  "Compare average electricity coverage by state",
];

let META, map, layer, weights = {}, lastFeedTop = null;
const $ = (id) => document.getElementById(id);
const scoreColor = (s) => (s >= 65 ? "#c2362b" : s >= 50 ? "#e8780c" : s >= 35 ? "#c9a21a" : "#1f8a5b");
const catLabel = (c) => META.categories[c]?.label || "Other";
const langName = (c) => META.languages[c]?.name || c;

function query(extra = {}) {
  const p = new URLSearchParams();
  if ($("fState").value) p.set("state", $("fState").value);
  if ($("fCat").value) p.set("category", $("fCat").value);
  for (const [k, v] of Object.entries(weights)) p.set("w_" + k, v);
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  return p.toString();
}

async function init() {
  META = await api("/api/meta");
  setAiBadge(META.ai_mode);
  weights = { ...META.default_weights };
  META.states.forEach((s) => $("fState").insertAdjacentHTML("beforeend", `<option>${esc(s)}</option>`));
  Object.entries(META.categories).forEach(([k, v]) => $("fCat").insertAdjacentHTML("beforeend", `<option value="${k}">${esc(v.label)}</option>`));
  $("fState").onchange = $("fCat").onchange = () => refresh(true);

  $("weights").innerHTML = Object.keys(weights).map((k) => `
    <div><label for="w_${k}"><span><span class="swatch" style="background:${COMP_COLORS[k]}"></span>${COMP_LABELS[k]}</span><span id="wv_${k}">${Math.round(weights[k] * 100)}</span></label>
    <input type="range" id="w_${k}" min="0" max="100" value="${Math.round(weights[k] * 100)}"></div>`).join("");
  let t;
  Object.keys(weights).forEach((k) => ($("w_" + k).oninput = (e) => {
    weights[k] = e.target.value / 100; $("wv_" + k).textContent = e.target.value;
    clearTimeout(t); t = setTimeout(() => refreshRanking(false), 150);
  }));

  $("examples").innerHTML = EXAMPLES.map((q) => `<button type="button">${esc(q)}</button>`).join("");
  $("examples").querySelectorAll("button").forEach((b) => (b.onclick = () => { $("askQ").value = b.textContent; ask(); }));
  $("askForm").onsubmit = (e) => { e.preventDefault(); ask(); };
  $("overlay").onclick = closeDrawer;
  document.addEventListener("keydown", (e) => e.key === "Escape" && closeDrawer());

  map = L.map("map", { scrollWheelZoom: false }).setView([22.8, 80.5], 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 12, attribution: "© OpenStreetMap" }).addTo(map);
  layer = L.layerGroup().addTo(map);

  await refresh(true);
  setInterval(() => refresh(false), 15000);
}

async function refresh(fit) {
  await Promise.all([refreshStats(), refreshRanking(fit), refreshFeed()]);
  $("updated").textContent = "Updated " + new Date().toLocaleTimeString();
}

async function refreshStats() {
  const s = await api("/api/stats?" + query());
  $("kTotal").textContent = fmt(s.total); $("kCitizens").textContent = fmt(s.citizens);
  $("kLangs").textContent = s.languages; $("kDistricts").textContent = s.districts;
  $("kStates").textContent = s.states; $("kWeek").textContent = fmt(s.last7);
  $("kLive").textContent = fmt(s.live);
  bars("catBars", s.by_category.map((r) => [catLabel(r.category), r.n]));
  bars("langBars", s.by_language.map((r) => [`${langName(r.language)} · ${META.languages[r.language]?.native || ""}`, r.n]));
  bars("chanBars", s.by_channel.map((r) => [r.channel, r.n]));
}

function bars(id, rows) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  $(id).innerHTML = rows.map(([l, n]) => `<div class="bar-row"><span>${esc(l)}</span>
    <div class="track"><div class="fill" style="width:${(100 * n) / max}%"></div></div><span class="num">${fmt(n)}</span></div>`).join("");
}

async function refreshRanking(fit) {
  const [pr, hs] = await Promise.all([api("/api/priorities?" + query({ limit: 30 })), api("/api/hotspots?" + query())]);
  $("rankCount").textContent = `${pr.total} district × sector candidates`;
  $("ranks").innerHTML = pr.items.map((r) => `
    <button class="rank" data-d="${esc(r.district)}" data-c="${r.category}">
      <span class="n">${r.rank}</span>
      <span><span class="t">${esc(r.district)}</span> <span class="muted small">${esc(r.state)}</span>
        <span class="chip">${esc(r.category_label)}</span>${r.emerging ? '<span class="chip hot">▲ emerging</span>' : ""}
        <div class="muted small">${r.requests} requests · ${r.distinct_issues} issues · ${r.coverage_pct != null ? `coverage ${Math.round(r.coverage_pct)}%` : "no official indicator"}</div>
        <div class="stack">${Object.entries(r.contributions).map(([k, v]) => `<span title="${COMP_LABELS[k]}: ${v}" style="width:${v}%;background:${COMP_COLORS[k]}"></span>`).join("")}</div>
      </span>
      <span class="s" style="color:${scoreColor(r.score)}">${r.score}</span>
    </button>`).join("") || '<p class="muted">No requests match these filters yet.</p>';
  $("ranks").querySelectorAll(".rank").forEach((b) => (b.onclick = () => openProject(b.dataset.d, b.dataset.c)));

  layer.clearLayers();
  const pts = [];
  for (const h of hs) {
    const r = h.top;
    const c = L.circleMarker([h.lat, h.lon], {
      radius: 5 + Math.sqrt(h.requests) * 2.2, color: scoreColor(r.score), fillColor: scoreColor(r.score),
      fillOpacity: 0.45, weight: h.emerging ? 3 : 1.5, dashArray: h.emerging ? "4 3" : null,
    }).addTo(layer);
    c.bindTooltip(`<b>${esc(h.district)}</b>, ${esc(h.state)}<br>${h.requests} requests<br>Top: ${esc(r.category_label)} (score ${r.score})`);
    c.on("click", () => openProject(h.district, r.category));
    pts.push([h.lat, h.lon]);
  }
  if (fit && pts.length) map.fitBounds(pts, { padding: [30, 30], maxZoom: 7 });
}

async function refreshFeed() {
  const items = await api("/api/requests?" + query({ limit: 25 }));
  const top = items[0]?.id;
  $("feed").innerHTML = items.map((r) => `
    <div class="feed-item ${lastFeedTop && r.id === top && top !== lastFeedTop ? "new-flash" : ""}">
      <div class="orig">${esc(r.original_text)}</div>
      ${r.language !== "en" ? `<div class="tr">${esc(r.translation)}</div>` : ""}
      <div class="meta">${r.ai_mode === "sample" ? '<span class="chip">sample</span>' : '<span class="chip hot">live</span>'}<span class="chip">${esc(langName(r.language))}</span><span class="chip">${esc(catLabel(r.category))}</span>
        <span class="urg urg-${r.urgency}">urgency ${r.urgency}/5</span><span>${esc(r.district || "unmapped")}</span>
        <span>· ${esc(r.channel)}</span><span>· ${ago(r.created_at)}</span>${r.ai_mode === "gemini" ? "<span>· ✦ Gemini</span>" : ""}</div>
    </div>`).join("");
  lastFeedTop = top;
}

async function ask() {
  const q = $("askQ").value.trim();
  if (!q) return;
  $("askBtn").disabled = true;
  $("askOut").innerHTML = '<p class="muted">Thinking…</p>';
  try {
    const r = await api("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q }) });
    const cols = r.rows.length ? Object.keys(r.rows[0]) : [];
    $("askOut").innerHTML = `<div class="answer">${md(r.answer)}</div>
      <details style="margin-top:8px"><summary class="muted small">Generated SQL (${r.ai_mode}) — ${esc(r.explanation)}</summary><pre class="sql">${esc(r.sql)}</pre></details>
      ${cols.length ? `<div class="table-wrap"><table class="data"><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr>
      ${r.rows.slice(0, 15).map((row) => `<tr>${cols.map((c) => `<td>${esc(row[c])}</td>`).join("")}</tr>`).join("")}</table></div>` : ""}`;
  } catch (e) {
    $("askOut").innerHTML = `<p class="error">${esc(e.message)}</p>`;
  } finally { $("askBtn").disabled = false; }
}

async function openProject(district, category) {
  $("drawer").innerHTML = '<p class="muted">Loading…</p>';
  $("drawer").classList.add("open"); $("overlay").classList.add("open");
  const d = await api(`/api/project/${encodeURIComponent(district)}/${category}?` + query());
  const p = d.priority;
  $("drawer").innerHTML = `
    <button class="ghost close" onclick="closeDrawer()" aria-label="Close">✕</button>
    <div class="muted small">National rank #${p.rank} · ${esc(p.scheme)}</div>
    <h2 style="font-size:21px;margin:4px 0">${esc(p.category_label)} — ${esc(p.district)}, ${esc(p.state)}</h2>
    <div>${p.emerging ? '<span class="chip hot">▲ emerging</span>' : ""}</div>
    <div style="display:flex;align-items:baseline;gap:10px;margin-top:10px"><span style="font-size:40px;font-weight:800;color:${scoreColor(p.score)}">${p.score}</span><span class="muted">priority score / 100</span></div>
    <div class="comp-grid">${Object.entries(p.contributions).map(([k, v]) => `<div class="comp" style="border-top:3px solid ${COMP_COLORS[k]}"><div class="v">${v}</div><div class="l">${COMP_LABELS[k]}</div></div>`).join("")}</div>
    <div class="kv">
      <div>Citizen requests</div><div><b>${p.requests}</b> from ${p.unique_citizens} citizens · ${p.distinct_issues} distinct issues</div>
      <div>Trend</div><div>${p.trend.last14} in last 14 days vs ${p.trend.prev14} in prior 14</div>
      <div>Avg urgency</div><div>${p.avg_urgency} / 5</div>
      <div>Official data (NFHS-5)</div><div>${p.coverage_pct != null ? `<b>${p.coverage_pct}%</b> — ${esc(p.indicator)}` : "No NFHS-5 indicator for this sector"}</div>
      <div>Population (Census 2011)</div><div>${p.population_2011 ? fmt(p.population_2011) : "n/a — district created after 2011"}${p.people_without ? ` · ~${fmt(p.people_without)} people without this service` : ""}</div>
      <div>Scheme</div><div>${esc(p.scheme)}</div>
      <div>Languages</div><div>${d.languages.map((l) => `${esc(langName(l.language))} (${l.n})`).join(", ")}</div>
    </div>
    <h3 style="margin-top:18px;font-size:14px">AI policy brief</h3>
    <div id="briefBox">${d.brief ? `<div class="brief">${md(d.brief.text)}</div>` : ""}</div>
    <button id="briefBtn" style="margin-top:8px">${d.brief ? "Regenerate brief" : "Generate brief with Gemini"}</button>
    <h3 style="margin-top:18px;font-size:14px">Issue clusters (duplicates merged)</h3>
    <div class="bars" style="margin-top:6px">${d.issues.map((i) => `<div class="bar-row" style="grid-template-columns:1fr 40px"><span>${esc(i.summary)} <span class="muted small">· urg ${i.urg}</span></span><span class="num">${i.n}×</span></div>`).join("")}</div>
    <h3 style="margin-top:18px;font-size:14px">What citizens said</h3>
    <div class="feed" style="max-height:none">${d.samples.map((s) => `<div class="feed-item"><div class="orig">${esc(s.original_text)}</div>
      ${s.language !== "en" ? `<div class="tr">${esc(s.translation)}</div>` : ""}
      <div class="meta">${s.ai_mode === "sample" ? '<span class="chip">sample</span>' : '<span class="chip hot">live</span>'}<span class="chip">${esc(langName(s.language))}</span><span class="urg urg-${s.urgency}">urgency ${s.urgency}</span><span>${esc(s.location_text || "")}</span><span>· ${esc(s.id)}</span></div></div>`).join("")}</div>`;
  $("briefBtn").onclick = async () => {
    $("briefBtn").disabled = true; $("briefBtn").innerHTML = '<span class="spinner"></span> Writing brief…';
    try {
      const b = await api(`/api/project/${encodeURIComponent(district)}/${category}/brief`, { method: "POST" });
      $("briefBox").innerHTML = `<div class="brief">${md(b.brief)}</div>`;
      $("briefBtn").textContent = "Regenerate brief";
    } catch (e) { $("briefBox").innerHTML = `<p class="error">${esc(e.message)}</p>`; $("briefBtn").textContent = "Retry"; }
    $("briefBtn").disabled = false;
  };
}

function closeDrawer() { $("drawer").classList.remove("open"); $("overlay").classList.remove("open"); }

init().catch((e) => { document.querySelector("main").insertAdjacentHTML("afterbegin", `<p class="error">Failed to load: ${esc(e.message)}</p>`); });
