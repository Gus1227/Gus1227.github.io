# Kabuzio bot: Threads (Cheche, 2026-10-19). 1 post a day: the same watch Instagram just got, all its photos + video.
# THREADS_TOKEN is a 60-day Threads user token (GitHub secret, made with the «User Token Generator» of the Threads app).
# The bot refreshes it every week and keeps the new one encrypted in bot/threads.tok (key = META_TOKEN), so it never expires.
#   THREADS=check    who the token is, how many posts are left today
#   THREADS=post     publish (PUBLICAR=si; anything else only prints). FILA_PUB=<n> forces a row.
import base64, hashlib, json, os, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
API = "https://graph.threads.net/v1.0"
TOK = os.path.join(HERE, "threads.tok")
LAST_IG = "/tmp/kabuzio_ultimo_ig.json"  # written by meta.instagram() in the same turn
PUBLISH = os.environ.get("PUBLICAR", "no").lower() in ("si", "sí", "yes", "true", "1")


# ---------- token ----------
def _box():
    from cryptography.fernet import Fernet
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("threads:" + os.environ["META_TOKEN"]).encode()).digest()))


def _secret_id():
    return hashlib.sha256(os.environ.get("THREADS_TOKEN", "").encode()).hexdigest()[:12]


def _saved():
    try:
        d = json.loads(_box().decrypt(open(TOK, "rb").read()))
        return d if d.get("from") == _secret_id() else None  # a new secret from Cheche always wins
    except Exception:
        return None


def token():
    d = _saved()
    if d:
        return d["token"]
    if not os.environ.get("THREADS_TOKEN"):
        raise SystemExit("Falta el secreto THREADS_TOKEN en GitHub.")
    return os.environ["THREADS_TOKEN"]


def refresh(force=False):
    """Every 7 days ask Threads for a fresh 60-day token. Returns True when bot/threads.tok changed (to commit it)."""
    d = _saved() or {}
    if not force and time.time() - d.get("at", 0) < 7 * 86400:
        return False
    res = call("/refresh_access_token", {"grant_type": "th_refresh_token"}, base="https://graph.threads.net")
    if not res.get("access_token"):
        print("Threads: no pude renovar el token")
        return False
    data = {"token": res["access_token"], "at": time.time(), "from": _secret_id()}
    open(TOK, "wb").write(_box().encrypt(json.dumps(data).encode()))
    print(f"Threads: token renovado ({int(res.get('expires_in', 0)) // 86400} días)")
    return True


def call(path, params=None, post=False, base=API):
    params = dict(params or {}, access_token=token())
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(base + path, data, method="POST") if post else \
        urllib.request.Request(base + path + "?" + data.decode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Threads {path}: {e.code} {e.read()[:500]!r}")


def check():
    me = call("/me", {"fields": "id,username"})
    print("Threads de:", me.get("username"), me.get("id"))
    lim = call(f"/{me['id']}/threads_publishing_limit", {"fields": "quota_usage,config"}).get("data", [{}])[0]
    print("Posts hoy:", lim.get("quota_usage"), "de", (lim.get("config") or {}).get("quota_total"))


# ---------- the post ----------
def pick():
    """The watch Instagram just posted; else the lowest row already on Instagram (like meta.py)."""
    from meta import IG_DONE, LINK, pick as meta_pick
    from telegram import TAB, google_token, sheets
    want = os.environ.get("FILA_PUB", "").strip()
    if not want and os.path.exists(LAST_IG):
        want = os.environ["FILA_PUB"] = str(json.load(open(LAST_IG)).get("fila", ""))
        os.remove(LAST_IG)
    if want:
        tok, n, r, g = meta_pick(IG_DONE)
        if n:
            return tok, n, r, g
    tok = google_token()
    rows = sheets(tok, f"values/{TAB}!A1:CZ?valueRenderOption=FORMATTED_VALUE").get("values", [])
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    cands = [(n, r) for n, r in enumerate(rows[1:], start=2) if g(r, IG_DONE) == "Sí" and g(r, LINK)]
    return (tok, *cands[-1], g) if cands else (tok, None, None, g)


def text(r, g):
    from meta import PRICE, headline
    from reel_publicar import page_of
    from textos import BEST
    head, feats = headline(r, g)
    t = (f"{head}\n{feats + chr(10) if feats else ''}\n💰 Now {g(r, PRICE)}\n{BEST}\n\n"
         f"👉 {page_of(r)}\nNew watches every day · Ad, affiliate link")
    return t[:500]  # Threads limit


def wait(cid):
    for _ in range(40):
        st = call(f"/{cid}", {"fields": "status,error_message"})
        if st.get("status") in ("FINISHED", "PUBLISHED"):
            return True
        if st.get("status") in ("ERROR", "EXPIRED"):
            print("Pieza con error:", st.get("error_message"))
            return False
        time.sleep(10)
    return False


def post():
    from meta import media, NAME
    if PUBLISH:
        refresh()
    tok, n, r, g = pick()
    if not n:
        print("Threads: no hay relojes en Instagram todavía.")
        return
    pics, video = media(r, g)
    items = [("IMAGE", u) for u in pics[:1]] + ([("VIDEO", video)] if video else []) + [("IMAGE", u) for u in pics[1:]]
    items = items[:20]
    cap = text(r, g)
    print(f"Threads fila {n}: {g(r, NAME)}\npiezas: {len(items)} (video: {'sí' if video else 'no'})\n---\n{cap}\n---")
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    uid = call("/me", {"fields": "id"})["id"]
    kids = []
    for kind, url in items if len(items) >= 2 else []:
        p = {"is_carousel_item": "true", "media_type": kind, ("video_url" if kind == "VIDEO" else "image_url"): url}
        try:
            cid = call(f"/{uid}/threads", p, post=True)["id"]
        except SystemExit as e:
            print("Pieza descartada:", e)
            continue
        if wait(cid):
            kids.append(cid)
    base = {"text": cap, "topic_tag": "Watches"}
    if len(kids) >= 2:
        box = call(f"/{uid}/threads", {**base, "media_type": "CAROUSEL", "children": ",".join(kids)}, post=True)["id"]
    elif pics:
        box = call(f"/{uid}/threads", {**base, "media_type": "IMAGE", "image_url": pics[0]}, post=True)["id"]
    else:
        box = call(f"/{uid}/threads", {**base, "media_type": "TEXT"}, post=True)["id"]
    wait(box)
    res = call(f"/{uid}/threads_publish", {"creation_id": box}, post=True)
    print("Threads post:", res.get("id"))


if __name__ == "__main__":
    {"check": check, "post": post, "renovar": lambda: refresh(True)}[os.environ.get("THREADS", "check")]()
