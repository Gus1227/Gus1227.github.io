# Kabuzio bot: tidy the brand column (M) of Ofertas. Same brand written many ways (PAGANI, Pagani Design)
# becomes one name, and words that are not brands (2026, New, Men...) are replaced by the brand found in the title.
# M is also the hashtag in the posts. MARCAS=si writes; anything else only prints what would change.
import collections, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
from telegram import TAB, google_token, sheets

WRITE = os.environ.get("MARCAS", "no").lower() in ("si", "sí", "1")
# known brands: how they are written in titles -> the one name we use
KNOWN = [(r"pagani\s*design|pagani", "PaganiDesign"), (r"tsar\s*bomba|tsar", "TsarBomba"), (r"san\s*martin", "SanMartin"),
         (r"addies\s*dive|addiesdive", "Addiesdive"), (r"watchdives", "Watchdives"), (r"steeldive", "Steeldive"),
         (r"heimdallr", "Heimdallr"), (r"phylida", "Phylida"), (r"cronos", "Cronos"), (r"merkur", "Merkur"),
         (r"baltany", "Baltany"), (r"proxima", "Proxima"), (r"sugess", "Sugess"), (r"berny", "Berny"),
         (r"seagull", "Seagull"), (r"daniel\s*gorman", "DanielGorman"), (r"cadisen", "Cadisen"), (r"didun", "Didun"),
         (r"benyar", "Benyar"), (r"poedagar", "Poedagar"), (r"rolls\s*timi", "RollsTimi"), (r"specht", "Specht"),
         (r"curren", "Curren"), (r"naviforce", "Naviforce"), (r"lige", "Lige"), (r"olevs", "Olevs"), (r"skmei", "Skmei"),
         (r"forsining", "Forsining"), (r"winner", "Winner"), (r"megir", "Megir"), (r"reef\s*tiger", "ReefTiger"),
         (r"ochstin", "Ochstin"), (r"bulova", "Bulova"), (r"guanqin", "Guanqin"), (r"tevise", "Tevise"),
         (r"hruodland", "Hruodland"), (r"escapement\s*time", "EscapementTime"), (r"thorn", "Thorn"),
         (r"ripple", "Ripple"), (r"red\s*star", "RedStar"), (r"seakoss", "Seakoss"), (r"ailang", "Ailang"),
         (r"ix\s*&\s*dao|ixdao", "IXDAO"), (r"jacques\s*genry", "JacquesGenry"), (r"farasute", "Farasute"), (r"hanboro", "Hanboro")]
NOT_BRAND = re.compile(r"^(\d+|new|men|mens|man|women|top|luxury|hot|original|automatic|mechanical|quartz|watch|watches|"
                       r"fashion|sport|sports|business|classic|brand|official|the|titanium|shanghai|skeleton|sin\s*marca|)$", re.I)


def brand_of(text):
    t = text.lower()
    for pat, name in KNOWN:
        if re.search(r"\b(" + pat + r")\b", t):
            return name
    return ""


def main():
    tok = google_token()
    rows = sheets(tok, f"values/{TAB}!A1:M5000").get("values", [])
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    before = collections.Counter(g(r, 12) for r in rows[1:] if g(r, 0))
    print("Antes:", before.most_common())
    cells, unknown = [], collections.Counter()
    for n, r in enumerate(rows[1:], start=2):
        if not g(r, 0):
            continue
        m = g(r, 12)
        new = brand_of(m) or (brand_of(g(r, 0)) if NOT_BRAND.match(m) or not m else "")
        if not new:
            if m and NOT_BRAND.match(m):  # a word that is not a brand: leave it without brand (Cheche, 2026-10-04)
                cells.append((n, m, ""))
            elif not m:
                unknown[g(r, 0)[:60]] += 1
            continue
        if new != m:
            cells.append((n, m, new))
    cells = [c for c in cells if c[1] != c[2]]
    for n, m, new in cells:
        print(f"  fila {n}: «{m}» -> {new}")
    print(f"Cambios: {len(cells)}. Sin marca clara: {sum(unknown.values())}")
    for t in unknown:
        print("  ?", t)
    if WRITE and cells:
        sheets(tok, "values:batchUpdate", {"valueInputOption": "RAW", "data": [
            {"range": f"{TAB}!M{n}", "values": [[new]]} for n, _, new in cells]}, method="POST")
        print("Escrito.")


if __name__ == "__main__":
    main()
