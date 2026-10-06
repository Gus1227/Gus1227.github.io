# Kabuzio bot: posts the next "Pendiente" watch from the Ofertas sheet to Telegram.
# Same post as the Make scenario 7725903 (album with video 2nd, caption, quiet hours),
# and it marks the row the same way (H = Publicado, I = date, S = message id).
import base64, datetime, html, json, os, re, time, urllib.error, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

SHEET = "16DfP-jC1SaFwRdZr6eZputV0KuIyUdMNupfn3rUGwxY"
TAB = "Ofertas"
CHAT = os.environ.get("TG_CHAT", "@KabuzioDeal")
PUBLISH = os.environ.get("PUBLICAR", "no").lower() in ("si", "sí", "yes", "true", "1")

# column indexes (A = 0)
NAME, PRICE, OLD, IMG, LINK, TITLE, TAGS, STATE, DATE, RATING = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
TG_ID, COUPON, VIDEO, EXTRA, LINK_TG, PRIO = 18, 19, 21, 22, 32, 38
BRAND_M, SALES = 12, 13


# ---------- Google Sheets (service account, no extra libraries but cryptography) ----------
def google_token(scope="https://www.googleapis.com/auth/spreadsheets"):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    sa = json.loads(os.environ["GOOGLE_SA_JSON"])
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=")
    now = int(time.time())
    head = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claim = b64(json.dumps({"iss": sa["client_email"], "scope": scope,
                            "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600}).encode())
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    sig = b64(key.sign(head + b"." + claim, padding.PKCS1v15(), hashes.SHA256()))
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": (head + b"." + claim + b"." + sig).decode()}).encode()
    return json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", body, timeout=30))["access_token"]


def sheets(token, path, body=None, method="GET"):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET}" + ("" if path[:1] in "?:" else "/") + path
    req = urllib.request.Request(url, json.dumps(body).encode() if body else None, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


# ---------- links: check that a link opens the right watch ----------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def item_of(url):
    """AliExpress item number a link opens (follows a few redirects), or '' if unknown."""
    opener = urllib.request.build_opener(_NoRedirect)
    for attempt in range(3):
        u = url
        for _ in range(5):
            m = re.search(r"/item/(\d+)", u)
            if m and u is not url:
                return m.group(1)
            try:
                r = opener.open(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20)
                m = re.search(r"aliexpress\.[a-z.]+/item/(\d+)", r.read(200000).decode("utf-8", "ignore"))
                if m:
                    return m.group(1)
                break
            except urllib.error.HTTPError as e:
                loc = e.headers.get("Location")
                if not loc:
                    break
                u = urllib.parse.urljoin(u, loc)
            except Exception:
                break
        time.sleep(1 + attempt * 2)
    return ""


def good_link(r):
    """Telegram link (AG) only if it opens the same watch as Enlace (E); otherwise Enlace."""
    g = lambda i: (r[i] if i < len(r) else "").strip()
    tg_link, main = g(LINK_TG), g(LINK)
    if tg_link and main:
        want = item_of(main)
        if want and item_of(tg_link) == want:
            return tg_link
        print("Link_TG lleva a otro reloj: uso Enlace")
    return main or tg_link


# ---------- the post (copy of the Make caption) ----------
def ventas(v):
    """AliExpress orders from column N. The cell is formatted as a percent, so 662 shows as «66200%»."""
    v = str(v or "").strip()
    return num(v) / (100 if v.endswith("%") else 1)


def num(s):
    s = re.sub(r"[^0-9.]", "", str(s or "").replace(",", ""))
    try:
        return float(s)
    except ValueError:
        return 0.0


def caption(r):
    """Quiet-luxury post: what the watch is, the features its title really lists, price, proof, link."""
    from textos import headline, kind as kind_of, specs
    raw = lambda i: (r[i] if i < len(r) else "").strip()
    g = lambda i: html.escape(raw(i), quote=False)
    p, name = num(g(PRICE)), raw(NAME)
    band = "#under50" if p < 50 else "#50to100" if p < 100 else "#over100"
    kind = {"Chronograph": "#chronograph"}.get(kind_of(name), "")
    if not kind and re.search(r"automatic|mechanical|tourbillon|skeleton", name.lower()):
        kind = "#automatic"
    feats = "".join(f"◦ {html.escape(f)}\n" for f in specs(name))
    sold = ventas(raw(SALES))
    proof = " · ".join(x for x in (f"{int(sold):,}+ sold" if sold >= 50 else "", g(RATING).strip(" ✅")) if x)
    link = html.escape(good_link(r))
    coupon = f"\nCoupon: <code>{g(COUPON)}</code>" if g(COUPON) else ""
    tags = re.sub(r"\s*#\s*$", "", g(TAGS))  # "#Watches #" when the watch has no brand
    return (f"<b>{html.escape(headline(name, raw(BRAND_M)))}</b>\n\n"  # clean name only, never the AliExpress keyword title
            f"{feats}{chr(10) if feats else ''}<b>{g(PRICE)}</b>{' · ' + proof if proof else ''}\n"
            f"Buyer Protection · Worldwide shipping{coupon}\n\n"
            f"<a href=\"{link}\">View the piece →</a>\n\n{tags} {band} {kind} #Kabuzio #ad")


def photos(r):
    g = lambda i: (r[i] if i < len(r) else "").strip()
    out = []
    for u in (g(IMG) + " " + g(EXTRA)).split():
        if u not in out:
            out.append(u)
    from fotos import limpias  # only clean photos, no infographics with text
    return limpias(out, g(BRAND_M))[:10]


def quiet():
    return datetime.datetime.now(ZoneInfo("Europe/London")).hour in (23, 0, 1, 2, 3, 4, 5, 6)


# ---------- Telegram ----------
def tg(method, payload):
    url = f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/{method}"
    req = urllib.request.Request(url, json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    for _ in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            res = json.loads(e.read() or b"{}")
            wait = res.get("parameters", {}).get("retry_after")
            if not wait:
                return res
            time.sleep(wait + 1)
    return res


def send(r):
    cap, pics, video = caption(r), photos(r), (r[VIDEO] if VIDEO < len(r) else "").strip()
    silent = quiet()
    if len(pics) + (1 if video else 0) >= 2:
        media = [{"type": "photo", "media": pics[0] + "_800x800.jpg", "caption": cap, "parse_mode": "HTML"}]
        if video:
            media.append({"type": "video", "media": video})
        media += [{"type": "photo", "media": u + "_800x800.jpg"} for u in pics[1:(9 if video else 10)]]
        res = tg("sendMediaGroup", {"chat_id": CHAT, "media": media, "disable_notification": silent})
        if res.get("ok"):
            return res["result"][0]["message_id"]
        print("album failed, sending one photo:", res.get("description"))
    res = tg("sendPhoto", {"chat_id": CHAT, "photo": (r[IMG] if IMG < len(r) else ""), "caption": cap,
                           "parse_mode": "HTML", "disable_notification": silent})
    if res.get("ok"):
        return res["result"]["message_id"]
    raise SystemExit(f"Telegram error: {res.get('description')}")


def main():
    token = google_token()
    rows = sheets(token, f"values/{TAB}!A1:AM?valueRenderOption=FORMATTED_VALUE").get("values", [])
    want = os.environ.get("FILA_PUB", "").strip()  # "Publicar ahora" from the panel: this exact row
    if want:
        n = int(want)
        r = rows[n - 1]
    else:
        # next "Pendiente": lowest Prioridad (AM) first, then sheet order
        pend = [(n, r) for n, r in enumerate(rows[1:], start=2) if len(r) > STATE and r[STATE].strip() == "Pendiente"]
        if not pend:
            print("No hay relojes Pendiente.")
            return
        n, r = min(pend, key=lambda t: (num(t[1][PRIO]) if len(t[1]) > PRIO and t[1][PRIO].strip() else 1e9, t[0]))
    print(f"Fila {n}: {r[NAME]}\n---\n{caption(r)}\n---\nfotos: {len(photos(r))}, video: {'sí' if len(r) > VIDEO and r[VIDEO].strip() else 'no'}")
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    mid = send(r)
    now = datetime.datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%Y-%m-%d %H:%M:%S")
    sheets(token, "values:batchUpdate", {"valueInputOption": "USER_ENTERED", "data": [
        {"range": f"{TAB}!H{n}:I{n}", "values": [["Publicado", now]]},
        {"range": f"{TAB}!S{n}", "values": [[mid]]},
        {"range": f"{TAB}!AM{n}", "values": [[""]]}]}, method="POST")
    print(f"Publicado en Telegram (mensaje {mid}) y marcado en la hoja.")


if __name__ == "__main__":
    main()
