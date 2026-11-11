#!/usr/bin/env python3
"""Build per-generation data files (gens/common.js, gens/gen1..8.js) for the app.

Run:  python -I -X utf8 scripts/build_gens.py
Stdlib only. Downloads are cached in %TEMP%/pkgd (delete to refresh).

Sources: Pokemon Showdown data (MIT) + PokeAPI CSVs (Korean move names, ids).

Rules
-----
* Entries of PK are identified by SPR (PokeAPI pokemon id) -> PokeAPI identifier ->
  Showdown species id (hyphen strip; special-cased suffixes; fallback to the base
  species / trailing-token stripping, so cosmetic forms resolve to their base).
* Generation resolution: Showdown mods gen8..gen1 each inherit the next one up, so the
  value in gen N is taken from the first mod among N..8 that overrides the field, else
  the base (gen 9) data. Types/stats/abilities/move type-power-category only.
  Output holds only values that differ from the Gen 9 *Showdown* value of the same
  entry (so that app-side PK/MV conventions are left untouched).
* Gen 1: Special = spa (== spd in the gen1 mod); C and D both emitted as that value.
* Abilities: Showdown slots 0,1,H(,S ignored) in this order, deduped. Gen 3-4: no hidden
  slot. Abilities whose Showdown `gen` > N are dropped (kept if that would empty the list).
  Gen 1-2: no abilities.
* Availability avail=[min,max]:
    min: national-dex ranges (1:1-151, 2:-251, 3:-386, 4:-493, 5:-649, 6:-721, 7:-809,
         8:-905, 9:-1025); forms bump it: Mega/Primal 6, Alola/Ultra Burst 7, Galar/Hisui 8,
         Paldea 9, plus a small table of later-introduced forms (see FORME_MIN).
    max: 9 if the species is not isNonstandard Past/Future in Showdown's base formats-data
         (gen 9); else 8 if not Past/Future in mods/gen8 formats-data (or if minGen==8,
         since Legends Arceus counts as gen 8); else 7.
    Megas: always [6,7] (engine handles Champions). Mega entries that did not exist in
    gens 6-7 (Legends Z-A new megas) are still [6,7] per contract (they inherit base data).
    Non-contiguous availability (e.g. absent from SwSh but back in SV) is reported as the
    range [min,max] (so gen 8 includes them).
* Learnsets: gens 3-8 from main learnsets.ts, gens 1-2 from mods/gen2/learnsets.ts (which
  carries 1x/2x codes). A move is learnable in gen N if any source code starts with N
  (letters M,T,L,E,S,D,R... but NOT "V" = Virtual-Console/Home transfer), unioned over the
  species prevo chain. Forms without own learnset, Mega/Primal/Ultra forms, and forms whose
  learnset only has restricted ("R") entries (Rotom appliances) also union the base species
  chain. Showdown has no Legends-Arceus (8) codes for Hisui forms & LA-only species:
  when a gen-8-available species has an empty gen 8 list it falls back to its gen 9 codes.
* mvExtra: moves learnable in gens 1-8 by an available species that are not in MV, with
  Showdown Gen 9 values (type, basePower, category), Korean name from PokeAPI.
"""
import csv, io, json, os, re, sys, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(tempfile.gettempdir(), 'pkgd')
os.makedirs(CACHE, exist_ok=True)
SD = 'https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/'
PA = 'https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/'


def fetch(url, name):
    p = os.path.join(CACHE, name)
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        try:
            with urllib.request.urlopen(url) as r, open(p, 'wb') as f:
                f.write(r.read())
        except Exception as e:
            if 'mods' in url:
                open(p, 'wb').close()
                return ''
            raise
    return open(p, encoding='utf8').read()


# ---------------------------------------------------------------- TS parser
TOK = re.compile(r'''\s+|//[^\n]*|/\*.*?\*/|(?P<str>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(?P<tpl>`)|(?P<num>-?\d+(?:\.\d+)?)|(?P<id>[A-Za-z_$][\w$]*)|(?P<p>.)''', re.S)


class P:
    def __init__(self, s):
        self.s = s
        self.t = []
        for m in TOK.finditer(s):
            k = m.lastgroup
            if k is None:
                continue
            if k == 'tpl':
                # template literal: consume to closing backtick
                self.t.append(('tplstart', m.end()))
                continue
            self.t.append((k, m.group(k)))
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ('eof', '')

    def nxt(self):
        x = self.peek()
        self.i += 1
        return x

    def skip_balanced(self):
        """consume one bracketed group, current token is an opener"""
        depth = 0
        while True:
            k, v = self.nxt()
            if k == 'eof':
                return
            if k == 'p':
                if v in '([{':
                    depth += 1
                elif v in ')]}':
                    depth -= 1
                    if depth == 0:
                        return

    def skip_expr(self):
        while True:
            k, v = self.peek()
            if k == 'eof':
                return
            if k == 'p' and v in ',}]':
                return
            if k == 'p' and v in '([{':
                self.skip_balanced()
            else:
                self.i += 1

    def value(self):
        k, v = self.peek()
        if k == 'p' and v == '{':
            r = self.obj()
        elif k == 'p' and v == '[':
            r = self.arr()
        elif k == 'str':
            self.i += 1
            r = unq(v)
        elif k == 'num':
            self.i += 1
            r = float(v) if '.' in v else int(v)
        elif k == 'id' and v in ('true', 'false', 'null'):
            self.i += 1
            r = {'true': True, 'false': False, 'null': None}[v]
        else:
            self.skip_expr()
            return None
        # trailing `as X` / other junk until , } ]
        k, v = self.peek()
        if not (k == 'p' and v in ',}]') and k != 'eof':
            self.skip_expr()
        return r

    def arr(self):
        self.nxt()
        out = []
        while True:
            k, v = self.peek()
            if k == 'p' and v == ']':
                self.nxt()
                return out
            if k == 'p' and v == ',':
                self.nxt()
                continue
            if k == 'eof':
                return out
            out.append(self.value())

    def obj(self):
        self.nxt()
        out = {}
        while True:
            k, v = self.peek()
            if k == 'p' and v == '}':
                self.nxt()
                return out
            if k == 'p' and v == ',':
                self.nxt()
                continue
            if k == 'eof':
                return out
            if k == 'p' and v == '[':  # computed key
                self.skip_balanced()
                key = None
            elif k in ('id', 'str', 'num'):
                self.nxt()
                key = unq(v) if k == 'str' else str(v)
            else:  # spread or junk
                self.skip_expr()
                continue
            k2, v2 = self.peek()
            if k2 == 'p' and v2 == ':':
                self.nxt()
                val = self.value()
                if key is not None:
                    out[key] = val
            elif k2 == 'p' and v2 in '(':  # method shorthand
                self.skip_balanced()
                if self.peek() == ('p', ':'):  # return type annotation
                    self.skip_expr()
                if self.peek() == ('p', '{'):
                    self.skip_balanced()
            else:  # shorthand property or async/get junk
                continue


def unq(v):
    q = v[0]
    body = v[1:-1]
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t'}.get(m.group(1), m.group(1)), body)


def strip_templates(s):
    # remove template literals (rare in these files) so the tokenizer stays in sync
    return re.sub(r'`(?:\\.|[^`\\])*`', '""', s, flags=re.S)


def load_ts(name, url):
    s = fetch(url, name)
    if not s:
        return {}
    s = strip_templates(s)
    i = s.index('= {') + 2
    p = P(s[i:])
    return p.value()


# ---------------------------------------------------------------- helpers
def sid(x):
    return re.sub(r'[^a-z0-9]', '', x.lower())


TYPES = ['Normal', 'Fighting', 'Flying', 'Poison', 'Ground', 'Rock', 'Bug', 'Ghost', 'Steel', 'Fire', 'Water', 'Grass', 'Electric', 'Psychic', 'Ice', 'Dragon', 'Dark', 'Fairy']
TI = {t: i for i, t in enumerate(TYPES)}
CAT = {'Physical': 0, 'Special': 1, 'Status': 2}
GEN_MAX = [151, 251, 386, 493, 649, 721, 809, 905, 1025]


def arr_from_html(html, name):
    i = html.index('const %s=' % name) + len('const %s=' % name)
    c = html[i]
    close = {'[': ']', '{': '}'}[c]
    depth = 0
    ins = False
    j = i
    while True:
        ch = html[j]
        if ins:
            if ch == '\\':
                j += 1
            elif ch == '"':
                ins = False
        else:
            if ch == '"':
                ins = True
            elif ch == c:
                depth += 1
            elif ch == close:
                depth -= 1
                if depth == 0:
                    break
        j += 1
    return json.loads(html[i:j + 1])


# forms introduced after their base species' generation
FORME_MIN = {
    'pikachu': {'cosplay': 6, 'rockstar': 6, 'belle': 6, 'popstar': 6, 'phd': 6, 'libre': 6, 'starter': 7},
    'eevee': {'starter': 7},
    'greninja': {'ash': 7},
    'zygarde': {'10': 6, '10pc': 6, 'complete': 7},
    'hoopa': {'unbound': 6},
    'meowstic': {'f': 6},
    'aegislash': {'blade': 6},
    'floette': {'eternal': 6},
    'necrozma': {'duskmane': 7, 'dawnwings': 7, 'ultra': 7},
    'toxtricity': {'lowkey': 8},
    'urshifu': {'rapidstrike': 8},
    'calyrex': {'ice': 8, 'shadow': 8},
    'zacian': {'crowned': 8}, 'zamazenta': {'crowned': 8},
    'eternatus': {'eternamax': 8},
    'sinistea': {}, 'polteageist': {},
}
REGION_MIN = {'alola': 7, 'alolan': 7, 'galar': 8, 'galarian': 8, 'hisui': 8, 'hisuian': 8, 'paldea': 9, 'paldean': 9, 'mega': 6, 'megax': 6, 'megay': 6, 'megaz': 6, 'primal': 6, 'gmax': 8}
BASE_FIX = {  # PokeAPI identifier -> Showdown id where the generic rules fail
    'tauros-paldea-combat-breed': 'taurospaldeacombat', 'tauros-paldea-blaze-breed': 'taurospaldeablaze',
    'tauros-paldea-aqua-breed': 'taurospaldeaaqua', 'necrozma-dusk': 'necrozmaduskmane', 'necrozma-dawn': 'necrozmadawnwings',
    'meowstic-female': 'meowsticf', 'indeedee-female': 'indeedeef', 'basculegion-female': 'basculegionf',
    'oinkologne-female': 'oinkolognef', 'ogerpon-wellspring-mask': 'ogerponwellspring', 'ogerpon-hearthflame-mask': 'ogerponhearthflame',
    'ogerpon-cornerstone-mask': 'ogerponcornerstone', 'zygarde-10': 'zygarde10', 'zygarde-50': 'zygarde',
    'mimikyu-disguised': 'mimikyu', 'mimikyu-busted': 'mimikyu', 'urshifu-single-strike': 'urshifu',
    'urshifu-rapid-strike': 'urshifurapidstrike', 'darmanitan-standard': 'darmanitan', 'darmanitan-zen': 'darmanitanzen',
    'darmanitan-galar-standard': 'darmanitangalar', 'darmanitan-galar-zen': 'darmanitangalarzen',
    'maushold-family-of-three': 'maushold', 'maushold-family-of-four': 'mausholdfour',
    'palafin-zero': 'palafin', 'palafin-hero': 'palafinhero', 'tatsugiri-curly': 'tatsugiri',
    'dudunsparce-two-segment': 'dudunsparce', 'dudunsparce-three-segment': 'dudunsparcethreesegment',
    'gimmighoul-chest': 'gimmighoul', 'gimmighoul-roaming': 'gimmighoulroaming',
    'terapagos-terastal': 'terapagosterastal', 'terapagos-stellar': 'terapagosstellar',
    'basculin-white-striped': 'basculinwhitestriped', 'basculin-blue-striped': 'basculinbluestriped',
    'toxtricity-low-key': 'toxtricitylowkey', 'lycanroc-midnight': 'lycanrocmidnight', 'lycanroc-dusk': 'lycanrocdusk',
    'oricorio-pom-pom': 'oricoriopompom', 'oricorio-pau': 'oricoriopau', 'oricorio-sensu': 'oricoriosensu',
    'minior-red-meteor': 'minior', 'wishiwashi-solo': 'wishiwashi', 'wishiwashi-school': 'wishiwashischool',
    'eiscue-ice': 'eiscue', 'eiscue-noice': 'eiscuenoice', 'morpeko-full-belly': 'morpeko', 'morpeko-hangry': 'morpekohangry',
    'squawkabilly-green-plumage': 'squawkabilly', 'squawkabilly-blue-plumage': 'squawkabillyblue',
    'squawkabilly-yellow-plumage': 'squawkabillyyellow', 'squawkabilly-white-plumage': 'squawkabillywhite',
    'meloetta-aria': 'meloetta', 'meloetta-pirouette': 'meloettapirouette', 'keldeo-ordinary': 'keldeo',
    'keldeo-resolute': 'keldeoresolute', 'aegislash-shield': 'aegislash', 'aegislash-blade': 'aegislashblade',
    'pumpkaboo-average': 'pumpkaboo', 'gourgeist-average': 'gourgeist', 'indeedee-male': 'indeedee', 'meowstic-male': 'meowstic',
    'basculegion-male': 'basculegion', 'oinkologne-male': 'oinkologne', 'giratina-altered': 'giratina',
    'giratina-origin': 'giratinaorigin', 'shaymin-land': 'shaymin', 'shaymin-sky': 'shayminsky', 'deoxys-normal': 'deoxys',
    'wormadam-plant': 'wormadam', 'tornadus-incarnate': 'tornadus', 'thundurus-incarnate': 'thundurus',
    'landorus-incarnate': 'landorus', 'enamorus-incarnate': 'enamorus', 'castform-normal': 'castform',
    'hoopa-confined': 'hoopa', 'lycanroc-midday': 'lycanroc', 'cramorant-gulping': 'cramorantgulping',
    'cramorant-gorging': 'cramorantgorging', 'meowstic-male-mega': 'meowsticmmega', 'meowstic-female-mega': 'meowsticfmega', 'eternatus-eternamax': 'eternatuseternamax', 'zacian-hero': 'zacian',
    'zamazenta-hero': 'zamazenta', 'calyrex-ice': 'calyrexice', 'calyrex-shadow': 'calyrexshadow',
}


def main():
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()
    PK = arr_from_html(html, 'PK')
    SPR = arr_from_html(html, 'SPR')
    AB = arr_from_html(html, 'AB')
    MV = arr_from_html(html, 'MV')
    assert len(PK) == len(SPR), (len(PK), len(SPR))
    print('PK', len(PK), 'MV', len(MV), 'AB', len(AB))

    dex = load_ts('pokedex.ts', SD + 'pokedex.ts')
    moves = load_ts('moves.ts', SD + 'moves.ts')
    learn = load_ts('learnsets.ts', SD + 'learnsets.ts')
    fd = load_ts('formats-data.ts', SD + 'formats-data.ts')
    abil = load_ts('abilities.ts', SD + 'abilities.ts')
    mods = {}
    for g in range(1, 9):
        mods[g] = {
            'dex': load_ts('g%d-pokedex.ts' % g, SD + 'mods/gen%d/pokedex.ts' % g),
            'mv': load_ts('g%d-moves.ts' % g, SD + 'mods/gen%d/moves.ts' % g),
            'fd': load_ts('g%d-formats-data.ts' % g, SD + 'mods/gen%d/formats-data.ts' % g),
        }
    l12 = load_ts('g2-learnsets.ts', SD + 'mods/gen2/learnsets.ts')
    for k, v in list(dex.items()):  # cosmetic forms without own data: inherit from base species
        if 'num' not in v and v.get('baseSpecies') and sid(v['baseSpecies']) in dex:
            nv = dict(dex[sid(v['baseSpecies'])])
            nv.update(v)
            dex[k] = nv
    print('parsed: dex', len(dex), 'moves', len(moves), 'learn', len(learn), 'l12', len(l12), 'fd', len(fd), 'abil', len(abil))

    # ---- PokeAPI
    pk_csv = list(csv.DictReader(io.StringIO(fetch(PA + 'pokemon.csv', 'pokemon.csv'))))
    pa_ident = {int(r['id']): r['identifier'] for r in pk_csv}
    pa_species = {int(r['id']): int(r['species_id']) for r in pk_csv}
    mv_csv = list(csv.DictReader(io.StringIO(fetch(PA + 'moves.csv', 'moves.csv'))))
    mv_ident = {int(r['id']): r['identifier'] for r in mv_csv}
    ko_by_ident = {}
    for r in csv.DictReader(io.StringIO(fetch(PA + 'move_names.csv', 'move_names.csv'))):
        if r['local_language_id'] == '3':
            ko_by_ident[sid(mv_ident[int(r['move_id'])])] = r['name']
    if 'vicegrip' in ko_by_ident:  # PokeAPI spelling differs from Showdown
        ko_by_ident['visegrip'] = ko_by_ident.pop('vicegrip')
    ab_csv = list(csv.DictReader(io.StringIO(fetch(PA + 'abilities.csv', 'abilities.csv'))))
    ab_sid2id = {sid(r['identifier']): int(r['id']) for r in ab_csv}
    ab_name2id = {}
    for k, v in abil.items():
        if sid(v.get('name', k)) in ab_sid2id:
            ab_name2id[k] = ab_sid2id[sid(v.get('name', k))]
        elif k in ab_sid2id:
            ab_name2id[k] = ab_sid2id[k]
    ab_gen = {k: v.get('gen', 1) for k, v in abil.items()}

    # ---- species mapping
    by_num = {}
    for k, v in dex.items():
        if v.get('num', 0) > 0 and not v.get('forme'):
            by_num.setdefault(v['num'], k)
    ent = []   # per PK idx: showdown species id
    unresolved = []
    for i, pid in enumerate(SPR):
        ident = pa_ident.get(pid)
        sp = None
        if ident:
            cands = [BASE_FIX.get(ident), sid(ident)]
            parts = ident.split('-')
            for n in range(len(parts) - 1, 0, -1):
                cands.append(sid(''.join(parts[:n])))
            for c in cands:
                if c and c in dex:
                    sp = c
                    if c != sid(ident) and c != BASE_FIX.get(ident):
                        unresolved.append((i, PK[i][0], ident, c))
                    break
        if sp is None:
            sp = by_num.get(pa_species.get(pid, 0))
            unresolved.append((i, PK[i][0], ident, sp))
        ent.append(sp)
    print('form fallbacks (idx, ko, pokeapi, ->showdown):', len(unresolved))
    for u in unresolved:
        print('  ', u)

    def dget(sp):
        return dex[sp]

    def base_of(sp):
        d = dex[sp]
        return sid(d['baseSpecies']) if d.get('baseSpecies') else sp

    def fd_of(table, sp):
        if sp in table:
            return table[sp]
        b = base_of(sp)
        return table.get(b, {})

    # ---- availability
    def min_gen(sp):
        d = dex[sp]
        num = d['num']
        g = next((n + 1 for n, m in enumerate(GEN_MAX) if num <= m), 9)
        forme = sid(d.get('forme', ''))
        if forme:
            first = d.get('forme', '').lower().split('-')[0]
            for key in (forme, first):
                if key in REGION_MIN:
                    g = max(g, REGION_MIN[key])
                    break
            fm = FORME_MIN.get(base_of(sp), {})
            if forme in fm:
                g = max(g, fm[forme])
        return g

    def is_mega(sp):
        toks = dex[sp].get('forme', '').lower().split('-')
        return 'mega' in toks or toks[0] == 'primal'

    avail = []
    for i, sp in enumerate(ent):
        if 'mega' in dex[sp].get('forme', '').lower().split('-'):
            avail.append([6, 7])
            continue
        mn = min_gen(sp)
        bad = ('Past', 'Future')
        f9 = fd_of(fd, sp).get('isNonstandard')
        f8t = mods[8]['fd']
        f8 = fd_of(f8t, sp) if (sp in f8t or base_of(sp) in f8t) else fd_of(fd, sp)
        if f9 not in bad:
            mx = 9
        elif mn >= 8 or f8.get('isNonstandard') not in bad:
            mx = 8
        else:
            mx = 7
        if mn > mx:
            mx = mn
        avail.append([mn, mx])

    # ---- moves: MV index <-> showdown id
    ko2sd = {}
    for k, ko in ko_by_ident.items():
        ko2sd.setdefault(ko, k)
        ko2sd.setdefault(ko.replace(' ', ''), k)
    mv_sd = []
    mv_unmapped = []
    sd2mv = {}
    for j, m in enumerate(MV):
        k = ko2sd.get(m[0]) or ko2sd.get(m[0].replace(' ', ''))
        if k is None or k not in moves:
            mv_unmapped.append((j, m[0], k))
            mv_sd.append(None)
            continue
        mv_sd.append(k)
        sd2mv.setdefault(k, j)
    print('MV unmapped to showdown:', len(mv_unmapped), mv_unmapped[:40])

    extra = []   # [ko,type,power,cat,0]
    extra_idx = {}

    def move_index(k, create=True):
        if k in sd2mv:
            return sd2mv[k]
        if k in extra_idx:
            return extra_idx[k]
        if not create:
            return None
        m = moves.get(k)
        if m is None:
            return None
        ko = ko_by_ident.get(k)
        if ko is None:
            return None
        extra.append([ko, TI.get(m.get('type'), 0), int(m.get('basePower') or 0), CAT.get(m.get('category'), 2), 0])
        extra_idx[k] = len(MV) + len(extra) - 1
        return extra_idx[k]

    def mval(g, k, field):
        for gg in range(g, 9):
            e = mods[gg]['mv'].get(k)
            if e and field in e:
                return e[field]
        return moves[k].get(field)

    def mtuple(g, k):
        return [TI.get(mval(g, k, 'type'), 0), int(mval(g, k, 'basePower') or 0), CAT.get(mval(g, k, 'category'), 2)]

    # ---- pokemon values per gen
    def pval(g, sp, field):
        for gg in range(g, 9):
            e = mods[gg]['dex'].get(sp)
            if e and field in e:
                return e[field]
        return dex[sp].get(field)

    def ptypes(g, sp):
        t = [TI[x] for x in pval(g, sp, 'types')]
        return [t[0], t[1] if len(t) > 1 else -1]

    def pstats(g, sp):
        b = pval(g, sp, 'baseStats')
        if g == 1:
            return [b['hp'], b['atk'], b['def'], b['spa'], b['spa'], b['spe']]
        return [b['hp'], b['atk'], b['def'], b['spa'], b['spd'], b['spe']]

    def pabil(g, sp):
        a = pval(g, sp, 'abilities') or {}
        out = []
        for slot in ('0', '1', 'H'):
            if slot == 'H' and g <= 4:
                continue
            n = a.get(slot)
            if not n:
                continue
            k = sid(n)
            if ab_gen.get(k, 1) > g:
                continue
            ai = ab_name2id.get(k)
            if ai is not None and ai not in out:
                out.append(ai)
        if not out and a.get('0'):
            ai = ab_name2id.get(sid(a['0']))
            if ai:
                out.append(ai)
        return out

    # sanity: gen9 abilities / stats / types vs PK
    mm = {'t': 0, 's': 0, 'a': 0}
    for i, sp in enumerate(ent):
        if ptypes(9, sp) != [PK[i][1], PK[i][2]]:
            mm['t'] += 1
        if pstats(9, sp) != PK[i][3:9]:
            mm['s'] += 1
            print('  stat diff', i, PK[i][0], sp, pstats(9, sp), PK[i][3:9])
        if sorted(pabil(9, sp)) != sorted(PK[i][9]):
            mm['a'] += 1
            print('  abil diff', i, PK[i][0], sp, pabil(9, sp), PK[i][9])
    print('PK vs showdown gen9 mismatches (types/stats/abilities):', mm)

    # ---- learnsets
    def codes_for(sp, g):
        """set of move ids learnable in gen g by species id sp (own entry only)"""
        src = l12 if g <= 2 else learn
        e = src.get(sp)
        if not e or not e.get('learnset'):
            return None
        out = set()
        for mk, cs in e['learnset'].items():
            for c in (cs or []):
                if not isinstance(c, str):
                    continue
                m = re.match(r'(\d+)([A-Za-z])', c)
                if m and int(m.group(1)) == g and m.group(2) != 'V':
                    out.add(mk)
        return out

    def only_restricted(sp):
        e = learn.get(sp, {}).get('learnset') or {}
        for cs in e.values():
            for c in cs:
                if isinstance(c, str) and not re.match(r'\d+R', c):
                    return False
        return True

    def chain(sp):
        """species + prevo chain, with base species chain unioned when appropriate"""
        seen = []
        stack = [sp]
        while stack:
            s = stack.pop()
            if s in seen or s not in dex:
                continue
            seen.append(s)
            d = dex[s]
            if d.get('prevo'):
                stack.append(sid(d['prevo']))
            own = learn.get(s, {}).get('learnset') if s in learn else None
            b = base_of(s)
            if b != s and (not own or is_mega(s) or only_restricted(s) or sid(d.get('forme', '')) in ('ultra', 'primal')):
                stack.append(b)
        return seen

    def learn_set(sp, g, fallback=True):
        out = set()
        for s in chain(sp):
            c = codes_for(s, g)
            if c:
                out |= c
        return out

    def species_gen_ok(sp, g):
        return True

    res = {g: {'types': {}, 'stats': {}, 'moves': {}, 'learn': {}, 'abil': {}} for g in range(1, 9)}
    missing_moves = {}
    for g in range(1, 9):
        R = res[g]
        used = set()
        for i, sp in enumerate(ent):
            mn, mx = avail[i]
            if not (mn <= g <= mx):
                continue
            t = ptypes(g, sp)
            if t != ptypes(9, sp):
                R['types'][i] = t
            s = pstats(g, sp)
            if s != pstats(9, sp):
                R['stats'][i] = s
            if g >= 3:
                a = pabil(g, sp)
                if a != pabil(9, sp) and a:
                    R['abil'][i] = a
            ls = learn_set(sp, g)
            if not ls and g == 8:
                ls = learn_set(sp, 9)
            idxs = set()
            for mk in ls:
                if mk not in moves:
                    continue
                if (moves[mk].get('isNonstandard') in ('CAP', 'Custom')):
                    continue
                j = move_index(mk)
                if j is None:
                    missing_moves[mk] = missing_moves.get(mk, 0) + 1
                    continue
                idxs.add(j)
                used.add(mk)
            R['learn'][i] = sorted(idxs)
        # move overrides: for all MV-mapped moves + extras
        cand = list(sd2mv.items()) + list(extra_idx.items())
        for k, j in cand:
            t9 = mtuple(9, k)
            tg = mtuple(g, k)
            if tg != t9:
                R['moves'][j] = tg
    # extras might have been created during later gens -> recompute moves overrides for all gens
    for g in range(1, 9):
        R = res[g]
        for k, j in list(sd2mv.items()) + list(extra_idx.items()):
            if mtuple(g, k) != mtuple(9, k):
                R['moves'][j] = mtuple(g, k)
        R['moves'] = dict(sorted(R['moves'].items()))
    print('learnset moves with no index/ko name:', missing_moves)

    # ---- write
    outdir = os.path.join(ROOT, 'gens')
    os.makedirs(outdir, exist_ok=True)

    def js(o):
        return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

    with open(os.path.join(outdir, 'common.js'), 'w', encoding='utf8', newline='\n') as f:
        f.write('window.GD={avail:%s,mvExtra:%s};\n' % (js(avail), js(extra)))
    for g in range(1, 9):
        R = res[g]
        parts = []
        for key in ('types', 'stats', 'moves', 'learn', 'abil'):
            if key == 'abil' and g <= 2:
                continue
            parts.append('%s:%s' % (key, js({str(k): v for k, v in R[key].items()})))
        with open(os.path.join(outdir, 'gen%d.js' % g), 'w', encoding='utf8', newline='\n') as f:
            f.write('GD[%d]={%s};\n' % (g, ','.join(parts)))
        print('gen%d: avail %d | types %d stats %d moves %d abil %d | learn entries %d' % (
            g, len(R['learn']), len(R['types']), len(R['stats']), len(R['moves']), len(R['abil']), len(R['learn'])))
    print('mvExtra:', len(extra))
    for fn in sorted(os.listdir(outdir)):
        print(fn, os.path.getsize(os.path.join(outdir, fn)))

    # ---- spot checks
    def find(ko):
        return [i for i, p in enumerate(PK) if p[0] == ko]
    print('--- spot checks')
    for ko in ('후딘', '피카츄', '버터플', '픽시', '코일', '마기라스', '리자몽'):
        for i in find(ko):
            print(ko, i, 'avail', avail[i], 'g1 types', res[1]['types'].get(i), 'g1 stats', res[1]['stats'].get(i) or PK[i][3:9],
                  'g5 types', res[5]['types'].get(i), 'g6 types', res[6]['types'].get(i))
    for i, p in enumerate(PK):
        if p[0] == '리자몽 (메가 X)':
            print('mega charizard X', i, p[0], avail[i])
    for nm in ('화염방사', '따라가때리기'):
        j = next((j for j, m in enumerate(MV) if m[0] == nm), None)
        if j is None:
            j = extra_idx.get(sid(nm)) or next((len(MV) + k for k, m in enumerate(extra) if m[0] == nm), None)
        print(nm, 'idx', j, [(g, res[g]['moves'].get(j)) for g in (1, 5, 6)], MV[j] if j is not None and j < len(MV) else (extra[j - len(MV)] if j else None))
        if nm == '따라가때리기':
            for i in find('마기라스'):
                print('  마기라스', i, [(g, j in res[g]['learn'].get(i, [])) for g in range(2, 9)])


if __name__ == '__main__':
    main()
