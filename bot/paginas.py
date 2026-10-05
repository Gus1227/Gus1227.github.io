# Kabuzio: one page per watch (w/<id>.html) + sitemap.xml + robots.txt, so Google can show each watch
# to people searching for it. Reads the same public «Catalogo» CSV as the website. Run by feed.yml.
import csv, glob, hashlib, html, io, json, os, re, urllib.request

CSV = ("https://docs.google.com/spreadsheets/d/e/2PACX-1vQRH7X54O1GzNSUWnIgBT1545CXdQMaZ7HOzKOyJC6mZKyXG9gxJ9T5DBbAv0WzbkZXOdHrW8ubzUwS/"
       "pub?gid=596242979&single=true&output=csv")
SITE = "https://gus1227.github.io/"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
e = lambda s: html.escape(str(s or "").strip())
nice = lambda b: re.sub(r"([a-z])([A-Z])", r"\1 \2", b)


def sold(v):
    """«2,451» or «2451.00» -> 2451"""
    m = re.search(r"\d[\d,]*(\.\d+)?", str(v or ""))
    return int(float(m.group().replace(",", ""))) if m else 0


def kind(name):
    n = name.lower()
    for words, k in ((("chronograph",), "Chronograph"), (("dive", "diver"), "Sport"), (("tourbillon",), "Tourbillon"),
                     (("skeleton",), "Skeleton"), (("automatic", "mechanical"), "Automatic"), (("quartz",), "Quartz")):
        if any(w in n for w in words):
            return k
    return ""


def watches():
    rows = list(csv.DictReader(io.StringIO(urllib.request.urlopen(CSV, timeout=60).read().decode("utf-8"))))
    out = []
    for r in rows:
        name = (r.get("Nombre_web") or "").strip() or (r.get("Producto") or "").strip()
        link = (r.get("Link_WEB") or "").strip()
        enlace = (r.get("Enlace") or "").strip()
        if not link.startswith("https://"):
            link = enlace
        if not (name and link.startswith("https://") and enlace) or (r.get("Oculto_web") or "").strip().lower().startswith("s"):
            continue
        # readable address for Google: words of the name + a short code of the link (links can be 1000+ characters)
        slug = re.sub(r"[^a-z0-9]+", "-", (r.get("Producto") or name).lower()).strip("-")[:60].rstrip("-")
        wid = f"{slug}-{hashlib.sha1(enlace.encode()).hexdigest()[:6]}"
        pics = []
        for u in [r.get("Imagen_URL") or ""] + (r.get("Fotos_extra") or "").split():
            if u.startswith("https://") and u not in pics:
                pics.append(u)
        brand = (r.get("Marca") or "").strip()
        out.append({"id": wid, "name": name, "price": (r.get("Precio") or "").strip(), "link": link, "pics": pics[:8],
                    "brand": "" if brand in ("", "Sin marca") else nice(brand), "kind": (r.get("Estilo_web") or "").strip() or kind(name),
                    "sales": sold(r.get("Ventas")), "video": (r.get("Video") or "").strip()})
    return [w for w in out if w["id"] and w["pics"]]


CSS = """:root{--ink:#111;--muted:#737373;--line:#ececec;--soft:#f5f5f4}*{box-sizing:border-box;margin:0}
body{font-family:Inter,system-ui,-apple-system,sans-serif;color:var(--ink);background:#fff;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}.nav{border-bottom:1px solid var(--line)}.nav div{max-width:1100px;margin:0 auto;padding:14px 16px;display:flex;justify-content:space-between;align-items:center}
.logo{font-weight:700;letter-spacing:.18em;font-size:15px}.back{font-size:13px;color:var(--muted)}
main{max-width:1100px;margin:0 auto;padding:24px 16px 60px;display:grid;gap:32px}@media(min-width:860px){main{grid-template-columns:1.1fr 1fr}}
.big{width:100%;aspect-ratio:1;object-fit:cover;border-radius:14px;background:var(--soft)}.th{display:flex;gap:8px;margin-top:10px;overflow-x:auto}
.th img{width:64px;height:64px;object-fit:cover;border-radius:8px;cursor:pointer;background:var(--soft);flex:none}
.br{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}h1{font-size:clamp(22px,3vw,30px);line-height:1.2;margin-top:8px;font-weight:600;letter-spacing:-.01em}
.pr{font-size:28px;font-weight:700;margin-top:16px}.meta{color:var(--muted);font-size:14px;margin-top:6px}
.cta{display:block;text-align:center;background:var(--ink);color:#fff;border-radius:999px;padding:16px;font-weight:600;margin-top:22px}
.trust{list-style:none;padding:0;margin-top:18px;display:grid;gap:8px;font-size:14px}.trust li{background:var(--soft);border-radius:10px;padding:10px 14px}
p.d{margin-top:20px;line-height:1.6;color:#333;font-size:15px}.rel{max-width:1100px;margin:0 auto;padding:0 16px 60px}.rel h2{font-size:18px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}@media(min-width:700px){.grid{grid-template-columns:repeat(4,1fr)}}
.grid img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:10px;background:var(--soft)}.grid b{display:block;font-size:13px;font-weight:500;margin-top:6px;line-height:1.35}.grid span{font-size:13px;color:var(--muted)}
footer{text-align:center;color:var(--muted);font-size:12px;padding:24px 16px;border-top:1px solid var(--line)}"""


def page(w, related):
    title = f"{w['name'][:70]} – {w['price']}"
    what = " ".join(x for x in (w["brand"], w["kind"], "watch") if x)
    sold = f", {w['sales']}+ sold" if w["sales"] else ""
    desc = (f"{what[0].upper() + what[1:]} for {w['price']} on AliExpress"
            f"{sold}. "
            "Hand-picked by Kabuzio. Buyer Protection and worldwide shipping.")
    price_num = re.sub(r"[^0-9.]", "", w["price"])
    ld = {"@context": "https://schema.org", "@type": "Product", "name": w["name"], "image": [p + "_800x800.jpg" for p in w["pics"]],
          "description": desc, "sku": w["id"],
          "offers": {"@type": "Offer", "url": f"{SITE}w/{w['id']}.html", "priceCurrency": "USD", "price": price_num,
                     "availability": "https://schema.org/InStock"}}
    if w["brand"]:
        ld["brand"] = {"@type": "Brand", "name": w["brand"]}
    if not price_num:
        ld.pop("offers")
    ldjs = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    pics = "".join(f'<img src="{e(p)}_200x200.jpg" alt="{e(w["name"])} photo {i + 1}" loading="lazy" '
                   f'onclick="document.getElementById(\'big\').src=\'{e(p)}_800x800.jpg\'">' for i, p in enumerate(w["pics"]))
    rel = "".join(f'<a href="{r["id"]}.html"><img src="{e(r["pics"][0])}_350x350.jpg" alt="{e(r["name"])}" loading="lazy">'
                  f'<b>{e(r["name"][:60])}</b><span>{e(r["price"])}</span></a>' for r in related)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | Kabuzio</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE}w/{w['id']}.html">
<meta property="og:type" content="product"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{e(w['pics'][0])}_800x800.jpg"><meta property="og:url" content="{SITE}w/{w['id']}.html">
<meta property="og:site_name" content="Kabuzio">{f'<meta property="og:price:amount" content="{price_num}"><meta property="og:price:currency" content="USD"><meta property="product:availability" content="instock">' if price_num else ''}
<meta name="referrer" content="no-referrer">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⌚</text></svg>">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script type="application/ld+json">{ldjs}</script>
<style>{CSS}</style></head><body>
<nav class="nav"><div><a class="logo" href="../">KABUZIO</a><a class="back" href="../">← All watches</a></div></nav>
<main><div><img id="big" class="big" src="{e(w['pics'][0])}_800x800.jpg" alt="{e(w['name'])}"><div class="th">{pics}</div></div>
<div><div class="br">{e(w['brand'] or 'Kabuzio Pick')}{' · ' + e(w['kind']) if w['kind'] else ''}</div><h1>{e(w['name'])}</h1>
<div class="pr">{e(w['price'])}</div>{f'<div class="meta">🔥 {w["sales"]}+ sold on AliExpress</div>' if w['sales'] else ''}
<a class="cta" href="{e(w['link'])}" rel="nofollow sponsored">View deal on AliExpress</a>
<ul class="trust"><li>🛡️ AliExpress Buyer Protection</li><li>🌍 Worldwide shipping</li><li>✅ Hand-picked best sellers</li></ul>
<p class="d">{e(desc)} More watches every day on our <a href="https://linktr.ee/Kabuzio_Deal"><u>Telegram and social pages</u></a>.</p>
<p class="d" style="font-size:12px;color:#999">Affiliate link: we may earn a commission at no extra cost to you.</p></div></main>
{f'<section class="rel"><h2>You may also like</h2><div class="grid">{rel}</div></section>' if rel else ''}
<footer>© Kabuzio · <a href="../">Watch deals</a></footer></body></html>"""


def main():
    ws = watches()
    os.makedirs(os.path.join(ROOT, "w"), exist_ok=True)
    keep = set()
    for w in ws:
        same = [r for r in ws if r["id"] != w["id"] and r["brand"] == w["brand"]]
        other = sorted((r for r in ws if r["id"] != w["id"] and r not in same), key=lambda r: -r["sales"])
        related = (sorted(same, key=lambda r: -r["sales"]) + other)[:8]
        f = os.path.join(ROOT, "w", f"{w['id']}.html")
        keep.add(f)
        txt = page(w, related)
        if not os.path.exists(f) or open(f, encoding="utf-8").read() != txt:
            open(f, "w", encoding="utf-8").write(txt)
    for f in glob.glob(os.path.join(ROOT, "w", "*.html")):
        if f not in keep:
            os.remove(f)  # watch left the catalog
    urls = [SITE] + [f"{SITE}w/{w['id']}.html" for w in ws]
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    open(os.path.join(ROOT, "robots.txt"), "w").write(
        f"User-agent: *\nDisallow: /panel.html\nDisallow: /editor.html\nDisallow: /bot/\nSitemap: {SITE}sitemap.xml\n")
    print(len(ws), "páginas")


if __name__ == "__main__":
    main()
