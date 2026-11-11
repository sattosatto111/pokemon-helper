#!/usr/bin/env python
"""Build meta/teams.js from pokedb Champions open data (ranked top teams).
Source: https://champs.pokedb.tokyo/guide/opendata  (files are meant to be downloaded programmatically,
not fetched from end-user browsers -> we ship a committed snapshot).
Run: python -I -X utf8 scripts/build_teams.py   (stdlib only)
"""
import csv, io, json, os, re, sys, tempfile, time, unicodedata, urllib.request
from collections import Counter
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir(), "pokemon-teams-cache")
UA = {"User-Agent": "Mozilla/5.0 (compatible; pokemon-meta-builder)"}
BASE = "https://champs.pokedb.tokyo/opendata/s%d_%s_ranked_teams.json"
PAPI = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"
TOP_TEAMS, TOP_CORES, TOP_USAGE = 100, 30, 40
MAX_SEASONS = 50  # upper bound for the season probe

# (national dex, form index) -> PokeAPI pokemon identifier (non-default forms)
FORMS = {
    (38, 1): "ninetales-alola", (53, 1): "persian-alola", (59, 1): "arcanine-hisui", (80, 2): "slowbro-galar",
    (128, 1): "tauros-paldea-combat-breed", (128, 2): "tauros-paldea-blaze-breed", (128, 3): "tauros-paldea-aqua-breed",
    (157, 1): "typhlosion-hisui", (199, 1): "slowking-galar", (479, 1): "rotom-heat", (479, 2): "rotom-wash",
    (479, 4): "rotom-fan", (479, 5): "rotom-mow", (503, 1): "samurott-hisui", (571, 1): "zoroark-hisui",
    (666, 18): "vivillon-fancy", (670, 5): "floette-eternal", (706, 1): "goodra-hisui", (711, 1): "gourgeist-small",
    (711, 2): "gourgeist-large", (724, 1): "decidueye-hisui", (745, 2): "lycanroc-dusk", (849, 1): "toxtricity-low-key",
    (876, 1): "indeedee-female", (902, 1): "basculegion-female", (925, 0): "maushold-family-of-three", (925, 1): "maushold-family-of-four",
}

def get(url, cache=True):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9.-]", "_", url.split("//")[1]))
    if cache and os.path.exists(p):
        return open(p, "rb").read()
    data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
    open(p, "wb").write(data)
    return data

def fetch_json(url, cache=True):
    """Parsed season dict, or None with a logged reason (HTTP/network error, soft-404 HTML, wrong shape)."""
    try:
        raw = get(url, cache)
    except Exception as e:  # HTTPError (non-2xx), URLError, timeout
        print(f"WARN fetch failed: {url}: {e}")
        return None
    try:
        d = json.loads(raw)
    except ValueError:
        print(f"WARN non-JSON response (soft-404 HTML?): {url}: {raw[:60]!r}")
        return None
    if isinstance(d, dict) and "teams" in d:
        return d
    print(f"WARN unexpected JSON shape (no 'teams'): {url}")
    return None

def csv_rows(name):
    return list(csv.DictReader(io.StringIO(get(PAPI + name).decode("utf-8"))))

def nk(s): return unicodedata.normalize("NFKC", s).replace(" ", "").replace("　", "")

def main():
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    spr = json.loads(re.search(r"^const SPR=(\[.*?\]);?\s*$", src, re.M).group(1))
    id2idx = {}
    for i, pid in enumerate(spr): id2idx.setdefault(pid, i)
    ident2id, default_of = {}, {}
    for r in csv_rows("pokemon.csv"):
        ident2id[r["identifier"]] = int(r["id"])
        if r["is_default"] == "1": default_of[int(r["species_id"])] = int(r["id"])
    ja = {}
    inames = {r["id"]: r["identifier"] for r in csv_rows("items.csv")}
    ko = {}
    for r in csv_rows("item_names.csv"):
        if r["local_language_id"] == "3": ko[r["item_id"]] = r["name"]
        if r["local_language_id"] in ("1", "11"): ja.setdefault(nk(r["name"]), r["item_id"])
    item_ko = lambda j: ko.get(ja.get(nk(j)))

    seasons, items, miss_mon, miss_item = [], [], Counter(), Counter()
    def item_idx(j):
        if not j or j == "持ち物なし": return -1
        k = item_ko(j)
        if k is None: miss_item[j] += 1; k = j
        if k not in items: items.append(k)
        return items.index(k)
    def mon_idx(m):
        dex, ff = (int(x) for x in m["id"].split("-"))
        pid = ident2id.get(FORMS[(dex, ff)]) if (dex, ff) in FORMS else default_of.get(dex)
        if (ff and (dex, ff) not in FORMS) or pid not in id2idx:
            miss_mon[(m["id"], m["pokemon"], m["form"])] += 1  # form not in app: fall back to base
            pid = default_of.get(dex)
        return id2idx.get(pid)
    n = 0
    while n < MAX_SEASONS and fetch_json(BASE % (n + 1, "single"), cache=False):  # discover latest published season
        n += 1; time.sleep(1)
    if n == 0: sys.exit("no published season found (see WARN lines above)")
    if n == MAX_SEASONS: print(f"WARN season probe hit cap {MAX_SEASONS}")
    for s in range(n, 0, -1):
        for rule in ("single", "double"):
            d = fetch_json(BASE % (s, rule))
            if d is None:
                print(f"WARN skipping season {s} {rule}"); continue
            teams = []
            for t in d["teams"]:
                ms = [m for m in t["team"] if m.get("id")]
                idx = [mon_idx(m) for m in ms]
                if any(i is None for i in idx):
                    for m, i in zip(ms, idx):
                        if i is None: miss_mon[(m["id"], m["pokemon"], m["form"])] += 1
                    continue
                if len(set(idx)) < 2: continue
                teams.append((t["rank"], (round(t["rating_value"]) if t.get("rating_value") is not None else None), [(i, item_idx(m["item"])) for i, m in zip(idx, ms)]))
            c2, c3, us = Counter(), Counter(), Counter()
            for _, _, ms in teams:
                ids = sorted({i for i, _ in ms})
                us.update(ids); c2.update(combinations(ids, 2)); c3.update(combinations(ids, 3))
            seasons.append({"season": d["season"], "rule": rule, "updated": d["updated_at"][:10], "n": len(teams),
                "teams": [{"rank": r, "rating": g, "mons": [list(x) for x in ms]} for r, g, ms in teams[:TOP_TEAMS]],
                "cores2": [[list(k), v] for k, v in c2.most_common(TOP_CORES)],
                "cores3": [[list(k), v] for k, v in c3.most_common(TOP_CORES)],
                "usage": [[k, v] for k, v in us.most_common(TOP_USAGE)]})
            time.sleep(1)
    out = {"source": {"name": "ポケDB チャンピオンズ (pokedb.tokyo)", "url": "https://champs.pokedb.tokyo/guide/opendata",
                      "note": "pokedb 오픈 데이터 (https://champs.pokedb.tokyo/guide/opendata) · 출처 표기"},
           "items": items, "seasons": seasons}
    p = os.path.join(ROOT, "meta", "teams.js")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("window.TEAMS=%s;" % json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print("seasons", n, "bytes", os.path.getsize(p))
    print("unmapped mon entries:", sum(miss_mon.values()), dict(miss_mon))
    print("unmapped items:", sum(miss_item.values()), dict(miss_item))

if __name__ == "__main__":
    main()
