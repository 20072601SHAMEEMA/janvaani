# Submission package

## Brief description (2–3 lines)
JanVaani lets citizens report local needs by voice, text or photo in any Indian language. Google Gemini understands,
translates and groups each request, and Cloud Firestore keeps every one. JanVaani combines these requests with real
NFHS-5 and Census 2011 data for all 705 districts, and gives planners a hotspot map, a ranked list of projects with
clear reasons, and AI-written policy briefs.

## Links
- Live app: https://janvaani-npik.onrender.com (citizen portal: https://janvaani-npik.onrender.com/submit)
- Source code: https://github.com/20072601SHAMEEMA/janvaani

## Google technology used
Gemini API (understanding voice, text and photos; answering planners' questions; writing briefs), Gemini embeddings
(grouping duplicate reports), Cloud Firestore / Firebase (storing citizen requests), Google Gen AI SDK.
Cloud Run deploy steps are in the README.

## Data declaration
- Real: NFHS-5 (2019–21) district indicators, Census 2011 population, Census 2011 district boundaries, OpenStreetMap.
- Sample: the starting citizen requests, because real complaints are private. They are tagged "sample";
  requests submitted in the app are tagged "live" and stored in Firestore.

## Checklist
- [x] Source code on GitHub
- [x] Live deployed link
- [x] Brief description (above)
- [x] Pitch deck, 12 slides (download as PDF)
- [ ] Demo video link (Drive "Anyone with the link" or YouTube "Unlisted")
