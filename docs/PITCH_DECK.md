# JanVaani — Pitch deck (12 slides)

**1. Title**
JanVaani · जनवाणी — *Every citizen's voice, every language, one national priority map.*
Build with AI: Code for Communities · AI & Governance · [Name] · [Live link] · [GitHub]

**2. The problem**
- Citizen requests arrive in 22+ languages through fragmented channels — grievance portals, letters, WhatsApp, gram sabhas.
- They are never joined with infrastructure data, so spending follows the loudest voice, not the greatest need.
- No way to measure whether digital public infrastructure is closing real gaps.

**3. Who we serve**
- Citizens, especially rural, low-literacy, non-English speakers: speak, don't fill forms.
- District collectors & line departments: a clean, deduplicated queue.
- State and national planners (NITI Aayog, ministries): ranked, justified project recommendations.

**4. The solution (one line)**
A multilingual AI platform that listens by voice, text, photo and chat, fuses that demand with demographic, infrastructure
and investment data, and recommends high-priority projects with evidence.

**5. Live demo flow** (screenshots)
Telugu voice note → ticket + spoken Telugu reply → appears on national map → Araria water ranks #1 → Gemini brief.

**6. How Google AI does the work**
- Gemini multimodal: audio + photo + text → structured JSON (transcript, translation, category, urgency, location, reply).
- Gemini embeddings: 49 complaints about one broken handpump become one strong signal, not 49 tickets.
- Gemini NL→SQL: "Which districts in Bihar need water most?" answered in seconds.
- Gemini policy brief: a decision note with numbers and citizen quotes.

**7. Transparent prioritisation**
score = 0.40 Demand + 0.30 Infra gap + 0.15 Population reach + 0.15 Funding gap (+ equity for aspirational districts).
Adjustable weights per ministry; every score comes with its breakdown. Explainable AI for public money.

**8. Architecture**
(diagram from docs/ARCHITECTURE.md) Channels → Cloud Run (FastAPI) → Gemini → Firestore/BigQuery → Dashboard.

**9. Built for India's scale**
- Language-agnostic by design: Gemini covers all major Indian languages plus code-mixed speech.
- Onboard a state by config: indicator CSV + scheme list + weights. No code changes.
- Stateless Cloud Run autoscaling; BigQuery for 780+ districts and millions of requests.
- Works on low bandwidth: 16 kHz WAV voice notes, a lightweight single-page UI.

**10. Impact**
- Pilot scope: 44 districts, 20 states, 12 languages in the prototype.
- Targets aspirational districts first (equity weight).
- Outcomes to track: time-to-acknowledge, % of requests mapped to a sanctioned project, gap closure per ₹ crore.

**11. Deployability: pilot in weeks**
- Open source (MIT), a Digital Public Good candidate; one container on Cloud Run.
- Week 1: load a state's data.gov.in exports. Week 2: connect WhatsApp/IVR. Week 3–4: district officer training and live pilot.
- Privacy by design: hashed identities, read-only analytics sandbox, no PII in AI answers.

**12. Roadmap & ask**
WhatsApp Business + IVR · Bhashini for dialects · BigQuery + Looker Studio · CPGRAMS integration · BRICS adaptation.
Ask: a pilot district cluster plus data-sharing MoU with one state planning department.
