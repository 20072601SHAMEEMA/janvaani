# Demo video script (about 4 minutes)

**0:00–0:25 · Hook** (dashboard on screen)
"Every day, citizens across India ask for water, roads, doctors, in Telugu, Bhojpuri, Odia, Assamese. Those requests are
scattered across systems and never meet the data planners use. JanVaani fixes that, with Google Gemini."

**0:25–1:30 · Citizen side** (`/submit`)
1. Tap the mic and speak in your language (e.g. Telugu or Hindi): describe a water or road problem in your village.
2. Submit and show: detected language, "we heard" transcript, English translation, category → scheme, urgency, district.
3. The acknowledgement is spoken back in the citizen's language. Point out the ticket number.
4. Show "N citizens have reported this same issue" (embedding-based deduplication).
5. Click the **Hinglish** sample to show code-mixed text understood, with the district picked up from the message.

**1:30–2:50 · Policymaker side** (`/`)
1. KPIs: requests, citizens, languages, districts.
2. Map: hotspots and dashed "emerging" circles. Hover Araria.
3. Ranking: #1 Araria drinking water. Explain the coloured bar: demand, infra gap, reach, funding gap, equity.
4. Open it: 49 requests, 38% tap coverage, ₹ sanctioned, issue clusters, original-language quotes with translations.
5. Click **Generate brief with Gemini** and read the recommendation line.
6. Move the **Infra gap** slider up: the ranking reorders live. "Each ministry sets its own policy mix; every score is auditable."

**2:50–3:30 · Ask the data**
Type "Which aspirational districts have the lowest road coverage but high demand?" Show the answer, then expand the generated SQL.
Mention the read-only sandbox and privacy masking.

**3:30–4:00 · Scale & close**
Architecture slide: Cloud Run + Gemini + BigQuery path; state onboarding by config; Telegram channel live, WhatsApp/IVR next.
"JanVaani: every voice counted, every rupee justified."

Recording tips: record at 1280×720 in Chrome; turn on Gemini mode first; pre-warm by submitting one request before recording.
