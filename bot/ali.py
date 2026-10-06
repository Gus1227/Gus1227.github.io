# Kabuzio bot: AliExpress affiliate API (replaces the Make scenarios for details, links and sales).
#   completar: fills empty data of new rows (name, prices, photos, video, sales, rating, product id) from the link
#   links:     one short affiliate link per network in AG:AL (kabuzioTG/IG/TT/FB/WEB/PIN), matched by source_value
#   ventas:    orders of the last 30 days into the «Ventas» tab (one row per sub-order, updated in place)
#   revision:  once a day, prices and watches that no longer exist (and one «Price drop» post in Telegram)
# Run: ALI_HACER="completar links" (default), "ventas" or "revision" (PUBLICAR=si to post the price drop). Secrets: ALI_APP_KEY, ALI_SECRET.
import datetime, hashlib, hmac, json, os, sys, time, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
from telegram import TAB, google_token, item_of, sheets

API = "https://api-sg.aliexpress.com/sync"
PUBLICAR = os.environ.get("PUBLICAR", "no").lower() in ("si", "sí", "yes", "true", "1")
NETS = [("AG", "kabuzioTG"), ("AH", "kabuzioIG"), ("AI", "kabuzioTT"), ("AJ", "kabuzioFB"), ("AK", "kabuzioWEB"), ("AL", "kabuzioPIN")]
COL = lambda c: sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(c))) - 1  # "AG" -> 32


def ali(method, **params):
    for attempt in range(6):
        res = _ali(method, **params)
        if not isinstance(res, str):
            return res
        print("espero:", res[:300], flush=True)
        time.sleep(5 + attempt * 5)  # "Api access frequency exceeds the limit": wait and retry
    raise SystemExit(f"AliExpress {method}: límite de llamadas")


def _ali(method, **params):
    time.sleep(1.2)
    p = {"app_key": os.environ["ALI_APP_KEY"].strip(), "method": method, "sign_method": "sha256",
         "timestamp": str(int(time.time() * 1000)), **{k: str(v) for k, v in params.items()}}
    base = "".join(k + p[k] for k in sorted(p))
    p["sign"] = hmac.new(os.environ["ALI_SECRET"].strip().encode(), base.encode(), hashlib.sha256).hexdigest().upper()
    res = json.load(urllib.request.urlopen(API + "?" + urllib.parse.urlencode(p), timeout=60))
    body = next(iter(res.values()))
    if "ApiCallLimit" in json.dumps(res):
        return json.dumps(res)
    if "error_response" in res or not isinstance(body, dict):
        raise SystemExit(f"AliExpress {method}: {json.dumps(res)[:400]}")
    return body.get("resp_result", body)


def read_rows(tok):
    return sheets(tok, f"values/{TAB}!A1:AN?valueRenderOption=FORMATTED_VALUE").get("values", [])


def write(tok, cells):
    """cells: [(a1, value)]"""
    for i in range(0, len(cells), 400):
        sheets(tok, "values:batchUpdate", {"valueInputOption": "USER_ENTERED", "data": [
            {"range": f"{TAB}!{a}", "values": [[v]]} for a, v in cells[i:i + 400]]}, method="POST")


def cell(r, c):
    i = COL(c)
    return (r[i] if i < len(r) else "").strip()


# ---------- completar: rows that only have a link ----------
def completar(tok, rows):
    todo = []
    for n, r in enumerate(rows[1:], start=2):
        if cell(r, "E").startswith("http") and not (cell(r, "A") and cell(r, "B") and cell(r, "D") and cell(r, "X")):
            pid = cell(r, "X") or item_of(cell(r, "E"))
            if pid:
                todo.append((n, r, pid))
    print("completar:", len(todo), "filas")
    cells = []
    for i in range(0, len(todo), 20):
        part = todo[i:i + 20]
        res = ali("aliexpress.affiliate.productdetail.get", product_ids=",".join(p for _, _, p in part),
                  target_currency="USD", target_language="EN", tracking_id="kabuzioTG")
        prods = {str(p["product_id"]): p for p in ((res.get("result") or {}).get("products") or {}).get("product", [])}
        for n, r, pid in part:
            p = prods.get(pid)
            if not p:
                print(f"fila {n}: la API no da el producto {pid}")
                continue
            imgs = [p.get("product_main_image_url", "")] + ((p.get("product_small_image_urls") or {}).get("string") or [])
            imgs = list(dict.fromkeys(u for u in imgs if u))
            new = {"A": p.get("product_title", ""), "B": f"${p['target_sale_price']}" if p.get("target_sale_price") else "",
                   "C": f"${p['target_original_price']}" if p.get("target_original_price") else "",
                   "D": imgs[0] if imgs else "", "W": " ".join(imgs[1:10]), "V": p.get("product_video_url", ""),
                   "X": pid, "N": str(p.get("lastest_volume", "")), "O": p.get("evaluate_rate", "")}
            for c, v in new.items():
                if v and not cell(r, c):
                    cells.append((f"{c}{n}", v))
            if not cell(r, "H"):
                cells.append((f"H{n}", "Pendiente" if (p.get("target_sale_price") and float(p["target_sale_price"]) >= 60) else "Bajo 60"))
    write(tok, cells)
    print("completar: escritas", len(cells), "celdas")


# ---------- links: one short link per network ----------
def links(tok, rows):
    cells = []
    for col, tracking in NETS:
        need = [(n, cell(r, "E")) for n, r in enumerate(rows[1:], start=2)
                if cell(r, "E").startswith("http") and "/e/" not in cell(r, col) and cell(r, "H") in ("Pendiente", "Publicado", "")]
        for i in range(0, len(need), 5):  # long links: few per call so the URL stays short
            part = need[i:i + 5]
            res = ali("aliexpress.affiliate.link.generate", promotion_link_type=0,
                      source_values=",".join(u for _, u in part), tracking_id=tracking)
            got = {l.get("source_value"): l.get("promotion_link") for l in
                   ((res.get("result") or {}).get("promotion_links") or {}).get("promotion_link", [])}
            for n, u in part:  # matched by source_value: the API returns them in another order
                if got.get(u):
                    cells.append((f"{col}{n}", got[u]))
    write(tok, cells)
    print("links: escritos", len(cells))


# ---------- revision: once a day, every watch on the web against AliExpress ----------
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estado.json")


def revision(tok, rows):
    """Price changes go to column B; a watch the API stops giving two days in a row becomes «No disponible»;
    under 60 $ becomes «Bajo 60». A published watch that drops 10 % or more gets one «Price drop» post (max 1 a day)."""
    from telegram import num
    st = json.load(open(STATE_FILE))
    faltan, hoy = st.get("faltan", {}), datetime.date.today().isoformat()
    live = [(n, r, cell(r, "X")) for n, r in enumerate(rows[1:], start=2) if cell(r, "H") in ("Pendiente", "Publicado") and cell(r, "X")]
    cells, drops, gone = [], [], []
    skipped = 0
    for i in range(0, len(live), 20):
        part = live[i:i + 20]
        time.sleep(3)
        try:
            res = ali("aliexpress.affiliate.productdetail.get", product_ids=",".join(p for _, _, p in part),
                      target_currency="USD", target_language="EN", tracking_id="kabuzioTG")
        except SystemExit as e:  # AliExpress busy: these watches wait for tomorrow, never marked as gone
            print(e)
            skipped += len(part)
            continue
        prods = {str(p["product_id"]): p for p in ((res.get("result") or {}).get("products") or {}).get("product", [])}
        print(f"revision: {i + len(part)} de {len(live)}", flush=True)
        for p in prods.values():
            if p.get("promo_code_info") and os.environ.get("DEBUG"):
                print("  cupón:", p["product_id"], json.dumps(p["promo_code_info"])[:300])
        for n, r, pid in part:
            p = prods.get(pid)
            if not p or not p.get("target_sale_price"):
                if faltan.get(pid) and faltan[pid] != hoy:  # missing yesterday too: really gone
                    cells.append((f"H{n}", "No disponible"))
                    gone.append(cell(r, "AO") or cell(r, "A")[:50])
                    faltan.pop(pid)
                else:
                    faltan.setdefault(pid, hoy)
                continue
            faltan.pop(pid, None)
            new, old = float(p["target_sale_price"]), num(cell(r, "B"))
            if old and abs(new - old) / old >= 0.02:
                print(f"  fila {n}: ${old:.2f} -> ${new:.2f}")
                cells.append((f"B{n}", f"${new:.2f}"))
                if new < 60:
                    cells.append((f"H{n}", "Bajo 60"))
                elif old * 0.5 <= new <= old * 0.9 and cell(r, "H") == "Publicado":  # more than 50 % is an old wrong price, not a deal
                    drops.append((old - new, n, r, old, new))
    write(tok, cells)
    st = json.load(open(STATE_FILE))  # fresh copy: other steps may have changed it
    st["faltan"] = faltan
    if drops and st.get("bajada") != hoy:
        _, n, r, old, new = max(drops)
        if PUBLICAR:
            st["bajada"] = hoy
            precio_bajo(r, old, new)
        print(f"bajada de precio: fila {n} ${old:.2f} -> ${new:.2f}")
    json.dump(st, open(STATE_FILE, "w"), indent=1)
    print(f"revision: {len(live)} relojes, {len(cells)} cambios, {len(gone)} ya no existen, {len(drops)} bajadas, {skipped} sin revisar")
    if gone:
        import aviso
        aviso.enviar("🧹 Gus quitó de la web " + str(len(gone)) + " reloj(es) que ya no existen en AliExpress:\n• " + "\n• ".join(gone[:10]))


def precio_bajo(r, old, new):
    """«Price drop» post in the Telegram channel: one photo, the clean name, old and new price, the link."""
    import html
    from telegram import CHAT, quiet, tg
    link = cell(r, "AG") if "/e/" in cell(r, "AG") else cell(r, "E")
    name = cell(r, "AO") or cell(r, "A")[:70]
    cap = (f"📉 <b>Price drop</b>\n\n<b>{html.escape(name)}</b>\n"
           f"Now <b>${new:.2f}</b> · was <s>${old:.2f}</s> (−{round((old - new) / old * 100)}%)\n"
           f"Buyer Protection · Worldwide shipping\n\n<a href=\"{html.escape(link)}\">View the piece →</a>\n\n#pricedrop #Kabuzio #ad")
    res = tg("sendPhoto", {"chat_id": CHAT, "photo": cell(r, "D"), "caption": cap, "parse_mode": "HTML", "disable_notification": quiet()})
    print("Price drop:", "publicado" if res.get("ok") else res.get("description"))


# ---------- ventas ----------
FIELDS = ("created_time,paid_time,finished_time,order_status,tracking_id,paid_amount,estimated_paid_commission,"
          "estimated_finished_commission,product_id,product_title,ship_to_country,sub_order_id,order_id")
HEAD = ["sub_order_id", "order_id", "created_time", "paid_time", "order_status", "tracking_id", "paid_amount",
        "estimated_paid_commission", "estimated_finished_commission", "product_id", "product_title", "ship_to_country"]


def ventas(tok):
    la = ZoneInfo("America/Los_Angeles")
    fin = datetime.datetime.now(la)
    ini = fin - datetime.timedelta(days=30)
    orders = []
    for status in ("Payment Completed", "Buyer Confirmed Receipt"):
        page = 1
        while True:
            res = ali("aliexpress.affiliate.order.list", start_time=ini.strftime("%Y-%m-%d %H:%M:%S"),
                      end_time=fin.strftime("%Y-%m-%d %H:%M:%S"), fields=FIELDS, status=status, page_no=page, page_size=50)
            got = ((res.get("result") or {}).get("orders") or {}).get("order", [])
            orders += got
            if len(got) < 50:
                break
            page += 1
    meta = sheets(tok, "?fields=sheets.properties")
    if not any(s["properties"]["title"] == "Ventas" for s in meta["sheets"]):
        sheets(tok, ":batchUpdate", {"requests": [{"addSheet": {"properties": {"title": "Ventas"}}}]}, method="POST")
    old = sheets(tok, "values/Ventas!A1:L").get("values", [])
    by = {r[0]: r for r in old[1:] if r}
    nuevas = [o for o in orders if str(o.get("sub_order_id")) not in by] if old else []  # first ever read: no alerts
    for o in orders:
        by[str(o.get("sub_order_id"))] = [str(o.get(h, "")) for h in HEAD]
    table = [HEAD] + sorted(by.values(), key=lambda r: r[2], reverse=True)
    sheets(tok, "values/Ventas!A1:L?valueInputOption=RAW", {"values": table}, method="PUT")
    print("ventas:", len(orders), "en 30 días,", len(table) - 1, "en total")
    if nuevas:
        aviso_venta(nuevas, len(table) - 1)


RED = {"kabuzioTG": "Telegram", "kabuzioIG": "Instagram", "kabuzioTT": "TikTok", "kabuzioFB": "Facebook",
       "kabuzioWEB": "la web", "kabuzioPIN": "Pinterest"}


def aviso_venta(nuevas, total):
    """Private message to Cheche for every new sale (bot/aviso.py)."""
    import html
    import aviso
    for o in nuevas[:10]:
        com = o.get("estimated_paid_commission") or o.get("estimated_finished_commission") or "?"
        aviso.enviar(f"💰 <b>¡Venta nueva!</b>\n{html.escape(str(o.get('product_title', ''))[:90])}\n"
                     f"Pagó ${o.get('paid_amount', '?')} · tu comisión ≈ ${com}\n"
                     f"Vino de: {RED.get(o.get('tracking_id'), o.get('tracking_id') or '?')} · país: {o.get('ship_to_country', '?')}\n"
                     f"Ventas en total: {total}")


def main():
    tok = google_token()
    hacer = os.environ.get("ALI_HACER", "completar links").split()
    if "completar" in hacer:
        try:
            completar(tok, read_rows(tok))
        except SystemExit as e:  # keep going: links do not depend on it
            print(e)
    if "links" in hacer:
        links(tok, read_rows(tok))
    if "ventas" in hacer:
        ventas(tok)
    if "revision" in hacer:
        revision(tok, read_rows(tok))


if __name__ == "__main__":
    main()
