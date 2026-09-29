"""Transparent priority engine.

score = 100 * (w_demand*Demand + w_gap*Gap + w_reach*Reach + w_funding*FundingGap) + equity bonus

  Demand      urgency- and recency-weighted citizen requests (sqrt-normalised nationally)
  Gap         infrastructure deficit from the district indicator (100 - coverage%)
  Reach       population that benefits (log-scaled)
  FundingGap  how little is already sanctioned per capita under the flagship scheme
  Equity      +3 points for NITI Aayog aspirational districts

Every component is returned with the score so any recommendation can be audited.
Weights are query parameters so each state/ministry can apply its own policy mix.
"""
import math
from datetime import datetime, timezone

from . import db
from .lang import CATEGORIES

DEFAULT_WEIGHTS = {"demand": 0.40, "gap": 0.30, "reach": 0.15, "funding": 0.15}
RECENCY_DAYS = 45
EQUITY_BONUS = 3.0


def _age_days(ts: str, now: datetime) -> float:
    return max(0.0, (now - datetime.fromisoformat(ts)).total_seconds() / 86400)


def compute(weights: dict | None = None, state: str | None = None, category: str | None = None) -> list[dict]:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    total_w = sum(w.values()) or 1.0
    w = {k: v / total_w for k, v in w.items()}

    districts = {d["district"]: d for d in db.rows("SELECT * FROM districts")}
    invest = {(r["district"], r["category"]): r for r in db.rows("SELECT * FROM investments")}
    reqs = db.rows("SELECT district, category, urgency, created_at, citizen_hash, cluster_id FROM requests")

    now = datetime.now(timezone.utc)
    groups: dict[tuple, dict] = {}
    for r in reqs:
        if r["district"] not in districts or r["category"] not in CATEGORIES:
            continue
        g = groups.setdefault((r["district"], r["category"]), {
            "n": 0, "demand_raw": 0.0, "urg_sum": 0, "citizens": set(), "clusters": set(),
            "last14": 0, "prev14": 0})
        age = _age_days(r["created_at"], now)
        g["n"] += 1
        g["urg_sum"] += r["urgency"]
        g["demand_raw"] += (r["urgency"] / 5) * math.exp(-age / RECENCY_DAYS)
        g["citizens"].add(r["citizen_hash"])
        g["clusters"].add(r["cluster_id"])
        if age <= 14:
            g["last14"] += 1
        elif age <= 28:
            g["prev14"] += 1
    if not groups:
        return []

    max_demand = max(g["demand_raw"] for g in groups.values()) or 1
    pops = [math.log(d["population"]) for d in districts.values()]
    pmin, pmax = min(pops), max(pops)
    per_lakh = {}
    for (dist, cat), inv in invest.items():
        per_lakh[(dist, cat)] = inv["sanctioned_cr"] / (districts[dist]["population"] / 1e5)
    max_per_lakh = {c: max((v for (d, cc), v in per_lakh.items() if cc == c), default=1) for c in CATEGORIES}

    out = []
    for (dist, cat), g in groups.items():
        d = districts[dist]
        if state and d["state"] != state:
            continue
        if category and cat != category:
            continue
        indicator = d[CATEGORIES[cat][1]]
        comp = {
            "demand": math.sqrt(g["demand_raw"] / max_demand),
            "gap": (100 - indicator) / 100,
            "reach": (math.log(d["population"]) - pmin) / ((pmax - pmin) or 1),
            "funding": 1 - per_lakh.get((dist, cat), 0) / (max_per_lakh[cat] or 1),
        }
        bonus = EQUITY_BONUS if d["aspirational"] else 0.0
        score = 100 * sum(w[k] * comp[k] for k in comp) + bonus
        inv = invest.get((dist, cat), {})
        out.append({
            "district": dist, "state": d["state"], "category": cat,
            "category_label": CATEGORIES[cat][0], "scheme": CATEGORIES[cat][2],
            "score": round(score, 1),
            "components": {k: round(v, 3) for k, v in comp.items()},
            "contributions": {k: round(100 * w[k] * comp[k], 1) for k in comp} | {"equity": bonus},
            "requests": g["n"], "unique_citizens": len(g["citizens"]), "distinct_issues": len(g["clusters"]),
            "avg_urgency": round(g["urg_sum"] / g["n"], 2),
            "trend": {"last14": g["last14"], "prev14": g["prev14"]},
            "emerging": g["last14"] >= 10 and g["last14"] >= 2 * max(g["prev14"], 1),
            "indicator_pct": indicator, "population": d["population"],
            "aspirational": bool(d["aspirational"]),
            "sanctioned_cr": inv.get("sanctioned_cr"),
            "est_underserved": int(d["population"] * (100 - indicator) / 100),
            "lat": d["lat"], "lon": d["lon"],
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out
