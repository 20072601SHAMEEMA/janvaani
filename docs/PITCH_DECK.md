# JanVaani: Pitch deck (12 slides)

**1. Title**
JanVaani (जनवाणी), Voice of the People. *Every citizen's voice, in every language, on one national priority map.*
AI & Governance track · [Your name] · [Live link] · [GitHub link]

**2. The problem**
- Citizens raise needs in many languages, through many separate channels.
- These requests are never matched with government data about where services are missing.
- So money often goes where the loudest voice is, not where the need is greatest.

**3. Who it helps**
- Citizens, especially rural and non-English speakers: they can just speak.
- District officers: one clean list, with duplicates merged.
- State and national planners: a ranked list of projects with clear reasons.

**4. Our solution**
A multilingual AI platform that collects requests by voice and text, understands them with Gemini, combines them with
real NFHS-5 and Census data for all 705 districts, and recommends which projects to fund first.

**5. Demo in one line**
Hindi voice/text request about no toilets → ticket + reply in Hindi → shows up in Saran, Bihar → Saran sanitation
ranks near the top (NFHS-5: only 37% coverage) → Gemini writes the policy brief.

**6. How Google AI does the work**
- Gemini: voice/text/photo in any Indian language → translation, category, urgency, location, reply.
- Gemini embeddings: many reports of the same problem become one strong signal.
- Gemini: planners ask questions in plain English and get answers from the data.
- Gemini: writes a short, evidence-based policy brief.

**7. Real data, clear scoring**
- NFHS-5 (2019–21): drinking water, sanitation, electricity, institutional births, girls' schooling, for 705 districts.
- Census 2011 population.
- Score = 50% citizen demand + 35% gap (NFHS-5) + 15% population. Every score shows its breakdown; weights are adjustable.

**8. Architecture**
Channels (web, voice, Telegram) → Cloud Run (FastAPI) → Gemini → database → planner dashboard. (Diagram in docs/ARCHITECTURE.md.)

**9. Built for all of India**
- Already covers all 705 NFHS-5 districts across 34 states/UTs.
- Gemini understands all major Indian languages, including mixed Hindi-English.
- New data sources (Jal Jeevan Mission, PMGSY, UDISE+) can be added as extra columns.
- Runs in one container; Cloud Run scales it automatically.

**10. Impact**
- The real data shows large gaps, e.g. sanitation below 40% in districts like Puruliya, Araria and Saran.
- JanVaani links those gaps to what people are actually asking for, so action can start where both are high.

**11. Ready to pilot**
- Open source (MIT), one container on Cloud Run.
- Week 1: set up for one state. Week 2: connect WhatsApp/phone line. Weeks 3–4: train district officers and go live.
- Privacy: no phone numbers stored, and the question feature can only read data.

**12. Next steps and ask**
WhatsApp + phone (IVR) channels · more government datasets · integration with grievance portals.
Ask: one pilot district cluster with a state planning department.

**Be clear about data in the talk:** coverage and population are real; the starting requests are sample data because
real complaints are private; requests submitted through the app are real.
