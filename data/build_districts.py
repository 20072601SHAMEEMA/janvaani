"""Build data/districts.csv from real public sources.

Run:  pip install pyshp openpyxl   then   python data/build_districts.py

Sources (downloaded by this script):
  1. NFHS-5 (2019-21) district fact sheets, Ministry of Health & Family Welfare / IIPS,
     as extracted to CSV by jvargh7/nfhs5_factsheets (MIT licence).
  2. Census 2011 Primary Census Abstract (district totals), Office of the Registrar General of India.
  3. Census 2011 district boundaries, datameet/maps (MIT licence) - used for map points.
  4. OpenStreetMap Nominatim - map points only for the districts created after 2011.
"""
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / ".cache"

NFHS_URL = "https://raw.githubusercontent.com/jvargh7/nfhs5_factsheets/main/data%20for%20analysis/districts.csv"
CENSUS_URL = "https://raw.githubusercontent.com/adarshg17192-bit/iddi/main/data/raw/DDW_PCA0000_2011_Indiastatedist.xlsx"
SHAPE_URL = "https://raw.githubusercontent.com/datameet/maps/master/Districts/Census_2011/2011_Dist."

# The NFHS-5 indicator we use for each category (share of people who HAVE the service)
INDICATORS = {
    "water": "8. Population living in households with an improved drinking-water source1 (%)",
    "sanitation": "9. Population living in households that use an improved sanitation facility2 (%)",
    "power": "7. Population living in households with electricity (%)",
    "health": "42. Institutional births (%)",
    "education": "1. Female population age 6 years and above who ever attended school (%)",
}

# NFHS-5 state name -> Census 2011 state name(s)
CENSUS_STATE = {
    "Andaman Nicobar Islands": ["Andaman & Nicobar Island"], "Arunachal Pradesh": ["Arunanchal Pradesh"],
    "Dadra Nagar Haveli Daman Diu": ["Dadara & Nagar Havelli", "Daman & Diu"],
    "Jammu Kashmir": ["Jammu & Kashmir"], "Ladakh": ["Jammu & Kashmir"], "NCT Delhi": ["NCT of Delhi"],
    "Telangana": ["Andhra Pradesh"],
}
NICE_STATE = {"Andaman Nicobar Islands": "Andaman and Nicobar Islands", "Jammu Kashmir": "Jammu and Kashmir",
              "Dadra Nagar Haveli Daman Diu": "Dadra and Nagar Haveli and Daman and Diu", "NCT Delhi": "Delhi"}

# Same district, different spelling or an official rename (NFHS-5 name -> Census 2011 name). Checked by hand.
RENAMED = {
    "Buxer": "Buxar", "Saran": "Saran (chhapra)", "Dantewada": "Dakshin Bastar Dantewada", "Dahod": "Dohad",
    "Pauri Garhwal": "Garhwal", "Prayagraj": "Allahabad", "Khandwa (East Nimar)": "East Nimar",
    "Khargone (West Nimar)": "West Nimar", "North Twenty Four Parganas": "North 24 Parganas",
    "South Twenty Four Parganas": "South 24 Parganas", "East District": "East", "North  District": "North",
    "South District": "South", "West District": "West", "Ahmedabad": "Ahmadabad", "Panchmahal": "Panch Mahals",
    "Chamarajanagar": "Chamrajnagar", "Gadchiroli": "Garhchiroli", "Morigaon": "Marigaon",
    "Lawngtlai": "Lawangtlai", "Nagapattinam": "Nagappattinam", "Virudhunagar": "Virudunagar",
    "Mahabubnagar": "Mahbubnagar", "Kanshiram Nagar": "Kansiram Nagar", "Mahrajganj": "Maharajganj",
    "Darjeeling": "Darjiling", "Paschim Medinipur": "Pashchim Medinipur",
}
# OpenStreetMap spelling for a few new districts
OSM_NAME = {"South Salmara Mancachar": "South Salmara-Mankachar", "Aravali": "Aravalli",
            "East Jantia Hills": "East Jaintia Hills", "Paschim Barddhaman": "Paschim Bardhaman"}


def download(url, name):
    CACHE.mkdir(exist_ok=True)
    path = CACHE / name
    if not path.exists():
        print("downloading", url)
        urllib.request.urlretrieve(url, path)
    return path


def key(name):
    return re.sub(r"[^a-z]", "", name.lower().replace("&", "and"))


def centroid(shape):
    """Centre of a district polygon (shoelace formula) as (lat, lon)."""
    pts, parts = shape.points, list(shape.parts) + [len(shape.points)]
    area = cx = cy = 0.0
    for a, b in zip(parts[:-1], parts[1:]):
        ring = pts[a:b]
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            f = x1 * y2 - x2 * y1
            area += f
            cx += (x1 + x2) * f
            cy += (y1 + y2) * f
    return cy / (3 * area), cx / (3 * area)


def census_districts():
    import openpyxl
    import shapefile

    population = {}
    book = openpyxl.load_workbook(download(CENSUS_URL, "census2011_pca.xlsx"), read_only=True)
    for row in book.active.iter_rows(min_row=2, values_only=True):
        if row[6] == "DISTRICT" and row[8] == "Total":
            population[int(row[1])] = int(row[10])

    for ext in ("shp", "shx", "dbf"):
        download(SHAPE_URL + ext, "2011_Dist." + ext)
    by_state = defaultdict(dict)
    for item in shapefile.Reader(str(CACHE / "2011_Dist")).iterShapeRecords():
        name, state, _, _, code = item.record
        lat, lon = centroid(item.shape)
        by_state[state][key(name)] = {"population": population.get(int(code or 0), ""),
                                      "lat": round(lat, 4), "lon": round(lon, 4)}
    return by_state


def geocode(district, state):
    """Map point for a district created after 2011, from OpenStreetMap (1 request per second)."""
    q = f"{OSM_NAME.get(district, district.replace('  ', ' '))} district, {state}, India"
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": q, "format": "json", "limit": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "JanVaani-prototype/1.0 (district map points)"})
    time.sleep(1.1)
    found = json.loads(urllib.request.urlopen(req, timeout=20).read())
    return (round(float(found[0]["lat"]), 4), round(float(found[0]["lon"]), 4)) if found else ("", "")


def main():
    nfhs = defaultdict(dict)
    with open(download(NFHS_URL, "nfhs5_districts.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for cat, indicator in INDICATORS.items():
                if row["Indicator"] == indicator and row["NFHS5"] not in ("", "NA"):
                    nfhs[(row["state"], row["district"])][cat] = float(row["NFHS5"])

    census = census_districts()
    out = []
    for (state, district), values in sorted(nfhs.items()):
        pool = {}
        for s in CENSUS_STATE.get(state, [state]):
            pool.update(census[s])
        match = pool.get(key(district)) or pool.get(key(RENAMED.get(district, "")))
        nice_state = NICE_STATE.get(state, state)
        if match:
            lat, lon, pop, note = match["lat"], match["lon"], match["population"], "census2011"
        else:
            lat, lon = geocode(district, nice_state)
            pop, note = "", "created after 2011 (no Census 2011 population)"
        out.append({"district": district.replace("  ", " "), "state": nice_state, "lat": lat, "lon": lon,
                    "population_2011": pop, **{c: values.get(c, "") for c in INDICATORS}, "note": note})

    with open(HERE / "districts.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out[0].keys())
        writer.writeheader()
        writer.writerows(out)
    print(f"wrote {len(out)} districts, {sum(1 for r in out if r['population_2011'])} with Census 2011 population")


if __name__ == "__main__":
    main()
