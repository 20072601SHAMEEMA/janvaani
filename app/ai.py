"""Google Gemini integration (with an offline fallback so the demo never breaks).

Gemini does four jobs:
  1. analyse()      multimodal understanding: voice/text/photo in any Indian language
                    -> structured JSON (transcript, translation, category, urgency, location...)
  2. embed()        gemini-embedding vectors to merge duplicate reports into one issue
  3. nl_to_sql()    policymakers ask questions in plain language -> safe read-only SQL
  4. policy_brief() evidence pack -> short, cited recommendation note for a ministry
"""
import enum
import time
import json
import os
import re

from pydantic import BaseModel, Field

from .lang import ACK, CATEGORIES, KEYWORDS, LANGUAGES, URGENT_WORDS, detect_language, template_lookup

API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")

_client = None
if API_KEY:
    try:
        from google import genai
        from google.genai import types
        # Set GOOGLE_GENAI_USE_VERTEXAI=true to route through Vertex AI instead of the Gemini Developer API
        use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("1", "true")
        # Keep citizens waiting seconds, not minutes: 25 s per call and one quick retry, then the next model
        http = types.HttpOptions(timeout=25_000, retry_options=types.HttpRetryOptions(
            attempts=2, initial_delay=1.0, max_delay=2.0))
        _client = genai.Client(vertexai=use_vertex, api_key=API_KEY, http_options=http)
    except Exception as e:  # pragma: no cover
        print("Gemini client unavailable, using offline mode:", e)

_TEMPLATES = template_lookup()


def mode() -> str:
    return "gemini" if _client else "offline"


# Backup models tried in order when the primary is overloaded or rate-limited (503/429)
FALLBACK_MODELS = [m for m in os.environ.get(
    "GEMINI_FALLBACK_MODELS", "gemini-3.5-flash,gemini-flash-latest,gemini-3.1-flash-lite").split(",") if m]


TOTAL_BUDGET_S = 60  # stop trying more models after this, and use the offline fallback


def _generate(contents, config):
    last, start = None, time.monotonic()
    for model in dict.fromkeys([MODEL, *FALLBACK_MODELS]):
        if last is not None and time.monotonic() - start > TOTAL_BUDGET_S:
            break
        try:
            return _client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            last = e
            # bad request / auth errors won't be fixed by another model; overload, rate-limit and network errors might
            if any(str(e).startswith(code) for code in ("400", "401", "403")):
                raise
            print(f"{model} unavailable, trying next model")
    raise last


# ---------------------------------------------------------------- analysis
Category = enum.Enum("Category", {c: c for c in list(CATEGORIES) + ["other"]}, type=str)
Lang = enum.Enum("Lang", {c: c for c in LANGUAGES}, type=str)


class Sentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    concerned = "concerned"
    negative = "negative"
    distressed = "distressed"


class Analysis(BaseModel):
    is_development_request: bool = Field(description="False for spam, greetings or unrelated content")
    transcript: str = Field(description="Verbatim text in the original language (transcribe audio if given)")
    language: Lang
    translation_en: str = Field(description="Faithful English translation")
    category: Category
    urgency: int = Field(description="1 (minor) to 5 (risk to life/health, many affected)")
    summary_en: str = Field(description="Under 12 words, headline style")
    location_mentioned: str = Field(description="Village/ward/landmark mentioned, or empty string")
    district_guess: str = Field(description="Indian district if inferable, else empty string")
    state_guess: str = Field(description="Indian state if inferable, else empty string")
    sentiment: Sentiment
    photo_observation: str = Field(description="What the photo shows as evidence, or empty string")
    acknowledgement: str = Field(description="Warm 1-2 sentence reply to the citizen IN THEIR LANGUAGE, "
                                             "confirming the issue was recorded. Include placeholder {id} for the ticket.")


ANALYSE_PROMPT = """You are the intake officer of JanVaani, India's multilingual citizen development-request platform.
A citizen has sent a request (text, voice and/or photo). Understand it in whatever Indian language or mix
(Hinglish, Tanglish, etc.) it is in and return the JSON schema exactly.

Categories: water (drinking water, piped supply, handpumps), roads (roads, bridges, potholes, transport access),
health (PHCs, hospitals, doctors, medicines), education (schools, teachers, school infrastructure),
power (electricity supply, transformers), sanitation (drains, sewage, garbage, toilets),
digital (mobile network, internet, BharatNet, CSC), other.
Urgency: 5 = immediate risk to life/health or whole community without an essential service; 1 = minor/cosmetic.
Citizen-selected location hint (may be empty): state="{state}", district="{district}".
"""


def analyse(text: str = "", audio: bytes | None = None, audio_mime: str = "audio/wav",
            image: bytes | None = None, image_mime: str = "image/jpeg",
            state_hint: str = "", district_hint: str = "") -> dict:
    if _client:
        try:
            return _analyse_gemini(text, audio, audio_mime, image, image_mime, state_hint, district_hint)
        except Exception as e:
            print("Gemini analyse failed, falling back:", e)
    return _analyse_offline(text, audio is not None, image is not None)


def _analyse_gemini(text, audio, audio_mime, image, image_mime, state_hint, district_hint) -> dict:
    parts = []
    if audio:
        parts.append(types.Part.from_bytes(data=audio, mime_type=audio_mime))
    if image:
        parts.append(types.Part.from_bytes(data=image, mime_type=image_mime))
    prompt = ANALYSE_PROMPT.format(state=state_hint, district=district_hint)
    if text:
        prompt += f"\nCitizen's typed message:\n\"\"\"{text}\"\"\""
    parts.append(prompt)
    resp = _generate(
        contents=parts,
        config=types.GenerateContentConfig(response_mime_type="application/json",
                                           response_schema=Analysis, temperature=0.1))
    a = resp.parsed if resp.parsed else Analysis.model_validate_json(resp.text)
    out = a.model_dump(mode="json")
    out["urgency"] = max(1, min(5, int(out["urgency"])))
    out["ai_mode"] = "gemini"
    return out


def _analyse_offline(text: str, had_audio: bool, had_image: bool) -> dict:
    text = (text or "").strip()
    if not text:
        text = ("(voice note received — transcription needs a Gemini API key)" if had_audio
                else "(photo received — an officer will review it)" if had_image else "")
    lang = detect_language(text)
    tpl = _TEMPLATES.get(text)
    if tpl:
        cat, v = tpl
        translation, urgency, summary = v["en"], v["urgency"], v["summary"]
    else:
        low = text.lower()
        cat = next((c for c, kws in KEYWORDS.items() if any(k.lower() in low for k in kws)), "other")
        urgency = 4 if any(w in low for w in URGENT_WORDS) else 3
        translation = text if lang == "en" else f"[offline mode — add GEMINI_API_KEY for translation] {text}"
        summary = (CATEGORIES[cat][0] if cat in CATEGORIES else "General") + " issue reported by citizen"
    return {
        "is_development_request": bool(text),
        "transcript": text, "language": lang, "translation_en": translation, "category": cat,
        "urgency": urgency, "summary_en": summary, "location_mentioned": "", "district_guess": "",
        "state_guess": "", "sentiment": "negative" if urgency >= 4 else "concerned",
        "photo_observation": "Photo attached (visual analysis needs a Gemini API key)" if had_image else "",
        "acknowledgement": ACK.get(lang, ACK["en"]), "ai_mode": "offline",
    }


# ---------------------------------------------------------------- embeddings
def embed(text: str) -> list[float] | None:
    if not _client or not text:
        return None
    try:
        r = _client.models.embed_content(model=EMBED_MODEL, contents=text,
                                         config=types.EmbedContentConfig(output_dimensionality=256,
                                                                         task_type="SEMANTIC_SIMILARITY"))
        return list(r.embeddings[0].values)
    except Exception as e:
        print("embed failed:", e)
        return None


def cosine(a, b) -> float:
    num = sum(x * y for x, y in zip(a, b))
    den = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
    return num / den if den else 0.0


def jaccard(a: str, b: str) -> float:
    ta, tb = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


# ---------------------------------------------------------------- ask the data
SQL_SCHEMA = """SQLite tables:
districts(district TEXT, state TEXT, lat REAL, lon REAL, population_2011 INT (Census 2011; NULL if created after 2011),
          water REAL, sanitation REAL, power REAL, health REAL, education REAL, note TEXT)
          -- real NFHS-5 (2019-21) % coverage, higher = better served:
          -- water = improved drinking-water source, sanitation = improved sanitation facility,
          -- power = households with electricity, health = institutional births, education = females 6+ ever in school
requests(id TEXT, created_at TEXT ISO8601, channel TEXT, language TEXT (ISO code e.g. hi, te, ta),
         translation TEXT (English), category TEXT one of water|roads|health|education|power|sanitation|digital|other,
         urgency INT 1-5, summary TEXT, state TEXT, district TEXT, status TEXT,
         ai_mode TEXT ('sample' = starting sample data, 'gemini'/'offline' = live submission))
"""


class SQLPlan(BaseModel):
    sql: str = Field(description="A single SQLite SELECT statement, LIMIT 50 or fewer rows")
    explanation: str = Field(description="One sentence on what the query computes")


def nl_to_sql(question: str) -> dict:
    if _client:
        try:
            resp = _generate(
                contents=f"{SQL_SCHEMA}\nWrite one read-only SQLite query answering the policymaker's question. "
                         f"Use exact state names as stored (e.g. 'Uttar Pradesh'). Prefer aggregated, "
                         f"ranked results with readable column aliases.\nQuestion: {question}",
                config=types.GenerateContentConfig(response_mime_type="application/json",
                                                   response_schema=SQLPlan, temperature=0))
            plan = resp.parsed or SQLPlan.model_validate_json(resp.text)
            return plan.model_dump() | {"ai_mode": "gemini"}
        except Exception as e:
            print("nl_to_sql failed, falling back:", e)
    return _nl_to_sql_offline(question) | {"ai_mode": "offline"}


def _nl_to_sql_offline(q: str) -> dict:
    from . import db
    low = q.lower()
    states = [r["state"] for r in db.rows("SELECT DISTINCT state FROM districts")]
    state = next((s for s in states if s.lower() in low), None)
    cat = next((c for c, kws in KEYWORDS.items() if any(k.lower() in low for k in kws)), None)
    where = []
    if state:
        where.append(f"r.state = '{state}'")
    if cat:
        where.append(f"r.category = '{cat}'")
    if "language" in low:
        sql = ("SELECT language, COUNT(*) AS requests FROM requests r"
               + (" WHERE " + " AND ".join(where) if where else "") + " GROUP BY language ORDER BY requests DESC")
        return {"sql": sql, "explanation": "Requests by language."}
    sql = ("SELECT r.district, r.state, COUNT(*) AS requests, ROUND(AVG(r.urgency),2) AS avg_urgency"
           + (f", d.{cat} AS nfhs5_coverage_pct" if cat and CATEGORIES[cat][2] else "")
           + " FROM requests r JOIN districts d ON d.district = r.district"
           + (" WHERE " + " AND ".join(where) if where else "")
           + " GROUP BY r.district ORDER BY requests DESC LIMIT 10")
    return {"sql": sql, "explanation": "Districts ranked by citizen request volume"
            + (f" for {cat}" if cat else "") + (f" in {state}" if state else "") + "."}


def summarise_answer(question: str, rows: list[dict]) -> str:
    if _client and rows:
        try:
            resp = _generate(
                contents=f"Question from a government policymaker: {question}\nQuery result (JSON): "
                         f"{json.dumps(rows[:50], default=str)}\nAnswer in 2-4 crisp sentences with the key "
                         f"numbers. Do not invent data beyond the result.",
                config=types.GenerateContentConfig(temperature=0.2))
            return resp.text.strip()
        except Exception as e:
            print("summarise failed:", e)
    if not rows:
        return "No matching records."
    top = rows[0]
    return "Top result: " + ", ".join(f"{k} = {v}" for k, v in top.items()) + f". ({len(rows)} rows returned.)"


# ---------------------------------------------------------------- policy brief
def policy_brief(ev: dict) -> tuple[str, str]:
    if _client:
        try:
            resp = _generate(
                contents="You are a policy analyst for a national infrastructure planning cell in India. Using ONLY "
                         "the evidence below, write a concise decision brief in Markdown with sections: "
                         "**Recommendation** (one line, specific project), **Why now** (3 bullets citing the numbers), "
                         "**Citizen voice** (2 short representative quotes, translated), **Suggested convergence** "
                         "(relevant central/state schemes), **Estimated reach**, **Risks & next steps**. "
                         "Max 220 words. Evidence:\n" + json.dumps(ev, ensure_ascii=False, default=str),
                config=types.GenerateContentConfig(temperature=0.3))
            return resp.text.strip(), "gemini"
        except Exception as e:
            print("brief failed, falling back:", e)
    return _brief_offline(ev), "offline"


def _brief_offline(ev: dict) -> str:
    p = ev["priority"]
    quotes = "\n".join(f"- “{q}”" for q in list(dict.fromkeys(ev["sample_requests_en"]))[:2])
    if p["coverage_pct"] is not None:
        gap_line = f"- NFHS-5: only {p['coverage_pct']:.0f}% coverage ({p['indicator'].lower()})."
    else:
        gap_line = "- No official district indicator for this sector yet, so no gap points; ranked on citizen demand and population."
    reach = (f"~{p['people_without']:,} people without this service (Census 2011 population x NFHS-5 gap)."
             if p["people_without"] else "Population figure not available (district created after 2011).")
    return (
        f"**Recommendation:** Take up a {p['category_label'].lower()} project in **{p['district']}, {p['state']}** "
        f"under {p['scheme']}.\n\n"
        f"**Why now**\n"
        f"- {p['requests']} requests from {p['unique_citizens']} citizens ({p['distinct_issues']} distinct issues), "
        f"average urgency {p['avg_urgency']}/5; {p['trend']['last14']} in the last 14 days.\n"
        f"{gap_line}\n"
        f"- Priority score {p['score']} (rank #{p['rank']} nationally).\n\n"
        f"**Citizen voice**\n{quotes}\n\n"
        f"**Estimated reach:** {reach}\n\n"
        f"**Next steps:** field check by the district office; match with the state budget line.\n\n"
        f"_Template brief. Gemini writes this when an API key is set._"
    )
