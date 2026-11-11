#!/usr/bin/env python
"""Build meta/ko.js: English/Showdown ids -> Korean names / PK indices (our own mapping, no API data).
Run: python -I -X utf8 scripts/build_ko_maps.py   (stdlib only; reuses scripts/build_meta.py helpers)
Optional: pass rankings JSON files (saved from /api/rankings) to report unmapped species; nothing from them is stored.
"""
import json, os, re, sys
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
    out = {"mon": mon, "move": mv, "item": it, "ability": ab, "nature": bm.NATURES}
    p = os.path.join(bm.ROOT, "meta", "ko.js")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("window.KO=%s;" % json.dumps(out, ensure_ascii=False, separators=(",", ":")))
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
