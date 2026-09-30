# JanVaani — Architecture

## 1. System overview

```mermaid
flowchart LR
  subgraph Channels["Citizen channels"]
    W[Web / PWA<br/>voice · text · photo]
    T[Telegram bot]
    WA[WhatsApp Business API<br/><i>roadmap</i>]
    IVR[IVR / missed-call<br/><i>roadmap</i>]
  end

  subgraph Run["Cloud Run · FastAPI (stateless, autoscaling)"]
    I[/api/requests intake/]
    G1[Gemini multimodal<br/>transcribe · translate · classify<br/>urgency · location · reply]
    E[Gemini embeddings<br/>duplicate clustering]
    R[District resolver<br/>form · Gemini guess · GPS]
    P[Priority engine<br/>Demand + Gap + Population]
    Q[Ask-the-data<br/>Gemini NL→SQL · read-only sandbox]
    B[Gemini policy brief]
  end

  subgraph Data["Data layer"]
    REQ[(requests)]
    DIST[(705 districts<br/>NFHS-5 coverage · Census 2011 population)]
  end

  W & T & WA & IVR --> I --> G1 --> R --> E --> REQ
  REQ & DIST --> P --> D[Policymaker dashboard<br/>map · ranking · weights · briefs]
  D --> Q --> Data
  D --> B
  I -. ticket + spoken reply in citizen's language .-> W
```

## 2. Request lifecycle

1. **Capture** — the browser records audio and converts it to 16 kHz mono WAV client-side (small uploads that work on 2G/3G
   and a format Gemini accepts everywhere). Optional photo and GPS.
2. **Understand** — *one* Gemini call receives audio + photo + text and returns a schema-validated JSON:
   `transcript, language, translation_en, category, urgency, summary_en, location_mentioned, district_guess, state_guess,
   sentiment, photo_observation, acknowledgement, is_development_request`.
3. **Locate** — citizen-selected district → Gemini's district guess (fuzzy-matched) → district named in text → nearest
   district to GPS (≤200 km).
4. **Deduplicate** — the English translation is embedded (`gemini-embedding-001`, 256-d). Cosine ≥ 0.88 against the last
   60 days in the same district × sector joins an existing issue cluster; otherwise a new cluster starts.
5. **Store & acknowledge** — ticket `JV-XXXXXXXX`, reply in the citizen's language (spoken via the browser's TTS; Cloud
   Text-to-Speech on the roadmap for IVR).
6. **Prioritise** — every dashboard view recomputes the ranking with the requested policy weights.

## 3. Priority model

| Part | How it is calculated | Source |
|---|---|---|
| Citizen demand (50%) | √( Σ urgency/5 · e^(−age/45 days) ÷ national max ) | citizen requests |
| Gap (35%) | (100 − coverage %) / 100 | NFHS-5 (2019–21) district fact sheets |
| Population (15%) | min–max of ln(population) | Census 2011 |

Sectors with no NFHS-5 district indicator (roads, digital) get no gap points; demand and population still count.
Every recommendation shows its parts, and the weights are sliders on the dashboard.
**Emerging** flag: at least 10 requests in the last 14 days and at least 2× the previous 14 days.

## 4. Scaling from prototype to national

| Concern | Prototype | National deployment |
|---|---|---|
| Compute | 1 Cloud Run service | Cloud Run autoscaling per state/region; Pub/Sub queue between intake and AI analysis |
| Storage | SQLite (seeded at start) | Firestore for live tickets + **BigQuery** for analytics (same schema; NL→SQL targets BigQuery) |
| Geography | All 705 NFHS-5 districts, 34 states/UTs | LGD district codes; Google Maps Platform with India-compliant boundaries |
| Data | NFHS-5 + Census 2011 (real) | Add data.gov.in feeds: JJM tap connections, PMGSY roads, UDISE+ schools, BharatNet, scheme spend |
| Languages | Gemini (all major Indian languages) | + Bhashini / Cloud Speech-to-Text for low-resource dialects; Cloud TTS for IVR |
| Channels | Web, Telegram | WhatsApp Business API, IVR/missed-call, CPGRAMS & state grievance portal import |
| Identity | Hashed phone | Optional DigiLocker/Aadhaar-free OTP; no PII in analytics layer |
| Governance | Open code | DPG registry, per-state config (weights, categories, schemes), audit log of recommendations |

**Multi-tenant by config, not code**: a state onboards by uploading its district indicator CSV and scheme list and setting
policy weights — no code changes. The same design extends to other BRICS countries (swap the admin-unit table, languages
and schemes).

## 5. Security & privacy

- Salted hashes instead of phone numbers; raw text is never exposed through free-form analytics.
- Ask-the-data: read-only connection, SQLite authorizer (SELECT/READ/FUNCTION only; private columns masked), statement
  validation, progress-handler timeout, 200-row cap.
- Uploads capped at 8 MB; all rendered content escaped.
- Gemini API key via environment/Secret Manager; never in the client.
