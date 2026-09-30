"""Priority score for every district x sector that has citizen requests.

score = 100 x (0.50 x Demand + 0.35 x Gap + 0.15 x Reach)

  Demand  citizen requests, weighted by urgency (1-5) and how recent they are
  Gap     100 - the district's real NFHS-5 coverage for that sector
          (roads and digital have no NFHS-5 indicator, so they get no gap points)
  Reach   Census 2011 population (log scale); districts created after 2011 get the median

Every part is returned with the score so anyone can check why a project ranks where it does.
The weights can be changed from the dashboard (or ?w_demand=&w_gap=&w_reach= on the API).
"""
import math
import statistics
from datetime import datetime, timezone

from . import db
from .lang import CATEGORIES

DEFAULT_WEIGHTS = {"demand": 0.50, "gap": 0.35, "reach": 0.15}
RECENCY_DAYS = 45


def compute(weights: dict | None = None, state: str | None = None, category: str | None = None) -> list[dict]:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    districts = {d["district"]: d for d in db.rows("SELECT * FROM districts")}
    requests = db.rows("SELECT district, category, urgency, created_at, citizen_hash, cluster_id FROM requests "
                       "WHERE status != 'needs_review'")  # spam / unclear messages never add to demand
    now = datetime.now(timezone.utc)

    groups = {}
    for r in requests:
        if r["district"] not in districts or r["category"] not in CATEGORIES:
            continue
        g = groups.setdefault((r["district"], r["category"]), {
            "n": 0, "demand": 0.0, "urgency": 0, "citizens": set(), "issues": set(), "last14": 0, "prev14": 0})
        age = (now - datetime.fromisoformat(r["created_at"])).total_seconds() / 86400
        g["n"] += 1
        g["urgency"] += r["urgency"]
        g["demand"] += (r["urgency"] / 5) * math.exp(-max(age, 0) / RECENCY_DAYS)
        g["citizens"].add(r["citizen_hash"])
        g["issues"].add(r["cluster_id"])
        if age <= 14:
            g["last14"] += 1
        elif age <= 28:
            g["prev14"] += 1
    if not groups:
        return []

    max_demand = max(g["demand"] for g in groups.values())
    log_pops = [math.log(d["population_2011"]) for d in districts.values() if d["population_2011"]]
    lo, hi, median = min(log_pops), max(log_pops), statistics.median(log_pops)

    out = []
    for (name, cat), g in groups.items():
        d = districts[name]
        if (state and d["state"] != state) or (category and cat != category):
            continue
        coverage = d[cat] if CATEGORIES[cat][2] else None
        parts = {
            "demand": math.sqrt(g["demand"] / max_demand),
            "gap": (100 - coverage) / 100 if coverage is not None else None,
            "reach": ((math.log(d["population_2011"]) if d["population_2011"] else median) - lo) / (hi - lo),
        }
        # A sector without an official indicator (roads, digital) simply gets no gap points
        total_w = sum(w.values()) or 1
        contributions = {k: round(100 * w[k] / total_w * v, 1) for k, v in parts.items() if v is not None}
        out.append({
            "district": name, "state": d["state"], "category": cat,
            "category_label": CATEGORIES[cat][0], "scheme": CATEGORIES[cat][1], "indicator": CATEGORIES[cat][2],
            "score": round(sum(contributions.values()), 1),
            "components": {k: (round(v, 3) if v is not None else None) for k, v in parts.items()},
            "contributions": contributions,
            "requests": g["n"], "unique_citizens": len(g["citizens"]), "distinct_issues": len(g["issues"]),
            "avg_urgency": round(g["urgency"] / g["n"], 2),
            "trend": {"last14": g["last14"], "prev14": g["prev14"]},
            "emerging": g["last14"] >= 10 and g["last14"] >= 2 * max(g["prev14"], 1),
            "coverage_pct": coverage, "population_2011": d["population_2011"],
            "people_without": int(d["population_2011"] * (100 - coverage) / 100)
            if coverage is not None and d["population_2011"] else None,
            "lat": d["lat"], "lon": d["lon"],
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out
