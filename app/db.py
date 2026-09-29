"""SQLite storage + demo seed.

SQLite keeps the prototype a single container. The schema maps 1:1 onto
BigQuery tables for national scale (see docs/ARCHITECTURE.md).
"""
import csv
import hashlib
import json
import math
import os
import random
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .lang import CATEGORIES, STATE_LANGUAGE, TEMPLATES

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("DB_PATH", ROOT / "data" / "janvaani.db"))
SALT = os.environ.get("CITIZEN_SALT", "janvaani-demo-salt")

SCHEMA = """
CREATE TABLE IF NOT EXISTS districts (
    district TEXT PRIMARY KEY, state TEXT, lat REAL, lon REAL, population INTEGER,
    aspirational INTEGER, water REAL, roads REAL, health REAL, education REAL,
    power REAL, sanitation REAL, digital REAL
);
CREATE TABLE IF NOT EXISTS investments (
    district TEXT, category TEXT, scheme TEXT, sanctioned_cr REAL,
    PRIMARY KEY (district, category)
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

SCHEMES = {c: v[2] for c, v in CATEGORIES.items()}
# Illustrative sanctioned investment, INR crore per lakh population
BASE_RATE = {"water": 6.0, "roads": 8.0, "health": 4.0, "education": 3.5, "power": 5.0,
             "sanitation": 2.5, "digital": 1.5}

# Planted demand spikes so the demo shows clear, recent hotspots
SPIKES = {("Araria", "water"): 45, ("Malkangiri", "roads"): 40, ("Barmer", "water"): 40,
          ("Bahraich", "health"): 38, ("Kupwara", "digital"): 25, ("Chennai", "sanitation"): 30,
          ("Bengaluru Urban", "roads"): 30, ("Pashchimi Singhbhum", "health"): 28,
          ("Dhubri", "roads"): 26, ("Nandurbar", "health"): 24, ("Raichur", "water"): 22,
          ("Gadchiroli", "digital"): 20}


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


def init_db(force_seed: bool = False):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect()
    conn.executescript(SCHEMA)
    has_rows = conn.execute("SELECT COUNT(*) FROM districts").fetchone()[0]
    if force_seed or not has_rows:
        _seed(conn)
    conn.close()


def _seed(conn, seed: int = 42):
    rng = random.Random(seed)
    conn.execute("DELETE FROM districts")
    conn.execute("DELETE FROM investments")
    conn.execute("DELETE FROM requests")
    conn.execute("DELETE FROM briefs")

    with open(ROOT / "data" / "districts.csv", encoding="utf-8") as f:
        districts = list(csv.DictReader(f))
    conn.executemany(
        "INSERT INTO districts VALUES (:district,:state,:lat,:lon,:population,:aspirational,"
        ":water,:roads,:health,:education,:power,:sanitation,:digital)", districts)

    for d in districts:
        lakh = int(d["population"]) / 1e5
        for cat in CATEGORIES:
            # Better-served districts tend to have more sanctioned spend already
            coverage = float(d[CATEGORIES[cat][1]]) / 100
            amount = lakh * BASE_RATE[cat] * (0.4 + coverage) * rng.uniform(0.6, 1.4)
            conn.execute("INSERT INTO investments VALUES (?,?,?,?)",
                         (d["district"], cat, SCHEMES[cat], round(amount, 1)))

    now = datetime.now(timezone.utc)
    citizens = [citizen_hash(f"+91{rng.randint(6000000000, 9999999999)}") for _ in range(1400)]
    rows = []

    def make(d, cat, recent=False):
        variants = TEMPLATES[cat]
        state_lang = STATE_LANGUAGE.get(d["state"], "hi")
        r = rng.random()
        lang = state_lang if r < 0.68 else ("hi" if r < 0.84 else "en")
        pool = [v for v in variants if lang in v["texts"]] or variants
        # urban districts lean on the second (urban) variant
        urban = float(d["digital"]) > 70
        v = pool[-1] if (urban and len(pool) > 1 and rng.random() < 0.6) else pool[0]
        if lang not in v["texts"]:
            lang = "en"
        block = rng.randint(1, 6)
        age = rng.uniform(0, 14) if recent else rng.expovariate(1 / 35)
        age = min(age, 120)
        created = now - timedelta(days=age, minutes=rng.randint(0, 1440))
        urgency = max(1, min(5, v["urgency"] + rng.choice([-1, 0, 0, 0, 1])))
        idx = TEMPLATES[cat].index(v)
        rows.append((
            new_ticket(), created.isoformat(timespec="seconds"),
            rng.choices(["web", "voice", "whatsapp", "telegram", "sms"], [30, 25, 25, 10, 10])[0],
            rng.choice(citizens), v["texts"][lang], lang, v["en"], cat, urgency, v["summary"],
            f"Block {block}, {d['district']}", d["state"], d["district"],
            float(d["lat"]) + rng.uniform(-0.25, 0.25), float(d["lon"]) + rng.uniform(-0.25, 0.25),
            "negative" if urgency >= 4 else "concerned", 0, None,
            rng.choices(["received", "under_review", "forwarded", "resolved"], [50, 25, 15, 10])[0],
            f"{d['district']}|{cat}|{idx}|{block}", None, "seed",
        ))

    for d in districts:
        pop = int(d["population"])
        n = int(8 + 7 * math.sqrt(pop / 1e6) * rng.uniform(0.7, 1.3))
        gaps = {c: (100 - float(d[CATEGORIES[c][1]])) ** 1.6 + 5 for c in CATEGORIES}
        cats = list(gaps)
        for _ in range(n):
            make(d, rng.choices(cats, [gaps[c] for c in cats])[0])
    by_name = {d["district"]: d for d in districts}
    for (dist, cat), n in SPIKES.items():
        for _ in range(n):
            make(by_name[dist], cat, recent=True)

    conn.executemany(f"INSERT INTO requests VALUES ({','.join('?' * 22)})", rows)
    conn.commit()


def rows(sql: str, params=()) -> list[dict]:
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def insert_request(rec: dict):
    cols = ["id", "created_at", "channel", "citizen_hash", "original_text", "language", "translation",
            "category", "urgency", "summary", "location_text", "state", "district", "lat", "lon",
            "sentiment", "has_photo", "photo_note", "status", "cluster_id", "embedding", "ai_mode"]
    conn = connect()
    try:
        conn.execute(f"INSERT INTO requests ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                     [json.dumps(rec[c]) if c == "embedding" and rec.get(c) is not None else rec.get(c)
                      for c in cols])
        conn.commit()
    finally:
        conn.close()
