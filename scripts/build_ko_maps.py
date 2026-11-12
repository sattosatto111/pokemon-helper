#!/usr/bin/env python
"""Build meta/ko.js: English/Showdown ids -> Korean names / PK indices (our own mapping, no API data).
Run: python -I -X utf8 scripts/build_ko_maps.py   (stdlib only; reuses scripts/build_meta.py helpers)
Optional: pass rankings JSON files (saved from /api/rankings) to report unmapped species; nothing from them is stored.
"""
import json, os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_meta as bm

# Showdown/API species name -> PokeAPI identifier, on top of build_meta.OVERRIDES
EXTRA = {"Maushold-Four": "maushold-family-of-four", "Squawkabilly-Yellow": "squawkabilly-yellow-plumage",
         "Squawkabilly-Blue": "squawkabilly-blue-plumage", "Squawkabilly-White": "squawkabilly-white-plumage",
         "Squawkabilly-Green": "squawkabilly-green-plumage", "Gourgeist-Small": "gourgeist-small",
         "Gourgeist-Large": "gourgeist-large", "Gourgeist-Super": "gourgeist-super", "Gourgeist": "gourgeist-average",
         "Pumpkaboo": "pumpkaboo-average", "Floette-Eternal": "floette-eternal", "Vivillon-Fancy": "vivillon-fancy",
         "Lycanroc-Dusk": "lycanroc-dusk", "Lycanroc-Midnight": "lycanroc-midnight",
         "Toxtricity-Low-Key": "toxtricity-low-key", "Aegislash-Blade": "aegislash-blade",
         "Mimikyu-Busted": "mimikyu-busted", "Morpeko": "morpeko-full-belly"}

# Korean item names are kept only for holdable battle items: PokeAPI categories below + anything flagged holdable
HELD_CATS = {"medicine", "picky-healing", "effort-drop", "type-protection", "in-a-pinch", "other", "held-items", "effort-training",
             "training", "choice", "type-enhancement", "bad-held-items", "plates", "jewels", "mega-stones", "memories",
             "species-specific", "scarves"}

def held_items():
    cat = {r["id"]: r["identifier"] for r in bm.csv_rows("item_categories.csv")}
    flag = {r["id"]: r["identifier"] for r in bm.csv_rows("item_flags.csv")}
    hold = {r["item_id"] for r in bm.csv_rows("item_flag_map.csv") if flag[r["item_flag_id"]].startswith("holdable")}
    return {bm.norm(r["identifier"]) for r in bm.csv_rows("items.csv") if cat[r["category_id"]] in HELD_CATS or r["id"] in hold}

RANK = "https://championsbattledata.com/api/rankings?format=%s&limit=400%s"

def roster_ids():
    """Union of showdownIds across Singles/Doubles x current + seasons M1..M7 (only the id set is kept)."""
    ids = set()
    for fmt in ("Singles", "Doubles"):
        for se in ("", "&season=M1", "&season=M2", "&season=M3", "&season=M4", "&season=M5", "&season=M6", "&season=M7"):
            req = urllib.request.Request(RANK % (fmt, se), headers=bm.UA)
            d = json.loads(urllib.request.urlopen(req, timeout=120).read().decode("utf-8"))
            ids |= {r["showdownId"] for r in d.get("rankings", [])}
    return ids

def build_roster(mon):
    src = open(os.path.join(bm.ROOT, "index.html"), encoding="utf-8").read()
    pk = json.loads(re.search(r"^const PK=(\[.*\]);?\s*$", src, re.M).group(1))
    base = lambda i: pk[i][0].split(" (")[0]
    ids = roster_ids()
    ros = {mon[bm.norm(s)] for s in ids if bm.norm(s) in mon}
    print("roster ids", len(ids), "unmapped", sorted(s for s in ids if bm.norm(s) not in mon))
    names = {base(i) for i in ros}
    ros |= {i for i, p in enumerate(pk) if p[0].startswith(base(i) + " (메가") and base(i) in names}
    return sorted(ros)

def main():
    id2idx = bm.load_app()
    ident = {r["identifier"]: int(r["id"]) for r in bm.csv_rows("pokemon.csv")}
    mon = {}
    for k, v in ident.items():          # every PokeAPI form identifier, normalised (showdown ids match this for most)
        if v in id2idx:
            mon.setdefault(bm.norm(k), id2idx[v])
    for name, pid in {**bm.OVERRIDES, **EXTRA}.items():
        if pid in ident and ident[pid] in id2idx:
            mon[bm.norm(name)] = id2idx[ident[pid]]
    # species whose variant has no sprite/PK entry in the app: use the base form
    for k, base in {"meowsticf": "meowsticmale", "toxtricitylowkey": "toxtricityamped", "vivillonfancy": "vivillon",
                    "squawkabilly": "squawkabillygreenplumage", "squawkabillyyellow": "squawkabillygreenplumage",
                    "palafin": "palafinzero", "pyroar": "pyroarmale"}.items():
        if base in mon: mon.setdefault(k, mon[base])
    mon = {k: v for k, v in sorted(mon.items())}
    mv = bm.names("moves.csv", "move_names.csv", "move_id")
    it = bm.names("items.csv", "item_names.csv", "item_id")
    ab = bm.names("abilities.csv", "ability_names.csv", "ability_id")
    ab.update({"eelevate": "천정부지", "firemane": "불꽃의갈기", "auraguard": "파동의방호"})   # new in Champions (gamewith.ai ko)
    held = held_items()
    it = {k: v for k, v in it.items() if k in held}
    roster = build_roster(mon)
    out = {"mon": mon, "roster": roster, "move": mv, "item": it, "ability": ab, "nature": bm.NATURES}
    p = os.path.join(bm.ROOT, "meta", "ko.js")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("window.KO=%s;window.dispatchEvent(new Event('koloaded'));" % json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print({k: len(v) for k, v in out.items()}, os.path.getsize(p), "bytes")
    # coverage check against saved API responses (not stored)
    miss = {"mon": set(), "move": set(), "item": set(), "ability": set()}
    for fp in sys.argv[1:]:
        d = json.load(open(fp, encoding="utf-8"))
        for r in d.get("rankings", []):
            if bm.norm(r["showdownId"]) not in mon: miss["mon"].add(r["name"])
        for r in d.get("rows", []):
            c, n = r["category"], bm.norm(r["name"])
            if c == "move" and n not in mv: miss["move"].add(r["name"])
            elif c == "held_item" and n not in it: miss["item"].add(r["name"])
            elif c == "ability" and n not in ab: miss["ability"].add(r["name"])
            elif c == "teammate" and n not in mon: miss["mon"].add(r["name"])
    for k, v in miss.items(): print("unmapped", k, len(v), sorted(v)[:40])

if __name__ == "__main__":
    main()
