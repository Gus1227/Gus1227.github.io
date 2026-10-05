# Kabuzio: «quiet luxury» copy for every network, built from what the AliExpress title really says.
# Only features found in the title are named (sapphire, 316L, automatic, NH35...): nothing is invented.
# Used by telegram.py, zernio.py and feed.yml (Pinterest). Also writes Ofertas AN (headline) and AO (specs)
# so Make (Instagram, Facebook) can use the same text: TEXTOS=si writes; anything else only prints.
import os, re, sys

# (regex on the lower-case title, feature) in the order they are shown
SPECS = (
    (r"sapphire|saphire|zafiro", "Sapphire crystal"),
    (r"316\s?l", "316L stainless steel"),
    (r"titanium", "Titanium case"),
    (r"ceramic", "Ceramic bezel"),
    (r"bronze", "Bronze case"),
    (r"tourbillon", "Tourbillon"),
    (r"automatic|self.?wind|mechanical|nh3[45]|nh38|pt5000|sw200|miyota\s?82|seagull", "Automatic movement"),
    (r"meteorite", "Meteorite dial"),
    (r"carbon fib", "Carbon fiber"),
    (r"bgw.?9|c3 |super.?lum|luminous", "Luminous dial"),
)
MOVEMENTS = ((r"nh35", "NH35"), (r"nh34", "NH34 GMT"), (r"nh38", "NH38"), (r"pt5000", "PT5000"), (r"sw200", "SW200"),
             (r"vh31", "VH31 sweep"), (r"vk6[34]", "VK meca-quartz"), (r"miyota\s?82\d\d", "Miyota 8215"),
             (r"seagull", "Seagull"))
KINDS = ((r"tourbillon", "Tourbillon"), (r"gmt", "GMT"), (r"chronograph|vk6[34]", "Chronograph"),
         (r"\bdiv(e|er|ers|ing)\b|200m|300m|20bar|30bar", "Diver"), (r"pilot|aviat|flieger", "Pilot"), (r"skeleton", "Skeleton"),
         (r"moon.?phase", "Moonphase"), (r"field", "Field"), (r"tonneau", "Tonneau"), (r"dress", "Dress"))


def water(t):
    m = re.search(r"(\d{2,4})\s?m\b(?!m)", t) or re.search(r"(\d{1,3})\s?bar", t)
    if not m:
        return ""
    meters = int(m.group(1)) * (10 if "bar" in m.group(0) else 1)
    return f"{meters}m water resistant" if 50 <= meters <= 2000 else ""


def specs(title, limit=4):
    t = " " + (title or "").lower() + " "
    out = [name for rx, name in SPECS if re.search(rx, t)]
    mv = next((name for rx, name in MOVEMENTS if re.search(rx, t)), "")
    if mv and "Automatic movement" in out and mv not in ("VH31 sweep", "VK meca-quartz"):
        out[out.index("Automatic movement")] = f"Automatic {mv}"
    elif mv:
        out.append(f"{mv} movement")
    w = water(t)
    if w:
        out.insert(min(3, len(out)), w)
    return out[:limit]


def kind(title):
    t = (title or "").lower()
    return next((k for rx, k in KINDS if re.search(rx, t)), "")


def nice_brand(b):
    b = (b or "").strip().lstrip("#")
    return "" if b.lower() in ("", "sin marca", "watches") else re.sub(r"([a-z])([A-Z])", r"\1 \2", b)


def headline(title, brand):
    """«Pagani Design Automatic Diver» / «Automatic Pilot Watch» — what the watch is, no hype."""
    t = (title or "").lower()
    auto = "Automatic" if re.search(r"automatic|mechanical|self.?wind|nh3[45]|pt5000", t) else ""
    k = kind(title)
    parts = [nice_brand(brand), auto if k not in ("Tourbillon",) else "", k or "Watch"]
    out = " ".join(p for p in parts if p)
    return out if out != "Watch" else "Kabuzio Pick"


def tag(s):
    return "#" + re.sub(r"[^A-Za-z0-9]", "", s).lower() if s else ""


def main():
    sys.path.insert(0, os.path.dirname(__file__))
    from telegram import TAB, google_token, sheets
    write = os.environ.get("TEXTOS", "no").lower() in ("si", "sí", "1")
    tok = google_token()
    rows = sheets(tok, f"values/{TAB}!A1:AO5000").get("values", [])
    head = rows[0] + [""] * (41 - len(rows[0]))
    if head[39] not in ("", "Titular") or head[40] not in ("", "Specs"):
        raise SystemExit(f"AN/AO ya se usan: {head[39]!r} {head[40]!r}")
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    data = [{"range": f"{TAB}!AN1:AO1", "values": [["Titular", "Specs"]]}] if head[39:41] != ["Titular", "Specs"] else []
    for n, r in enumerate(rows[1:], start=2):
        if not g(r, 0):
            continue
        h, s = headline(g(r, 0), g(r, 12)), " · ".join(specs(g(r, 0)))
        if n < 8:
            print(f"{n}: {g(r, 0)[:90]}\n    -> {h} | {s}")
        if [g(r, 39), g(r, 40)] != [h, s]:
            data.append({"range": f"{TAB}!AN{n}:AO{n}", "values": [[h, s]]})
    print(len(data), "filas por escribir")
    if write and data:
        sheets(tok, "values:batchUpdate", {"valueInputOption": "RAW", "data": data}, method="POST")
        print("Escrito.")


if __name__ == "__main__":
    main()
