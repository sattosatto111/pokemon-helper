#!/usr/bin/env python
"""Build meta/bss.js and meta/vgc.js from Smogon Champions usage stats (chaos JSON).
Run: python -I -X utf8 scripts/build_meta.py   (stdlib only)

Percent conventions (all relative to a Pokemon's own total = sum of its Abilities weights):
- moves/items/abilities/spreads: weight / total * 100
- mates (Teammates): the chaos Teammates value is the (weighted) count of games both were on a
  team together, so weight / total * 100 = "how often this Pokemon's team also has that mate".
"""
import csv, io, json, os, re, sys, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir(), "pokemon-meta-cache")
UA = {"User-Agent": "Mozilla/5.0 (compatible; pokemon-meta-builder)"}
SMOGON = "https://www.smogon.com/stats/"
PAPI = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"
FORMATS = [("bss", "gen9championsbssregmc", "싱글 (챔피언스 BSS)"),
           ("vgc", "gen9championsvgc2026regmc", "더블 (챔피언스 VGC)")]
NATURES = dict(zip("Lonely Adamant Naughty Brave Bold Impish Lax Relaxed Modest Mild Rash Quiet Calm Gentle Careful Sassy Timid Hasty Jolly Naive Hardy Docile Bashful Quirky Serious".split(),
                   "외로움 고집 개구쟁이 용감 대담 장난꾸러기 촐랑 무사태평 조심 의젓 덜렁 냉정 차분 얌전 신중 건방 겁쟁이 성급 명랑 천진난만 노력 온순 수줍음 변덕 성실".split()))
# manual overrides: Smogon species -> PokeAPI identifier
OVERRIDES = {
    "Ogerpon-Wellspring": "ogerpon-wellspring-mask", "Ogerpon-Hearthflame": "ogerpon-hearthflame-mask",
    "Ogerpon-Cornerstone": "ogerpon-cornerstone-mask", "Tauros-Paldea-Aqua": "tauros-paldea-aqua-breed",
    "Tauros-Paldea-Blaze": "tauros-paldea-blaze-breed", "Tauros-Paldea-Combat": "tauros-paldea-combat-breed",
    "Indeedee-F": "indeedee-female", "Indeedee": "indeedee-male", "Basculegion-F": "basculegion-female",
    "Basculegion": "basculegion-male", "Meowstic-F": "meowstic-female", "Meowstic": "meowstic-male",
    "Oinkologne-F": "oinkologne-female", "Oinkologne": "oinkologne-male",
    "Meowstic-F-Mega": "meowstic-female-mega", "Meowstic-Mega": "meowstic-male-mega",
    "Aegislash": "aegislash-shield", "Lycanroc": "lycanroc-midday", "Maushold": "maushold-family-of-four",
    "Mimikyu": "mimikyu-disguised", "Toxtricity": "toxtricity-amped",
}

def get(url):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, re.sub(r"[^A-Za-z0-9.-]", "_", url.split("//")[1]))
    if os.path.exists(p) and "smogon" not in url:
        return open(p, "rb").read()
    req = urllib.request.Request(url, headers=UA)
    data = urllib.request.urlopen(req, timeout=120).read()
    open(p, "wb").write(data)
    return data

def exists(url):
    try:
        urllib.request.urlopen(urllib.request.Request(url, headers=UA, method="HEAD"), timeout=60)
        return True
    except Exception:
        return False

def csv_rows(name):
    return list(csv.DictReader(io.StringIO(get(PAPI + name).decode("utf-8"))))

def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())

def names(idfile, namefile, key):
    ident = {r["id"]: norm(r["identifier"]) for r in csv_rows(idfile)}
    ko = {r[key]: r["name"] for r in csv_rows(namefile) if r["local_language_id"] == "3"}
    return {ident[i]: ko[i] for i in ident if i in ko}

def pick_month():
    html = get(SMOGON).decode("utf-8", "replace")
    months = sorted(set(re.findall(r'href="(\d{4}-\d{2})/"', html)), reverse=True)
    for m in months:
        if all(any(exists(f"{SMOGON}{m}/chaos/{f}-{c}.json") for c in (1630, 1500, 0)) for _, f, _ in FORMATS):
            return m
    sys.exit("no month with both formats")

def load_app():
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    spr = json.loads(re.search(r"^const SPR=(\[.*?\]);?\s*$", src, re.M).group(1))
    pk = re.search(r"^const PK=(\[.*\]);?\s*$", src, re.M).group(1)
    ko = re.findall(r'\[\s*"([^"]+)"\s*,\s*\d', pk)
    id2idx = {}
    for i, pid in enumerate(spr):
        id2idx.setdefault(pid, i)
    return id2idx

def main():
    id2idx = load_app()
    ident2id = {}
    for r in csv_rows("pokemon.csv"):
        ident2id[r["identifier"]] = int(r["id"])
    mv, it, ab = (names("moves.csv", "move_names.csv", "move_id"),
                  names("items.csv", "item_names.csv", "item_id"),
                  names("abilities.csv", "ability_names.csv", "ability_id"))
    month = pick_month()
    miss = {"species": set(), "moves": set(), "items": set(), "abilities": set()}

    def sp_idx(name):
        cands = [OVERRIDES[name]] if name in OVERRIDES else []
        base = re.sub(r"[.':]", "", name.lower().replace(" ", "-"))
        cands += [base, base.replace("-mega-x", "-mega-x")]
        for c in cands:
            if c in ident2id and ident2id[c] in id2idx:
                return id2idx[ident2id[c]]
        return None

    for key, fmt, label in FORMATS:
        for cut in (1630, 1500, 0):
            url = f"{SMOGON}{month}/chaos/{fmt}-{cut}.json"
            if exists(url): break
        d = json.loads(get(url))
        fmtname = f"{fmt}-{cut}"
        data = d["data"]
        idxmap = {s: sp_idx(s) for s in data}
        mons = []
        ranked = sorted(data.items(), key=lambda kv: -kv[1].get("usage", 0))
        for s, v in ranked:
            if v.get("usage", 0) < 0.005: continue
            if idxmap[s] is None:
                miss["species"].add(s); continue
            tot = sum(v.get("Abilities", {}).values()) or 1
            def top(dct, n, tr, mk):
                out = []
                for k, w in sorted(dct.items(), key=lambda kv: -kv[1]):
                    if k in ("nothing", ""): continue
                    t = tr(k)
                    if t is None: miss[mk].add(k); continue
                    out.append([t, round(w / tot * 100, 1)])
                    if len(out) == n: break
                return out
            def spread(k):
                nat, evs = k.split(":", 1)
                return f"{NATURES.get(nat, nat)} {evs}"
            mates = []
            for m, w in sorted(v.get("Teammates", {}).items(), key=lambda kv: -kv[1]):
                mi = idxmap.get(m) if m in idxmap else sp_idx(m)
                if mi is None or mi == idxmap[s]: continue
                mates.append([mi, round(w / tot * 100, 1)])
                if len(mates) == 10: break
            mons.append({"i": idxmap[s], "u": round(v["usage"] * 100, 1), "rank": len(mons) + 1,
                         "moves": top(v.get("Moves", {}), 8, lambda k: mv.get(k), "moves"),
                         "items": top(v.get("Items", {}), 5, lambda k: it.get(k), "items"),
                         "abilities": top(v.get("Abilities", {}), 3, lambda k: ab.get(k), "abilities"),
                         "spreads": top(v.get("Spreads", {}), 3, spread, "items"),
                         "mates": mates})
            if len(mons) == 200: break
        out = {"fmt": fmtname, "label": label, "month": month, "battles": d["info"]["number of battles"], "mons": mons}
        os.makedirs(os.path.join(ROOT, "meta"), exist_ok=True)
        p = os.path.join(ROOT, "meta", f"{key}.js")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("window.META=window.META||{};window.META.%s=%s;" % (key, json.dumps(out, ensure_ascii=False, separators=(",", ":"))))
        print(f"{key}: {month} {fmtname} battles={out['battles']} mons={len(mons)} bytes={os.path.getsize(p)}")
    for k, v in miss.items():
        print(f"unmatched {k}: {len(v)} {sorted(v)[:15]}")

if __name__ == "__main__":
    main()
