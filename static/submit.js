const $ = (id) => document.getElementById(id);
let META, audioBlob = null, recorder = null, chunks = [], timer = null, coords = null;

const SAMPLES = [
  { label: "తెలుగు · water", district: "Anantapur", text: "మా గ్రామానికి మూడు వారాలుగా తాగునీరు రావడం లేదు, చేతి పంపు పాడైపోయింది." },
  { label: "हिन्दी · health", district: "Bahraich", text: "हमारे प्राथमिक स्वास्थ्य केंद्र में कोई डॉक्टर नहीं है, इलाज के लिए 40 किलोमीटर जाना पड़ता है।" },
  { label: "தமிழ் · sanitation", district: "Chennai", text: "கழிவுநீர் கால்வாய்கள் அடைபட்டுள்ளன, கழிவுநீர் தெருவில் ஓடுகிறது, குழந்தைகள் நோய்வாய்ப்படுகிறார்கள்." },
  { label: "ଓଡ଼ିଆ · roads", district: "Malkangiri", text: "ଆମ ଗାଁର ରାସ୍ତା ଭାଙ୍ଗିଯାଇଛି, ବର୍ଷାରେ କାଦୁଅ ହୋଇଯାଏ, ଆମ୍ବୁଲାନ୍ସ ଆସିପାରୁନାହିଁ।" },
  { label: "অসমীয়া · roads", district: "Dhubri", text: "আমাৰ গাঁৱৰ পথটো ভাঙি গৈছে, বাৰিষা বোকা হৈ যায়, এম্বুলেন্স আহিব নোৱাৰে।" },
  { label: "Hinglish · power", district: "", text: "Bhaiya humare gaon Jhabua mein 1 mahine se transformer jala hua hai, bijli nahi hai, bachche padh nahi paa rahe" },
];

async function init() {
  META = await api("/api/meta");
  setAiBadge(META.ai_mode);
  META.states.forEach((s) => $("state").insertAdjacentHTML("beforeend", `<option>${esc(s)}</option>`));
  fillDistricts();
  $("state").onchange = fillDistricts;
  $("samples").innerHTML = SAMPLES.map((s, i) => `<button type="button" data-i="${i}">${esc(s.label)}</button>`).join("");
  $("samples").querySelectorAll("button").forEach((b) => (b.onclick = () => {
    const s = SAMPLES[b.dataset.i];
    $("text").value = s.text;
    const d = META.districts.find((x) => x.district === s.district);
    $("state").value = d ? d.state : ""; fillDistricts(); $("district").value = s.district;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }));
  $("mic").onclick = toggleRecord;
  $("geoBtn").onclick = locate;
  $("form").onsubmit = submit;
  $("trackForm").onsubmit = track;
  const t = new URLSearchParams(location.search).get("ticket");
  if (t) { $("ticket").value = t; track(new Event("submit")); }
}

function fillDistricts() {
  const st = $("state").value;
  $("district").innerHTML = '<option value="">Auto-detect</option>' + META.districts
    .filter((d) => !st || d.state === st).map((d) => `<option>${esc(d.district)}</option>`).join("");
}

function locate() {
  if (!navigator.geolocation) return ($("geoStatus").textContent = "Location not supported");
  $("geoStatus").textContent = "Locating…";
  navigator.geolocation.getCurrentPosition(
    (p) => { coords = { lat: p.coords.latitude, lon: p.coords.longitude }; $("geoStatus").textContent = `📍 ${coords.lat.toFixed(3)}, ${coords.lon.toFixed(3)}`; },
    () => ($("geoStatus").textContent = "Location permission denied"), { timeout: 10000 });
}

// ---- voice: record with MediaRecorder, convert to 16 kHz mono WAV (universally accepted by Gemini)
async function toggleRecord() {
  if (recorder && recorder.state === "recording") return recorder.stop();
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chunks = []; recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      clearInterval(timer); $("mic").classList.remove("rec");
      $("micStatus").innerHTML = "Processing…";
      try {
        audioBlob = await toWav(new Blob(chunks, { type: recorder.mimeType }));
        $("playback").src = URL.createObjectURL(audioBlob); $("playback").hidden = false;
        $("micStatus").innerHTML = `<b>Voice note ready</b> (${(audioBlob.size / 1024).toFixed(0)} KB) — tap 🎙️ to re-record`;
      } catch (e) { $("micStatus").textContent = "Could not process audio: " + e.message; }
    };
    recorder.start();
    $("mic").classList.add("rec");
    let s = 0;
    $("micStatus").innerHTML = "<b>Recording…</b> 0s — tap to stop";
    timer = setInterval(() => { s++; $("micStatus").innerHTML = `<b>Recording…</b> ${s}s — tap to stop`; if (s >= 60) recorder.stop(); }, 1000);
  } catch (e) { $("micStatus").textContent = "Microphone unavailable: " + e.message; }
}

async function toWav(blob) {
  const buf = await blob.arrayBuffer();
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const decoded = await ctx.decodeAudioData(buf);
  ctx.close();
  const rate = 16000;
  const off = new OfflineAudioContext(1, Math.ceil(decoded.duration * rate), rate);
  const src = off.createBufferSource(); src.buffer = decoded; src.connect(off.destination); src.start();
  const pcm = (await off.startRendering()).getChannelData(0);
  const out = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const w = (o, s) => [...s].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); out.setUint32(4, 36 + pcm.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, 1, true);
  out.setUint32(24, rate, true); out.setUint32(28, rate * 2, true); out.setUint16(32, 2, true); out.setUint16(34, 16, true);
  w(36, "data"); out.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) out.setInt16(44 + i * 2, Math.max(-1, Math.min(1, pcm[i])) * 0x7fff, true);
  return new Blob([out], { type: "audio/wav" });
}

async function submit(e) {
  e.preventDefault();
  $("err").textContent = "";
  const text = $("text").value.trim();
  if (!text && !audioBlob && !$("photo").files[0]) return ($("err").textContent = "Please speak, type or add a photo of the problem.");
  const fd = new FormData();
  fd.append("text", text);
  fd.append("state", $("state").value); fd.append("district", $("district").value);
  fd.append("contact", $("contact").value.trim());
  fd.append("channel", audioBlob ? "voice" : "web");
  if (coords) { fd.append("lat", coords.lat); fd.append("lon", coords.lon); }
  if (audioBlob) fd.append("audio", audioBlob, "voice.wav");
  if ($("photo").files[0]) fd.append("photo", $("photo").files[0]);
  const btn = $("submitBtn");
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Understanding your request…';
  try {
    const r = await api("/api/requests", { method: "POST", body: fd });
    showResult(r);
    $("form").reset(); audioBlob = null; $("playback").hidden = true; coords = null; $("geoStatus").textContent = "";
    $("micStatus").innerHTML = "<b>Tap to speak</b> — up to 60 seconds"; fillDistricts();
  } catch (err) { $("err").textContent = err.message; }
  finally { btn.disabled = false; btn.textContent = "Submit request"; }
}

function speak(text, lang) {
  if (!("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  const v = speechSynthesis.getVoices().find((x) => x.lang.replace("_", "-").startsWith(lang.slice(0, 2)));
  if (v) u.voice = v;
  speechSynthesis.speak(u);
}

function showResult(r) {
  const lang = META.languages[r.language] || { name: r.language, native: "" };
  $("result").innerHTML = `
    <div class="card result">
      <div class="muted small">Your ticket number</div>
      <div class="ticket">${esc(r.id)}</div>
      <div class="ack">${esc(r.acknowledgement)} <button type="button" class="ghost" id="speakBtn" title="Listen">🔊</button></div>
      ${r.is_development_request ? "" : '<p class="error">This did not look like a development request — it has been queued for manual review.</p>'}
      <div class="kv">
        <div>Language detected</div><div>${esc(lang.name)}${lang.native && lang.native !== lang.name ? " · " + esc(lang.native) : ""}</div>
        ${r.original_text ? `<div>We heard</div><div>${esc(r.original_text)}</div>` : ""}
        ${r.translation && r.translation !== r.original_text ? `<div>In English</div><div>${esc(r.translation)}</div>` : ""}
        <div>Category</div><div>${esc(META.categories[r.category]?.label || "Other")} → routed to ${esc(META.categories[r.category]?.scheme || "district office")}</div>
        <div>Urgency</div><div class="urg urg-${r.urgency}">${r.urgency} / 5</div>
        <div>Location</div><div>${esc(r.district ? `${r.district}, ${r.state}` : "Pending — an officer will confirm")}</div>
        ${r.photo_note ? `<div>Photo</div><div>${esc(r.photo_note)}</div>` : ""}
        <div>Community signal</div><div>${r.similar_reports > 1 ? `<b>${r.similar_reports} citizens</b> have reported this same issue — your voice strengthens its priority.` : "First report of this issue in your area."}</div>
        <div>Analysed by</div><div>${r.ai_mode === "gemini" ? "✦ Google Gemini" : "Basic keyword analysis (Gemini unavailable)"}</div>
      </div>
    </div>`;
  $("speakBtn").onclick = () => speak(r.acknowledgement, r.bcp47);
  speak(r.acknowledgement, r.bcp47);
  $("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function track(e) {
  e.preventDefault();
  const id = $("ticket").value.trim();
  if (!id) return;
  try {
    const r = await api("/api/requests/" + encodeURIComponent(id));
    const steps = ["received", "under_review", "forwarded", "resolved"];
    const at = steps.indexOf(r.status);
    $("trackOut").innerHTML = `<div class="kv">
      <div>Status</div><div>${steps.map((s, i) => `<span class="chip" style="${i <= at ? "background:var(--good);color:#fff" : ""}">${s.replace("_", " ")}</span>`).join(" ")}</div>
      <div>Issue</div><div>${esc(r.summary)}</div>
      <div>Where</div><div>${esc(r.district || "Pending")}${r.state ? ", " + esc(r.state) : ""}</div>
      <div>Filed</div><div>${new Date(r.created_at).toLocaleString()}</div>
      <div>Similar reports</div><div>${r.similar_reports}</div></div>`;
  } catch (err) { $("trackOut").innerHTML = `<p class="error">${esc(err.message)}</p>`; }
}

init();
