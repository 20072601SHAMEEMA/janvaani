"""SQLite storage and sample data.

districts  - real data: NFHS-5 indicators + Census 2011 population (built by data/build_districts.py)
requests   - citizen requests. Live submissions are real; the starting set is clearly marked sample data
             (ai_mode = 'sample') because real individual complaints are private and not published.
"""
import csv
import hashlib
import json
import math
import os
import random
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import store
from .lang import CATEGORIES, STATE_LANGUAGE, TEMPLATES

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("DB_PATH", ROOT / "data" / "janvaani.db"))
SALT = os.environ.get("CITIZEN_SALT", "janvaani-demo-salt")
INDICATOR_CATS = [c for c, v in CATEGORIES.items() if v[2]]  # categories with a real NFHS-5 indicator

SCHEMA = """
CREATE TABLE IF NOT EXISTS districts (
    district TEXT PRIMARY KEY, state TEXT, lat REAL, lon REAL, population_2011 INTEGER,
    water REAL, sanitation REAL, power REAL, health REAL, education REAL, note TEXT
);
CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY, created_at TEXT, channel TEXT, citizen_hash TEXT,
    original_text TEXT, language TEXT, translation TEXT, category TEXT,
    urgency INTEGER, summary TEXT, location_text TEXT, state TEXT, district TEXT,
    lat REAL, lon REAL, sentiment TEXT, has_photo INTEGER, photo_note TEXT,
    status TEXT, cluster_id TEXT, embedding TEXT, ai_mode TEXT
);
CREATE INDEX IF NOT EXISTS idx_req_dc ON requests (district, category);
CREATE INDEX IF NOT EXISTS idx_req_state ON requests (state);
CREATE TABLE IF NOT EXISTS briefs (key TEXT PRIMARY KEY, text TEXT, created_at TEXT);
"""


def connect(readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def citizen_hash(contact: str) -> str:
    return hashlib.sha256((SALT + contact.strip()).encode()).hexdigest()[:16]


def new_ticket() -> str:
    return "JV-" + uuid.uuid4().hex[:8].upper()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect()
    conn.executescript(SCHEMA)
    if not conn.execute("SELECT COUNT(*) FROM districts").fetchone()[0]:
        load_districts(conn)
        add_sample_requests(conn)
    conn.close()
    store.init()
    restored = sum(_insert(rec, ignore=True) for rec in store.load_all())
    if store.enabled():
        print(f"Loaded {restored} live requests from Firestore")


def load_districts(conn):
    with open(ROOT / "data" / "districts.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Some names exist in two states (e.g. Aurangabad). Add the state so every district is unique.
    repeated = {n for n, k in Counter(r["district"] for r in rows).items() if k > 1}
    for r in rows:
        if r["district"] in repeated:
            r["district"] = f"{r['district']} ({r['state']})"
        r["population_2011"] = int(r["population_2011"]) if r["population_2011"] else None
    conn.executemany(
        "INSERT INTO districts VALUES (:district,:state,:lat,:lon,:population_2011,"
        ":water,:sanitation,:power,:health,:education,:note)", rows)
    conn.commit()


def add_sample_requests(conn, seed: int = 42):
    """Sample citizen requests so the dashboard is not empty on day one.

    How they are made (so it can be explained honestly):
      - every district gets a few requests, more for bigger populations;
      - the category of each request follows that district's REAL NFHS-5 gaps
        (a district with 30% sanitation gets many more sanitation requests than one with 95%);
      - in each sector, the 2 districts with the largest real gap x population get a recent surge,
        so the demo shows emerging hotspots that the real data supports;
      - the text comes from sample sentences in 12 Indian languages (app/lang.py).
    """
    rng = random.Random(seed)
    districts = [dict(r) for r in conn.execute("SELECT * FROM districts")]
    now = datetime.now(timezone.utc)
    citizens = [citizen_hash(f"sample-citizen-{i}") for i in range(4000)]
    rows = []

    def gap(d, cat):
        return (100 - d[cat]) if CATEGORIES[cat][2] else 25  # roads/digital: no official indicator

    def make(d, cat, recent=False):
        state_lang = STATE_LANGUAGE.get(d["state"], "hi")
        r = rng.random()
        lang = state_lang if r < 0.7 else ("hi" if r < 0.85 else "en")
        pool = [v for v in TEMPLATES[cat] if lang in v["texts"]] or TEMPLATES[cat]
        v = rng.choice(pool)
        if lang not in v["texts"]:
            lang = "en"
        block = rng.randint(1, 5)
        age = rng.uniform(0, 14) if recent else min(rng.expovariate(1 / 40), 120)
        urgency = max(1, min(5, v["urgency"] + rng.choice([-1, 0, 0, 0, 1])))
        rows.append((
            new_ticket(), (now - timedelta(days=age, minutes=rng.randint(0, 1440))).isoformat(timespec="seconds"),
            rng.choices(["web", "voice", "whatsapp", "telegram", "sms"], [30, 25, 25, 10, 10])[0],
            rng.choice(citizens), v["texts"][lang], lang, v["en"], cat, urgency, v["summary"],
            f"Block {block}, {d['district']}", d["state"], d["district"],
            d["lat"] + rng.uniform(-0.12, 0.12), d["lon"] + rng.uniform(-0.12, 0.12),
            "negative" if urgency >= 4 else "concerned", 0, None,
            rng.choices(["received", "under_review", "forwarded", "resolved"], [50, 25, 15, 10])[0],
            f"{d['district']}|{cat}|{TEMPLATES[cat].index(v)}|{block}", None, "sample",
        ))

    cats = list(CATEGORIES)
    for d in districts:
        pop = d["population_2011"] or 1_000_000
        n = max(2, int(2 + 3 * math.sqrt(pop / 1e6) * rng.uniform(0.6, 1.4)))
        weights = [gap(d, c) ** 1.5 + 3 for c in cats]
        for _ in range(n):
            make(d, rng.choices(cats, weights)[0])

    # Recent surges where the real data shows the largest need
    used = set()
    for cat in INDICATOR_CATS:
        worst = sorted(districts, key=lambda d: gap(d, cat) * math.sqrt(d["population_2011"] or 0), reverse=True)
        for d in [d for d in worst if d["district"] not in used][:2]:
            used.add(d["district"])
            for _ in range(rng.randint(18, 32)):
                make(d, cat, recent=True)

    conn.executemany(f"INSERT INTO requests VALUES ({','.join('?' * 22)})", rows)
    conn.commit()


def rows(sql: str, params=()) -> list[dict]:
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


REQUEST_COLS = ["id", "created_at", "channel", "citizen_hash", "original_text", "language", "translation",
                "category", "urgency", "summary", "location_text", "state", "district", "lat", "lon",
                "sentiment", "has_photo", "photo_note", "status", "cluster_id", "embedding", "ai_mode"]


def _insert(rec: dict, ignore: bool = False) -> int:
    """Write one request to SQLite. Returns 1 if a new row was added."""
    values = [json.dumps(rec[c]) if c == "embedding" and isinstance(rec.get(c), list) else rec.get(c)
              for c in REQUEST_COLS]
    conn = connect()
    try:
        cur = conn.execute(f"INSERT {'OR IGNORE ' if ignore else ''}INTO requests ({','.join(REQUEST_COLS)}) "
                           f"VALUES ({','.join('?' * len(REQUEST_COLS))})", values)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def insert_request(rec: dict):
    """A new live request: saved locally for ranking and in Firestore so it is never lost."""
    _insert(rec)
    store.save({c: rec.get(c) for c in REQUEST_COLS})
