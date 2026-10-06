# Kabuzio web: buying guides (g/) and «A vs B» comparisons (vs/) in every language, for people searching Google
# for the best watch of a kind or brand. Built from the same catalog as the watch pages (bot/paginas.py calls make()).
import datetime, html, json, re

from idiomas import LANGS, T, prefix, w as tr
from textos import specs

SITE = "https://gus1227.github.io/"
e = lambda s: html.escape(str(s or "").strip())
YEAR = datetime.date.today().year

G = {
    "en": {"kind": "Best {k} Watches on AliExpress ({y})", "brand": "Best {b} Watches on AliExpress ({y})", "top": "Best-Selling Watches on AliExpress ({y})",
           "intro": "The {n} most chosen pieces right now, hand-picked by Kabuzio from AliExpress best sellers. We look at real sales, buyer ratings and what the watch is made of, and we refresh this list every day.",
           "how": "How we pick", "howt": "Only watches with many real orders and good ratings. No famous-brand copies. Prices are checked against AliExpress every day.",
           "faq": [("Is it safe to buy watches on AliExpress?", "Every order is covered by AliExpress Buyer Protection: if the watch does not arrive or is not as described, you get your money back."),
                   ("Do they ship to my country?", "Yes, these watches ship worldwide. Delivery time depends on your country and the seller."),
                   ("Why these watches?", "They are the pieces buyers choose most, with solid materials like sapphire crystal, stainless steel and automatic movements.")],
           "sold": "sold", "vs": "{a} vs {b}: which one to choose ({y})", "vsintro": "Two of the most chosen watches on AliExpress, side by side.",
           "more_sold": "{x} is the crowd favourite, with {n}+ orders.", "lower": "{x} has the lower price.", "same": "Both are top sellers: pick the style you like most.",
           "price": "Price", "orders": "Orders", "brand_l": "Brand", "feats": "Features", "all_g": "All guides"},
    "es": {"kind": "Los mejores relojes {k} en AliExpress ({y})", "brand": "Los mejores relojes {b} en AliExpress ({y})", "top": "Los relojes más vendidos de AliExpress ({y})",
           "intro": "Las {n} piezas más elegidas ahora mismo, seleccionadas por Kabuzio entre los más vendidos de AliExpress. Miramos ventas reales, valoraciones y materiales, y actualizamos la lista cada día.",
           "how": "Cómo elegimos", "howt": "Solo relojes con muchos pedidos reales y buenas valoraciones. Nada de copias de marcas famosas. Los precios se revisan cada día en AliExpress.",
           "faq": [("¿Es seguro comprar relojes en AliExpress?", "Cada pedido tiene la Protección al comprador de AliExpress: si el reloj no llega o no es como se describe, te devuelven el dinero."),
                   ("¿Envían a mi país?", "Sí, estos relojes se envían a todo el mundo. El plazo depende de tu país y del vendedor."),
                   ("¿Por qué estos relojes?", "Son los que más eligen los compradores, con materiales sólidos como cristal de zafiro, acero inoxidable y movimientos automáticos.")],
           "sold": "vendidos", "vs": "{a} vs {b}: cuál elegir ({y})", "vsintro": "Dos de los relojes más elegidos de AliExpress, uno al lado del otro.",
           "more_sold": "{x} es el favorito, con {n}+ pedidos.", "lower": "{x} tiene el precio más bajo.", "same": "Los dos se venden muy bien: elige el estilo que más te guste.",
           "price": "Precio", "orders": "Pedidos", "brand_l": "Marca", "feats": "Detalles", "all_g": "Todas las guías"},
    "fr": {"kind": "Les meilleures montres {k} sur AliExpress ({y})", "brand": "Les meilleures montres {b} sur AliExpress ({y})", "top": "Les montres les plus vendues sur AliExpress ({y})",
           "intro": "Les {n} pièces les plus choisies en ce moment, sélectionnées par Kabuzio parmi les meilleures ventes d'AliExpress. Nous regardons les ventes réelles, les avis et les matériaux, et la liste est mise à jour chaque jour.",
           "how": "Notre sélection", "howt": "Seulement des montres avec beaucoup de commandes réelles et de bons avis. Aucune copie de grande marque. Les prix sont vérifiés chaque jour sur AliExpress.",
           "faq": [("Est-ce sûr d'acheter une montre sur AliExpress ?", "Chaque commande est couverte par la Protection acheteur AliExpress : si la montre n'arrive pas ou ne correspond pas, vous êtes remboursé."),
                   ("Livrent-ils dans mon pays ?", "Oui, ces montres sont livrées dans le monde entier. Le délai dépend de votre pays et du vendeur."),
                   ("Pourquoi ces montres ?", "Ce sont les pièces les plus choisies, avec des matériaux solides comme le verre saphir, l'acier inoxydable et les mouvements automatiques.")],
           "sold": "vendues", "vs": "{a} vs {b} : laquelle choisir ({y})", "vsintro": "Deux des montres les plus choisies sur AliExpress, côte à côte.",
           "more_sold": "{x} est la préférée, avec {n}+ commandes.", "lower": "{x} a le prix le plus bas.", "same": "Les deux se vendent très bien : choisissez le style qui vous plaît.",
           "price": "Prix", "orders": "Commandes", "brand_l": "Marque", "feats": "Détails", "all_g": "Tous les guides"},
    "de": {"kind": "Die besten {k}-Uhren auf AliExpress ({y})", "brand": "Die besten {b} Uhren auf AliExpress ({y})", "top": "Die meistverkauften Uhren auf AliExpress ({y})",
           "intro": "Die {n} gefragtesten Uhren im Moment, von Kabuzio aus den AliExpress-Bestsellern ausgewählt. Wir achten auf echte Verkäufe, Bewertungen und Materialien und aktualisieren die Liste täglich.",
           "how": "So wählen wir aus", "howt": "Nur Uhren mit vielen echten Bestellungen und guten Bewertungen. Keine Kopien bekannter Marken. Die Preise werden täglich auf AliExpress geprüft.",
           "faq": [("Ist es sicher, Uhren auf AliExpress zu kaufen?", "Jede Bestellung ist durch den AliExpress Käuferschutz abgesichert: Kommt die Uhr nicht an oder entspricht nicht der Beschreibung, bekommst du dein Geld zurück."),
                   ("Wird in mein Land geliefert?", "Ja, diese Uhren werden weltweit versendet. Die Lieferzeit hängt von deinem Land und dem Verkäufer ab."),
                   ("Warum diese Uhren?", "Es sind die Uhren, die Käufer am häufigsten wählen, mit soliden Materialien wie Saphirglas, Edelstahl und Automatikwerken.")],
           "sold": "verkauft", "vs": "{a} vs {b}: welche wählen ({y})", "vsintro": "Zwei der gefragtesten Uhren auf AliExpress im direkten Vergleich.",
           "more_sold": "{x} ist der Favorit mit {n}+ Bestellungen.", "lower": "{x} hat den niedrigeren Preis.", "same": "Beide verkaufen sich sehr gut: Wähle den Stil, der dir gefällt.",
           "price": "Preis", "orders": "Bestellungen", "brand_l": "Marke", "feats": "Details", "all_g": "Alle Ratgeber"},
    "pt": {"kind": "Os melhores relógios {k} no AliExpress ({y})", "brand": "Os melhores relógios {b} no AliExpress ({y})", "top": "Os relógios mais vendidos do AliExpress ({y})",
           "intro": "As {n} peças mais escolhidas agora, selecionadas pela Kabuzio entre os mais vendidos do AliExpress. Olhamos vendas reais, avaliações e materiais, e atualizamos a lista todos os dias.",
           "how": "Como escolhemos", "howt": "Só relógios com muitos pedidos reais e boas avaliações. Nada de cópias de marcas famosas. Os preços são conferidos todos os dias no AliExpress.",
           "faq": [("É seguro comprar relógios no AliExpress?", "Todo pedido tem a Proteção ao comprador do AliExpress: se o relógio não chegar ou não for como descrito, você recebe o dinheiro de volta."),
                   ("Entregam no meu país?", "Sim, estes relógios são enviados para todo o mundo. O prazo depende do seu país e do vendedor."),
                   ("Por que estes relógios?", "São as peças que os compradores mais escolhem, com materiais sólidos como cristal de safira, aço inoxidável e movimentos automáticos.")],
           "sold": "vendidos", "vs": "{a} vs {b}: qual escolher ({y})", "vsintro": "Dois dos relógios mais escolhidos do AliExpress, lado a lado.",
           "more_sold": "{x} é o favorito, com {n}+ pedidos.", "lower": "{x} tem o preço mais baixo.", "same": "Os dois vendem muito bem: escolha o estilo que mais gosta.",
           "price": "Preço", "orders": "Pedidos", "brand_l": "Marca", "feats": "Detalhes", "all_g": "Todos os guias"},
    "it": {"kind": "I migliori orologi {k} su AliExpress ({y})", "brand": "I migliori orologi {b} su AliExpress ({y})", "top": "Gli orologi più venduti su AliExpress ({y})",
           "intro": "I {n} pezzi più scelti in questo momento, selezionati da Kabuzio tra i più venduti di AliExpress. Guardiamo vendite reali, recensioni e materiali, e aggiorniamo la lista ogni giorno.",
           "how": "Come scegliamo", "howt": "Solo orologi con molti ordini reali e buone recensioni. Nessuna copia di marchi famosi. I prezzi sono controllati ogni giorno su AliExpress.",
           "faq": [("È sicuro comprare orologi su AliExpress?", "Ogni ordine è coperto dalla Protezione acquirente AliExpress: se l'orologio non arriva o non è come descritto, vieni rimborsato."),
                   ("Spediscono nel mio paese?", "Sì, questi orologi vengono spediti in tutto il mondo. I tempi dipendono dal tuo paese e dal venditore."),
                   ("Perché questi orologi?", "Sono i pezzi più scelti dagli acquirenti, con materiali solidi come vetro zaffiro, acciaio inox e movimenti automatici.")],
           "sold": "venduti", "vs": "{a} vs {b}: quale scegliere ({y})", "vsintro": "Due degli orologi più scelti su AliExpress, uno accanto all'altro.",
           "more_sold": "{x} è il preferito, con {n}+ ordini.", "lower": "{x} ha il prezzo più basso.", "same": "Entrambi vendono molto bene: scegli lo stile che ti piace di più.",
           "price": "Prezzo", "orders": "Ordini", "brand_l": "Marca", "feats": "Dettagli", "all_g": "Tutte le guide"},
}

# kind words as they read inside a guide title («relojes automáticos», «montres à quartz»)
PLURAL = {"es": {"Automatic": "automáticos", "Quartz": "de cuarzo", "Sport": "deportivos", "Chronograph": "cronógrafo", "Skeleton": "esqueleto", "Tourbillon": "tourbillon"},
          "fr": {"Automatic": "automatiques", "Quartz": "à quartz", "Sport": "sport", "Chronograph": "chronographe", "Skeleton": "squelette", "Tourbillon": "tourbillon"},
          "pt": {"Automatic": "automáticos", "Quartz": "de quartzo", "Sport": "esportivos", "Chronograph": "cronógrafo", "Skeleton": "esqueleto", "Tourbillon": "tourbillon"},
          "it": {"Automatic": "automatici", "Quartz": "al quarzo", "Sport": "sportivi", "Chronograph": "cronografo", "Skeleton": "scheletrati", "Tourbillon": "tourbillon"}}

CSS = """:root{--ink:#111;--muted:#737373;--line:#ececec;--soft:#f5f5f4}*{box-sizing:border-box;margin:0}
body{font-family:Inter,system-ui,-apple-system,sans-serif;color:var(--ink);background:#fff;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}.nav{border-bottom:1px solid var(--line)}.nav div{max-width:900px;margin:0 auto;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;gap:12px}
.logo{font-weight:700;letter-spacing:.18em;font-size:15px}.back{font-size:13px;color:var(--muted)}
.lg{display:flex;gap:8px;font-size:11px;color:var(--muted)}.lg a.on{color:var(--ink);font-weight:700}@media(max-width:560px){.lg{display:none}}
main{max-width:900px;margin:0 auto;padding:28px 16px 60px}h1{font-size:clamp(24px,4vw,34px);line-height:1.15;letter-spacing:-.01em}
.lead{color:#444;line-height:1.6;margin-top:12px}ol.list{list-style:none;padding:0;margin-top:28px;display:grid;gap:18px}
.it{display:grid;grid-template-columns:110px 1fr;gap:16px;align-items:center;border:1px solid var(--line);border-radius:14px;padding:12px}
.it img{width:110px;height:110px;object-fit:cover;border-radius:10px;background:var(--soft)}.it h2{font-size:16px;line-height:1.3;font-weight:600}
.it .n{font-size:12px;color:var(--muted);letter-spacing:.1em}.it .p{font-weight:700;margin-top:6px}.it .s{font-size:13px;color:var(--muted);margin-top:4px}
.it .go{display:inline-block;margin-top:8px;font-size:13px;font-weight:600;border-bottom:1px solid}
h3{font-size:18px;margin-top:36px}.box p{color:#444;line-height:1.6;margin-top:8px}details{border-top:1px solid var(--line);padding:12px 0}summary{cursor:pointer;font-weight:600}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:24px}.two .c{border:1px solid var(--line);border-radius:14px;padding:14px}
.two img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:10px;background:var(--soft)}.two h2{font-size:15px;margin-top:10px;line-height:1.3}
table{width:100%;border-collapse:collapse;margin-top:20px;font-size:14px}td,th{border-top:1px solid var(--line);padding:10px;text-align:left;vertical-align:top}
.verdict{background:var(--soft);border-radius:12px;padding:14px 16px;margin-top:20px;line-height:1.6}
.cta{display:block;text-align:center;background:var(--ink);color:#fff;border-radius:999px;padding:12px;font-weight:600;margin-top:12px;font-size:14px}
ul.gl{list-style:none;padding:0;margin-top:20px;display:grid;gap:10px}ul.gl a{display:block;border:1px solid var(--line);border-radius:12px;padding:14px;font-weight:600}
footer{text-align:center;color:var(--muted);font-size:12px;padding:24px 16px;border-top:1px solid var(--line)}"""


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def shell(lang, title, desc, path, img, body, ld):
    from paginas import head, langbar
    up = "../" * (1 + (lang != "en"))
    t = T[lang]
    return head(lang, title, desc, path, img) + f"""
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>
<style>{CSS}</style></head><body>
<nav class="nav"><div><a class="logo" href="{up}">KABUZIO</a><span class="lg">{langbar(lang, path, up)}</span><a class="back" href="{up}">{t['all']}</a></div></nav>
<main>{body}</main>
<footer>{t['aff']}<br>© Kabuzio · <a href="{up}">{t['deals']}</a> · <a href="{up}{prefix(lang)}g/">{t['guides']}</a></footer></body></html>"""


def guide(lang, key, title, items):
    t, g = T[lang], G[lang]
    path = f"g/{key}.html"
    up = "../" * (1 + (lang != "en"))
    rows = "".join(
        f'<li class="it"><a href="{up}{prefix(lang)}w/{x["id"]}.html"><img src="{e(x["pics"][0])}_350x350.jpg" alt="{e(x["name"])}" loading="lazy"></a>'
        f'<div><div class="n">#{i + 1}{" · " + e(x["brand"]) if x["brand"] else ""}</div><h2><a href="{up}{prefix(lang)}w/{x["id"]}.html">{e(x["name"])}</a></h2>'
        f'<div class="p">{e(x["price"])}{f" · 🔥 {x["sales"]}+ {g["sold"]}" if x["sales"] else ""}</div>'
        f'<div class="s">{e(" · ".join(tr(lang, f) for f in specs(x["raw"], 3)))}</div>'
        f'<a class="go" href="{e(x["link"])}" rel="nofollow sponsored">{t["cta"]} →</a></div></li>' for i, x in enumerate(items))
    faq = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in g["faq"])
    body = (f"<h1>{e(title)}</h1><p class='lead'>{e(g['intro'].format(n=len(items)))}</p><ol class='list'>{rows}</ol>"
            f"<div class='box'><h3>{g['how']}</h3><p>{e(g['howt'])}</p><h3>FAQ</h3>{faq}</div>")
    ld = [{"@context": "https://schema.org", "@type": "ItemList", "name": title, "itemListElement": [
              {"@type": "ListItem", "position": i + 1, "url": f"{SITE}{prefix(lang)}w/{x['id']}.html", "name": x["name"]} for i, x in enumerate(items)]},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
              {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in g["faq"]]}]
    return path, shell(lang, title, g["intro"].format(n=len(items))[:155], path, items[0]["pics"][0] + "_800x800.jpg", body, ld)


def versus(lang, a, b):
    t, g = T[lang], G[lang]
    key = f"{slug(a['brand'] or 'kabuzio')}-{a['id'][-6:]}-vs-{slug(b['brand'] or 'kabuzio')}-{b['id'][-6:]}"
    path = f"vs/{key}.html"
    up = "../" * (1 + (lang != "en"))
    short = lambda x: " ".join(p for p in (x["brand"], tr(lang, x["kind"])) if p) or x["name"][:40]
    title = g["vs"].format(a=short(a), b=short(b), y=YEAR)
    num = lambda x: float(re.sub(r"[^0-9.]", "", x["price"]) or 0)
    lines = []
    if a["sales"] != b["sales"]:
        top = max(a, b, key=lambda x: x["sales"])
        lines.append(g["more_sold"].format(x=short(top), n=top["sales"]))
    if num(a) != num(b):
        lines.append(g["lower"].format(x=short(min(a, b, key=num))))
    lines.append(g["same"])
    card = lambda x: (f'<div class="c"><a href="{up}{prefix(lang)}w/{x["id"]}.html"><img src="{e(x["pics"][0])}_350x350.jpg" alt="{e(x["name"])}" loading="lazy">'
                      f'<h2>{e(x["name"][:80])}</h2></a><a class="cta" href="{e(x["link"])}" rel="nofollow sponsored">{t["cta"]}</a></div>')
    row = lambda label, f: f"<tr><th>{label}</th><td>{f(a)}</td><td>{f(b)}</td></tr>"
    table = ("<table>" + row(g["brand_l"], lambda x: e(x["brand"] or "—")) + row(g["price"], lambda x: e(x["price"]))
             + row(g["orders"], lambda x: f"{x['sales']}+" if x["sales"] else "—")
             + row(g["feats"], lambda x: "<br>".join(e(tr(lang, f)) for f in specs(x["raw"]))) + "</table>")
    body = (f"<h1>{e(title)}</h1><p class='lead'>{e(g['vsintro'])}</p><div class='two'>{card(a)}{card(b)}</div>{table}"
            f"<div class='verdict'>{'<br>'.join(e(l) for l in lines)}</div>")
    ld = {"@context": "https://schema.org", "@type": "WebPage", "name": title, "about": [
        {"@type": "Product", "name": x["name"], "url": f"{SITE}{prefix(lang)}w/{x['id']}.html"} for x in (a, b)]}
    return path, shell(lang, title, g["vsintro"], path, a["pics"][0] + "_800x800.jpg", body, ld)


def make(ws, put):
    """Writes every guide and comparison in every language; returns their paths (for the sitemap)."""
    best = lambda xs: sorted(xs, key=lambda x: -x["sales"])[:10]
    lists = [("best-selling-watches-aliexpress", None, None, best(ws))]
    for k in sorted({x["kind"] for x in ws if x["kind"]}):
        xs = [x for x in ws if x["kind"] == k]
        if len(xs) >= 4:
            lists.append((f"best-{slug(k)}-watches-aliexpress", k, None, best(xs)))
    for b in sorted({x["brand"] for x in ws if x["brand"]}):
        xs = [x for x in ws if x["brand"] == b]
        if len(xs) >= 4:
            lists.append((f"best-{slug(b)}-watches-aliexpress", None, b, best(xs)))
    # comparisons: the best sellers of each kind, two by two (different brands when possible)
    pairs, used = [], set()
    for k in sorted({x["kind"] for x in ws if x["kind"]}):
        xs = best([x for x in ws if x["kind"] == k])[:6]
        for i, a in enumerate(xs):
            for b in xs[i + 1:]:
                if a["brand"] != b["brand"] and (a["id"], b["id"]) not in used:
                    pairs.append((a, b)); used.add((a["id"], b["id"]))
    pairs = pairs[:30]
    paths = []
    for lang in LANGS:
        g = G[lang]
        links = []
        for key, k, b, items in lists:
            title = g["top"].format(y=YEAR) if not (k or b) else g["kind"].format(k=PLURAL.get(lang, {}).get(k) or tr(lang, k), y=YEAR) if k else g["brand"].format(b=b, y=YEAR)
            path, txt = guide(lang, key, title, items)
            put(prefix(lang) + path, txt); paths.append(prefix(lang) + path); links.append((path, title))
        vs_links = []
        for a, b in pairs:
            path, txt = versus(lang, a, b)
            put(prefix(lang) + path, txt); paths.append(prefix(lang) + path); vs_links.append((path, txt.split("<title>")[1].split(" | ")[0]))
        up = "../" * (1 + (lang != "en"))
        body = (f"<h1>{T[lang]['guides']}</h1><ul class='gl'>" + "".join(f'<li><a href="{up}{prefix(lang)}{p}">{e(t)}</a></li>' for p, t in links) + "</ul>"
                f"<h3>{T[lang]['compare']}</h3><ul class='gl'>" + "".join(f'<li><a href="{up}{prefix(lang)}{p}">{t}</a></li>' for p, t in vs_links) + "</ul>")
        idx = shell(lang, G[lang]["all_g"], G[lang]["intro"].format(n=10)[:155], "g/index.html", ws[0]["pics"][0] + "_800x800.jpg", body,
                    {"@context": "https://schema.org", "@type": "CollectionPage", "name": G[lang]["all_g"]})
        put(prefix(lang) + "g/index.html", idx); paths.append(prefix(lang) + "g/index.html")
    print(len(lists), "guías y", len(pairs), "comparativas por idioma,", len(LANGS), "idiomas")
    return paths
