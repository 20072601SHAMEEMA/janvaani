"""JanVaani API — FastAPI app serving the citizen intake, policymaker dashboard and REST API."""
import difflib
import json
import math
import os
import sqlite3
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, db, priority
from .lang import CATEGORIES, LANGUAGES

app = FastAPI(title="JanVaani", description="Multilingual citizen development-request platform (Digital Public Good)")
STATIC = db.ROOT / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")

MAX_UPLOAD = 8 * 1024 * 1024


@app.on_event("startup")
def _startup():
    db.init_db()


@app.get("/")
def dashboard():
    return FileResponse(STATIC / "index.html")


@app.get("/submit")
def submit_page():
    return FileResponse(STATIC / "submit.html")


@app.get("/api/health")
def health():
    return {"ok": True, "ai_mode": ai.mode(), "model": ai.MODEL if ai.mode() == "gemini" else None}


@app.get("/api/meta")
def meta():
    districts = db.rows("SELECT district, state, lat, lon FROM districts ORDER BY state, district")
    return {
        "ai_mode": ai.mode(),
        "categories": {k: {"label": v[0], "scheme": v[2]} for k, v in CATEGORIES.items()},
        "languages": LANGUAGES,
        "states": sorted({d["state"] for d in districts}),
        "districts": districts,
        "default_weights": priority.DEFAULT_WEIGHTS,
    }


def _filters(state: str | None, category: str | None):
    where, params = [], []
    if state:
        where.append("state = ?"); params.append(state)
    if category:
        where.append("category = ?"); params.append(category)
    return (" WHERE " + " AND ".join(where)) if where else "", params


@app.get("/api/stats")
def stats(state: str | None = None, category: str | None = None):
    w, p = _filters(state, category)
    total = db.rows(f"SELECT COUNT(*) n, COUNT(DISTINCT citizen_hash) c, COUNT(DISTINCT district) d, "
                    f"COUNT(DISTINCT state) s, COUNT(DISTINCT language) l FROM requests{w}", p)[0]
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    week = db.rows(f"SELECT COUNT(*) n FROM requests{w}{' AND' if w else ' WHERE'} created_at >= ?", p + [since])[0]["n"]
    by_cat = db.rows(f"SELECT category, COUNT(*) n, ROUND(AVG(urgency),2) urg FROM requests{w} "
                     f"GROUP BY category ORDER BY n DESC", p)
    by_lang = db.rows(f"SELECT language, COUNT(*) n FROM requests{w} GROUP BY language ORDER BY n DESC", p)
    by_channel = db.rows(f"SELECT channel, COUNT(*) n FROM requests{w} GROUP BY channel ORDER BY n DESC", p)
    daily = db.rows(f"SELECT substr(created_at,1,10) day, COUNT(*) n FROM requests{w} "
                    f"GROUP BY day ORDER BY day DESC LIMIT 60", p)
    return {"total": total["n"], "citizens": total["c"], "districts": total["d"], "states": total["s"],
            "languages": total["l"], "last7": week, "by_category": by_cat, "by_language": by_lang,
            "by_channel": by_channel, "daily": list(reversed(daily))}


def _weights(req: Request) -> dict:
    out = {}
    for k in priority.DEFAULT_WEIGHTS:
        v = req.query_params.get(f"w_{k}")
        if v is not None:
            try:
                out[k] = max(0.0, float(v))
            except ValueError:
                pass
    return out


@app.get("/api/priorities")
def priorities(request: Request, state: str | None = None, category: str | None = None, limit: int = 25):
    ranked = priority.compute(_weights(request), state, category)
    return {"weights": {**priority.DEFAULT_WEIGHTS, **_weights(request)}, "total": len(ranked),
            "items": ranked[:limit]}


@app.get("/api/hotspots")
def hotspots(request: Request, state: str | None = None, category: str | None = None):
    ranked = priority.compute(_weights(request), state, category)
    by_d: dict[str, dict] = {}
    for r in ranked:
        h = by_d.setdefault(r["district"], {"district": r["district"], "state": r["state"], "lat": r["lat"],
                                            "lon": r["lon"], "requests": 0, "top": r, "emerging": False})
        h["requests"] += r["requests"]
        h["emerging"] = h["emerging"] or r["emerging"]
    return list(by_d.values())


def _project(district: str, category: str, weights: dict | None = None):
    ranked = priority.compute(weights)
    p = next((r for r in ranked if r["district"] == district and r["category"] == category), None)
    if not p:
        raise HTTPException(404, "No requests for this district/category")
    issues = db.rows("SELECT cluster_id, summary, COUNT(*) n, ROUND(AVG(urgency),1) urg, MAX(created_at) last "
                     "FROM requests WHERE district=? AND category=? GROUP BY cluster_id ORDER BY n DESC LIMIT 8",
                     (district, category))
    samples = db.rows("SELECT id, created_at, channel, language, original_text, translation, urgency, "
                      "location_text, status FROM requests WHERE district=? AND category=? "
                      "ORDER BY urgency DESC, created_at DESC LIMIT 6", (district, category))
    langs = db.rows("SELECT language, COUNT(*) n FROM requests WHERE district=? AND category=? "
                    "GROUP BY language ORDER BY n DESC", (district, category))
    return p, issues, samples, langs


@app.get("/api/project/{district}/{category}")
def project(district: str, category: str, request: Request):
    p, issues, samples, langs = _project(district, category, _weights(request))
    cached = db.rows("SELECT text, created_at FROM briefs WHERE key=?", (f"{district}|{category}",))
    return {"priority": p, "issues": issues, "samples": samples, "languages": langs,
            "brief": cached[0] if cached else None}


@app.post("/api/project/{district}/{category}/brief")
def project_brief(district: str, category: str):
    p, issues, samples, langs = _project(district, category)
    evidence = {
        "priority": p, "top_issue_clusters": issues,
        "sample_requests_en": [s["translation"] for s in samples],
        "languages_of_requests": langs,
    }
    text, mode = ai.policy_brief(evidence)
    conn = db.connect()
    conn.execute("INSERT OR REPLACE INTO briefs VALUES (?,?,?)",
                 (f"{district}|{category}", text, datetime.now(timezone.utc).isoformat(timespec="seconds")))
    conn.commit(); conn.close()
    return {"brief": text, "ai_mode": mode}


@app.get("/api/requests")
def list_requests(state: str | None = None, category: str | None = None, district: str | None = None,
                  limit: int = 30):
    w, p = _filters(state, category)
    if district:
        w += (" AND" if w else " WHERE") + " district = ?"; p.append(district)
    return db.rows(f"SELECT id, created_at, channel, language, original_text, translation, category, urgency, "
                   f"summary, state, district, status, ai_mode FROM requests{w} ORDER BY created_at DESC LIMIT ?",
                   p + [min(limit, 200)])


@app.get("/api/requests/{rid}")
def get_request(rid: str):
    r = db.rows("SELECT id, created_at, channel, language, original_text, translation, category, urgency, "
                "summary, location_text, state, district, status, photo_note, ai_mode FROM requests WHERE id=?",
                (rid.upper(),))
    if not r:
        raise HTTPException(404, "Ticket not found")
    rec = r[0]
    rec["similar_reports"] = db.rows("SELECT COUNT(*) n FROM requests WHERE cluster_id = "
                                     "(SELECT cluster_id FROM requests WHERE id=?)", (rid.upper(),))[0]["n"]
    return rec


# ------------------------------------------------------------------ intake
def _resolve_district(district: str, state: str, analysis: dict, lat: float | None, lon: float | None):
    ds = db.rows("SELECT district, state, lat, lon FROM districts")
    names = {d["district"].lower(): d for d in ds}
    if district and district.lower() in names:
        return names[district.lower()]
    guess = (analysis.get("district_guess") or "").lower()
    if guess:
        m = difflib.get_close_matches(guess, names.keys(), n=1, cutoff=0.75)
        if m:
            return names[m[0]]
    blob = f"{analysis.get('transcript', '')} {analysis.get('translation_en', '')}".lower()
    mentioned = [d for n, d in names.items() if n in blob]
    if mentioned:
        return max(mentioned, key=lambda d: len(d["district"]))
    if lat is not None and lon is not None:
        def dist(d):
            dlat, dlon = math.radians(d["lat"] - lat), math.radians(d["lon"] - lon)
            a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(d["lat"])) * math.sin(dlon / 2) ** 2
            return 6371 * 2 * math.asin(math.sqrt(a))
        nearest = min(ds, key=dist)
        if dist(nearest) < 200:
            return nearest
    return None


def _assign_cluster(district: str | None, category: str, translation: str, emb: list | None, rid: str) -> str:
    if not district:
        return f"unmapped|{rid}"
    since = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    cands = db.rows("SELECT cluster_id, translation, embedding FROM requests WHERE district=? AND category=? "
                    "AND created_at >= ? ORDER BY created_at DESC LIMIT 300", (district, category, since))
    best, best_sim = None, 0.0
    for c in cands:
        if emb and c["embedding"]:
            sim, thr = ai.cosine(emb, json.loads(c["embedding"])), 0.88
        else:
            sim, thr = ai.jaccard(translation, c["translation"] or ""), 0.6
        if sim >= thr and sim > best_sim:
            best, best_sim = c["cluster_id"], sim
    return best or f"{district}|{category}|live|{rid}"


def ingest(text: str = "", audio: bytes | None = None, audio_mime: str = "audio/wav",
           image: bytes | None = None, image_mime: str = "image/jpeg", channel: str = "web",
           contact: str = "", state: str = "", district: str = "",
           lat: float | None = None, lon: float | None = None) -> dict:
    a = ai.analyse(text, audio, audio_mime, image, image_mime, state, district)
    if not a.get("is_development_request") and not text and not audio:
        raise HTTPException(400, "Empty request")
    rid = db.new_ticket()
    d = _resolve_district(district, state, a, lat, lon)
    cat = a["category"] if a["category"] in CATEGORIES else "other"
    emb = ai.embed(a["translation_en"])
    cluster = _assign_cluster(d["district"] if d else None, cat, a["translation_en"], emb, rid)
    rec = {
        "id": rid, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "channel": channel,
        "citizen_hash": db.citizen_hash(contact or rid), "original_text": a["transcript"],
        "language": a["language"], "translation": a["translation_en"], "category": cat,
        "urgency": a["urgency"], "summary": a["summary_en"],
        "location_text": a.get("location_mentioned") or (d["district"] if d else ""),
        "state": d["state"] if d else (a.get("state_guess") or state or None),
        "district": d["district"] if d else None,
        "lat": lat if lat is not None else (d["lat"] if d else None),
        "lon": lon if lon is not None else (d["lon"] if d else None),
        "sentiment": a["sentiment"], "has_photo": int(image is not None), "photo_note": a.get("photo_observation"),
        "status": "received" if a.get("is_development_request", True) else "needs_review",
        "cluster_id": cluster, "embedding": emb, "ai_mode": a["ai_mode"],
    }
    db.insert_request(rec)
    similar = db.rows("SELECT COUNT(*) n FROM requests WHERE cluster_id=?", (cluster,))[0]["n"]
    ack = (a.get("acknowledgement") or "").replace("{id}", rid)
    if rid not in ack:
        ack += f" ({rid})"
    rec.pop("embedding"); rec.pop("citizen_hash")
    return {**rec, "acknowledgement": ack, "bcp47": LANGUAGES.get(a["language"], {}).get("bcp47", "en-IN"),
            "similar_reports": similar, "is_development_request": a.get("is_development_request", True)}


@app.post("/api/requests")
async def create_request(text: str = Form(""), state: str = Form(""), district: str = Form(""),
                         contact: str = Form(""), channel: str = Form("web"),
                         lat: float | None = Form(None), lon: float | None = Form(None),
                         audio: UploadFile | None = File(None), photo: UploadFile | None = File(None)):
    audio_b = await audio.read() if audio else None
    photo_b = await photo.read() if photo else None
    if (audio_b and len(audio_b) > MAX_UPLOAD) or (photo_b and len(photo_b) > MAX_UPLOAD):
        raise HTTPException(413, "File too large (8 MB max)")
    if not text.strip() and not audio_b:
        raise HTTPException(400, "Please type a message or record a voice note")
    return ingest(text=text.strip(), audio=audio_b or None,
                  audio_mime=(audio.content_type if audio else None) or "audio/wav",
                  image=photo_b or None, image_mime=(photo.content_type if photo else None) or "image/jpeg",
                  channel=channel if channel in {"web", "voice", "whatsapp", "telegram", "sms"} else "web",
                  contact=contact, state=state, district=district, lat=lat, lon=lon)


# ------------------------------------------------------------------ ask the data
class Ask(BaseModel):
    question: str


PRIVATE_COLUMNS = {"citizen_hash", "embedding", "original_text", "lat", "lon"}


def _authorizer(action, arg1, arg2, dbname, source):
    if action == sqlite3.SQLITE_READ and arg2 in PRIVATE_COLUMNS and arg1 == "requests":
        return sqlite3.SQLITE_IGNORE  # privacy: never expose raw citizen data via free-form queries
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def run_readonly(sql: str) -> list[dict]:
    s = sql.strip().rstrip(";")
    if not s.lower().startswith(("select", "with")) or ";" in s:
        raise HTTPException(400, "Only single SELECT queries are allowed")
    conn = db.connect(readonly=True)
    conn.set_authorizer(_authorizer)
    steps = [0]

    def guard():
        steps[0] += 1
        return 1 if steps[0] > 2000 else 0  # abort runaway queries
    conn.set_progress_handler(guard, 1000)
    try:
        return [dict(r) for r in conn.execute(s).fetchmany(200)]
    except sqlite3.Error as e:
        raise HTTPException(400, f"Query failed: {e}")
    finally:
        conn.close()


@app.post("/api/ask")
def ask(body: Ask):
    q = body.question.strip()[:500]
    if not q:
        raise HTTPException(400, "Ask a question")
    plan = ai.nl_to_sql(q)
    rows = run_readonly(plan["sql"])
    return {"question": q, "sql": plan["sql"], "explanation": plan["explanation"], "rows": rows,
            "answer": ai.summarise_answer(q, rows), "ai_mode": plan["ai_mode"]}


# ------------------------------------------------------------------ Telegram channel
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TG_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")


def _tg(method: str, payload: dict) -> dict:
    req = urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/{method}",
                                 data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


@app.post("/webhook/telegram/{secret}")
async def telegram(secret: str, request: Request):
    if not TG_TOKEN or not TG_SECRET or secret != TG_SECRET:
        raise HTTPException(404)
    upd = await request.json()
    msg = upd.get("message") or {}
    chat = msg.get("chat", {}).get("id")
    if not chat:
        return {"ok": True}
    if msg.get("text", "").startswith("/start"):
        _tg("sendMessage", {"chat_id": chat, "text": "🙏 JanVaani: send your development request as text or a "
                                                     "voice note in any Indian language. Share location for accuracy."})
        return {"ok": True}
    audio, loc = None, msg.get("location") or {}
    if msg.get("voice"):
        f = _tg("getFile", {"file_id": msg["voice"]["file_id"]})["result"]
        with urllib.request.urlopen(f"https://api.telegram.org/file/bot{TG_TOKEN}/{f['file_path']}", timeout=20) as r:
            audio = r.read()
    text = msg.get("text") or msg.get("caption") or ""
    if not text and not audio:
        return {"ok": True}
    res = ingest(text=text, audio=audio, audio_mime="audio/ogg", channel="telegram",
                 contact=f"tg:{msg.get('from', {}).get('id', chat)}", lat=loc.get("latitude"), lon=loc.get("longitude"))
    _tg("sendMessage", {"chat_id": chat, "text": f"{res['acknowledgement']}\n\n📍 {res['district'] or 'Location pending'}"
                                                 f" · {CATEGORIES.get(res['category'], ('Other',))[0]}"
                                                 f" · {res['similar_reports']} similar report(s)"})
    return {"ok": True}
