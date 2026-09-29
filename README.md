# JanVaani — जनवाणी · "Voice of the People"

**A multilingual, AI-powered Digital Public Good that turns citizens' development requests — by voice, text,
photo or messaging app, in any Indian language — into ranked, evidence-backed infrastructure priorities for policymakers.**

Built for *Build with AI: Code for Communities (2nd Edition)* — AI & Governance track.

> Citizens speak in 22 languages across 780+ districts. Budgets are decided in a handful of offices.
> JanVaani is the bridge: Gemini listens to every voice, fuses it with demographic, infrastructure and
> investment data, and tells planners *where* the next rupee should go — and *why*.

## What it does

| For citizens | For policymakers |
|---|---|
| 🎙️ Speak or type in any Indian language (Hinglish too) | 🗺️ Live hotspot map of demand across districts |
| 📷 Attach a photo as evidence | 🏆 Ranked priority projects with a transparent score breakdown |
| 🎫 Instant ticket + spoken acknowledgement in their own language | 🎚️ Policy-weight sliders — each ministry/state sets its own mix |
| 🔁 "N others reported this" — duplicates merge into one stronger signal | 💬 *Ask the data* — plain-language questions → safe SQL → answer |
| 📍 Track status by ticket | 📝 One-click Gemini policy brief per project |
| 💬 Telegram bot channel (WhatsApp-ready design) | 📈 Emerging-surge detection (last 14 days vs prior) |

## How Google AI is used

| Job | Google AI | Where |
|---|---|---|
| Understand voice/text/photo in any Indian language → transcript, translation, category, urgency, location, sentiment, reply in citizen's language — **one multimodal call with a JSON schema** | Gemini 2.5 Flash (structured output) | `app/ai.py · analyse()` |
| Merge duplicate reports into issue clusters | Gemini embeddings (`gemini-embedding-001`) | `app/ai.py · embed()`, `app/main.py · _assign_cluster()` |
| Plain-language analytics for officials | Gemini NL→SQL + answer summarisation | `app/ai.py · nl_to_sql()` |
| Decision brief per recommended project | Gemini | `app/ai.py · policy_brief()` |

Without a key the app runs in **offline demo mode** (script-based language detection + keyword rules), so it never breaks mid-demo.

## Priority score (auditable, not a black box)

```
score = 100 × ( 0.40·Demand + 0.30·Gap + 0.15·Reach + 0.15·FundingGap ) + 3 if aspirational district
```
- **Demand** — urgency- and recency-weighted citizen requests (45-day decay), nationally normalised
- **Gap** — infrastructure deficit from the district indicator (100 − coverage %)
- **Reach** — population benefiting (log-scaled)
- **FundingGap** — how little is already sanctioned per capita under the flagship scheme
- Weights are adjustable per ministry/state via the dashboard or `?w_demand=…` API params.

## Run locally (2 minutes)

```bash
pip install -r requirements.txt
cp .env.example .env        # then paste your key from https://aistudio.google.com/apikey
python -m uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000 (dashboard) and http://localhost:8000/submit (citizen portal).
The demo database is seeded automatically on first start (delete `data/janvaani.db` to reseed).

## Deploy to Google Cloud Run (from Cloud Shell — nothing to install)

1. Open https://console.cloud.google.com → select/create a project → click **Activate Cloud Shell**.
2. Run:
   ```bash
   git clone https://github.com/<you>/janvaani.git && cd janvaani
   gcloud run deploy janvaani --source . --region asia-south1 --allow-unauthenticated \
     --set-env-vars GEMINI_API_KEY=<your-key>
   ```
3. The command prints your live URL. (For production, store the key in Secret Manager and use `--set-secrets`.)

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/requests` | Multipart intake: `text`, `audio`, `photo`, `state`, `district`, `lat`, `lon`, `contact`, `channel` |
| GET | `/api/requests/{ticket}` | Track status |
| GET | `/api/priorities` | Ranked projects (`state`, `category`, `w_demand`, `w_gap`, `w_reach`, `w_funding`, `limit`) |
| GET | `/api/hotspots` | District-level map data |
| GET | `/api/project/{district}/{category}` | Evidence pack for one project |
| POST | `/api/project/{district}/{category}/brief` | Generate Gemini policy brief |
| POST | `/api/ask` | `{question}` → SQL + rows + answer |
| GET | `/api/stats`, `/api/meta`, `/api/health` | Dashboard data |
| POST | `/webhook/telegram/{secret}` | Telegram bot (set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`) |

Interactive docs at `/docs`.

## Data

- `data/districts.csv` — 44 districts across 20 states/UTs, incl. NITI Aayog aspirational districts. Populations approximate
  Census 2011. **Infrastructure indices and sanctioned-investment figures are illustrative**, modelled on public indicators
  (Jal Jeevan Mission, PMGSY, NFHS-5, UDISE+, BharatNet). The schema is designed to take data.gov.in exports directly.
- Seed requests (~1,180) are generated from native-language templates in 12 languages with planted emerging hotspots.

## Privacy & safety by design

- Citizen phone numbers are stored only as salted SHA-256 hashes.
- *Ask the data* runs on a **read-only** connection with an SQLite authorizer that denies writes and masks raw citizen text,
  identifiers and coordinates; queries are time-boxed.
- All user content is HTML-escaped in the UI.

## Repository layout

```
app/        FastAPI backend: main.py (API), ai.py (Gemini), priority.py (scoring), db.py (storage+seed), lang.py
static/     Dashboard (index.html, dashboard.js), citizen portal (submit.html, submit.js), style.css
data/       District indicators CSV
docs/       Architecture, pitch deck outline, demo script, submission text
```

## Open-source credits

FastAPI, Uvicorn, Pydantic, Google Gen AI SDK, Leaflet, OpenStreetMap tiles. Licensed under MIT (see LICENSE).
