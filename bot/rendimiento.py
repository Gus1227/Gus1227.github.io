# Kabuzio bot: performance agent. Reads the «Ventas» tab (AliExpress orders, filled by ali.py) and:
#   1. writes a «Rendimiento» tab: sales and commission per network, per brand, per price band and the top watches
#   2. sorts the «Pendiente» queue (AM Prioridad): watches like the ones that sell (same brand, same price band,
#      many AliExpress orders) go first. Only empty cells or our own values (50 and up) are touched:
#      a number below 50 typed by Cheche always wins.
#   3. compliance: a «Pendiente» watch whose title names a famous brand (Rolex, Omega...) is set to «Réplica»,
#      out of the queue and the web. «Seiko NH35 movement» and similar are real parts and do not count.
#   4. repeat what sells: once a day, the best-selling watch last posted 14+ days ago goes back to «Pendiente»
#      at the front of the queue (AM 49) and its network marks (Q Instagram, R TikTok, U Facebook) are cleared,
#      so every network posts it again.
# RENDIMIENTO=si writes; anything else only prints.
import datetime, math, os, re, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from revisar import FAMOUS
from top import when
from telegram import NAME, PRICE, STATE, TAB, PRIO, BRAND_M, SALES, google_token, sheets

WRITE = os.environ.get("RENDIMIENTO", "no").lower() in ("si", "sí", "1")
PID, RATING_O = 23, 14  # X = product id, O = rating
AUTO = 50  # our priorities start here
NETS = {"kabuzioTG": "Telegram", "kabuzioIG": "Instagram", "kabuzioTT": "TikTok", "kabuzioFB": "Facebook",
        "kabuzioWEB": "Web", "kabuzioPIN": "Pinterest"}
BANDS = [(60, 80), (80, 100), (100, 150), (150, 250), (250, 10 ** 6)]


def num(v):
    m = re.search(r"\d[\d,]*(\.\d+)?", str(v or ""))
    return float(m.group().replace(",", "")) if m else 0.0


def band(price):
    for lo, hi in BANDS:
        if lo <= price < hi:
            return f"${lo}–{hi}" if hi < 10 ** 6 else f"${lo}+"
    return "<$60"


def main():
    tok = google_token()
    rows = sheets(tok, f"values/{TAB}!A1:AM?valueRenderOption=FORMATTED_VALUE").get("values", [])
    sales = sheets(tok, "values/Ventas!A1:L").get("values", [])
    head, sales = (sales[0], sales[1:]) if sales else ([], [])
    col = {h: i for i, h in enumerate(head)}
    g = lambda r, i: (r[i] if i < len(r) else "").strip()

    by_pid = {g(r, PID).lstrip("'"): (n, r) for n, r in enumerate(rows[1:], start=2) if g(r, PID)}
    net, brand, bands, watch, other, country = Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    money = defaultdict(float)
    for s in sales:
        pid, tid = g(s, col.get("product_id", 9)), g(s, col.get("tracking_id", 5))
        com = num(g(s, col.get("estimated_paid_commission", 7)))
        net[NETS.get(tid, tid or "?")] += 1
        country[g(s, col.get("ship_to_country", 11)) or "?"] += 1
        money[NETS.get(tid, tid or "?")] += com
        if pid in by_pid:
            r = by_pid[pid][1]
            brand[g(r, BRAND_M) or "?"] += 1
            bands[band(num(g(r, PRICE)))] += 1
            watch[pid] += 1
        else:
            other[g(s, col.get("product_title", 10))[:60] or pid] += 1

    # ---- 1. report ----
    table = [["Kabuzio · Rendimiento (últimos pedidos de AliExpress)", "", ""], ["Pedidos en total", len(sales), ""], [],
             ["Por red", "Pedidos", "Comisión $"]]
    table += [[k, v, round(money[k], 2)] for k, v in net.most_common()]
    table += [[], ["Por país", "Pedidos", ""]] + [[k, v, ""] for k, v in country.most_common(15)]
    table += [[], ["Por marca (relojes de la hoja)", "Pedidos", ""]] + [[k, v, ""] for k, v in brand.most_common(15)]
    table += [[], ["Por precio", "Pedidos", ""]] + [[k, v, ""] for k, v in bands.most_common()]
    table += [[], ["Relojes más vendidos", "Pedidos", "Fila"]]
    table += [[g(by_pid[p][1], NAME)[:70], v, by_pid[p][0]] for p, v in watch.most_common(10)]
    table += [[], ["Compras de otros productos (no están en la hoja)", "Pedidos", ""]] + [[k, v, ""] for k, v in other.most_common(10)]
    for line in table:
        print(" | ".join(str(c) for c in line))

    # ---- 2. queue order ----
    pend, fake = [], []
    for n, r in enumerate(rows[1:], start=2):
        if g(r, STATE) != "Pendiente":
            continue
        title = re.sub(r"(seiko|citizen|miyota)[^,;|]{0,25}?(movement|movt|mechanism|caliber|calibre)|(seiko|miyota|citizen)\s*(japan\s*)?(nh|vh|vk|pt)\d+\w*",
                       "", g(r, NAME).lower())  # a Seiko/Miyota MOVEMENT is a real part, not a fake brand
        if FAMOUS.search(title):
            fake.append(n)
            continue
        cur = g(r, PRIO)
        if cur and num(cur) < AUTO:
            continue  # Cheche's own priority
        score = 10 * brand[g(r, BRAND_M)] + 5 * bands[band(num(g(r, PRICE)))] + math.log10(1 + num(g(r, SALES)))
        if num(g(r, RATING_O)) and num(g(r, RATING_O)) < 90:
            score -= 1
        pend.append((score, n, cur))
    pend.sort(key=lambda t: (-t[0], t[1]))
    cells = [(f"AM{n}", str(AUTO + i)) for i, (_, n, cur) in enumerate(pend) if cur != str(AUTO + i)]
    cells += [(f"H{n}", "Réplica") for n in fake]
    old = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=14)
    again = [(v, by_pid[p][0]) for p, v in watch.most_common() if g(by_pid[p][1], STATE) == "Publicado"
             and (when(g(by_pid[p][1], 8)) or old) <= old]
    if again:
        n = again[0][1]
        cells += [(f"H{n}", "Pendiente"), (f"AM{n}", str(AUTO - 1))] + [(f"{c}{n}", "") for c in "QRU"]
        print(f"Repetir: fila {n} ({again[0][0]} ventas) vuelve a la cola, primera.")
    print("Posibles réplicas (marca famosa en el título):", ", ".join(f"fila {n}: {g(rows[n - 1], NAME)[:120]}" for n in fake) or "ninguna")
    print(f"\nCola: {len(pend)} relojes Pendiente ordenados; {len(cells)} cambios. Primeros:",
          ", ".join(f"fila {n} ({s:.1f})" for s, n, _ in pend[:8]))
    if not WRITE:
        print("Modo prueba: no se escribe nada.")
        return

    meta = sheets(tok, "?fields=sheets.properties")
    if not any(s["properties"]["title"] == "Rendimiento" for s in meta["sheets"]):
        sheets(tok, ":batchUpdate", {"requests": [{"addSheet": {"properties": {"title": "Rendimiento"}}}]}, method="POST")
    out = [([str(c) for c in l] + ["", "", ""])[:3] for l in table] + [["", "", ""]] * max(0, 120 - len(table))
    sheets(tok, "values/Rendimiento!A1:C?valueInputOption=RAW", {"values": out}, method="PUT")  # blanks clear old lines
    for i in range(0, len(cells), 400):
        sheets(tok, "values:batchUpdate", {"valueInputOption": "USER_ENTERED", "data": [
            {"range": f"{TAB}!{a}", "values": [[v]]} for a, v in cells[i:i + 400]]}, method="POST")
    print("Rendimiento escrito.")


if __name__ == "__main__":
    main()
