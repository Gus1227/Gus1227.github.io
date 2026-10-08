# Kabuzio: «quiet luxury» copy for every network, built from what the AliExpress title really says.
# Only features found in the title are named (sapphire, 316L, automatic, NH35...): nothing is invented.
# Used by telegram.py, zernio.py and feed.yml (Pinterest). Also writes Ofertas «Titular» and «Specs» columns
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
        out[out.index("Automatic movement")] = f"{mv} automatic movement"
    elif mv:
        out.append(f"{mv} movement")
    if "316L stainless steel" not in out and "Titanium case" not in out and "stainless" in t:
        out.insert(1 if out[:1] == ["Sapphire crystal"] else 0, "Stainless steel case")
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
    if k == "Diver":  # Cheche (2026-10-05): we never sell them as diving watches
        k = ""
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
    rows = sheets(tok, f"values/{TAB}!A1:CZ5000").get("values", [])
    head = [h.strip() for h in rows[0]]
    # own columns, found by their header; the first time they go after the last used header
    col = lambda i: (chr(64 + i // 26) if i >= 26 else "") + chr(65 + i % 26)
    if "Titular" in head and "Specs" in head:
        ch, cs = head.index("Titular"), head.index("Specs")
    else:
        ch = len(head)
        cs = ch + 1
    print("columnas:", col(ch), col(cs))
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    data = [] if "Titular" in head else [{"range": f"{TAB}!{col(ch)}1:{col(cs)}1", "values": [["Titular", "Specs"]]}]
    for n, r in enumerate(rows[1:], start=2):
        if not g(r, 0):
            continue
        h, s = headline(g(r, 0), g(r, 12)), " · ".join(specs(g(r, 0)))
        if n < 12:
            print(f"{n}: {g(r, 0)[:90]}\n    -> {h} | {s}")
        if g(r, ch) != h:
            data.append({"range": f"{TAB}!{col(ch)}{n}", "values": [[h]]})
        if g(r, cs) != s:
            data.append({"range": f"{TAB}!{col(cs)}{n}", "values": [[s]]})
    print(len(data), "filas por escribir")
    if write and data:
        props = next(x["properties"] for x in sheets(tok, "?fields=sheets.properties")["sheets"] if x["properties"]["title"] == TAB)
        if props["gridProperties"]["columnCount"] < cs + 1:  # the sheet ends before our columns: add them
            sheets(tok, ":batchUpdate", {"requests": [{"appendDimension": {"sheetId": props["sheetId"], "dimension": "COLUMNS",
                   "length": cs + 1 - props["gridProperties"]["columnCount"]}}]}, method="POST")
        sheets(tok, "values:batchUpdate", {"valueInputOption": "RAW", "data": data}, method="POST")
        print("Escrito.")


if __name__ == "__main__":
    main()


def tiktok_seo(title, brand):
    """TikTok search words (Cheche, 2026-10-07): one line people actually type + hashtags, for every TikTok post.
    Only words that are true for this watch; no "cheap"."""
    t = (title or "").lower()
    k = kind(title)
    k = "" if k == "Diver" else k
    auto = bool(re.search(r"automatic|mechanical|self.?wind|nh3[45]|pt5000", t))
    b = nice_brand(brand)
    words = [f"{'automatic ' if auto else ''}{k.lower() + ' ' if k else ''}watch for men".strip(),
             f"{b} watch" if b else "", "men's watches", "watch gift for him", "watch collection"]
    tags = ["#ad", "#watches", "#menswatch", "#watchesformen", "#watchtok", "#watchcollector",
            tag(b) if b else "", f"#{k.lower()}watch" if k else "", "#automaticwatch" if auto else "", "#kabuzio"]
    return " · ".join(w for w in words if w), " ".join(dict.fromkeys(x for x in tags if x))


def dm_code(pid):
    """Short code for «DM us K1234»: K + last 4 digits of the product id (bot/tiktok_dm.py finds the watch by it)."""
    d = re.sub(r"\D", "", pid or "")
    return f"K{d[-4:]}" if len(d) >= 4 else ""


def dm_line(pid):
    """TikTok call to action (Cheche, 2026-10-07): comment on the post, Gus answers right there with the link."""
    return COMMENT


# Cheche (2026-10-08): right under the price in every post, short
COMMENT = "💬 Comment «LINK» to get the link"
BEST = "🏆 Best prices · 🎟 Coupons · 🔒 100% Buyer Protection"
