# Kabuzio bot: Facebook page and Instagram through the Meta Graph API (to replace Make 7725903 and 7728023).
# META_TOKEN is the never-expiring token of the business system user «kabuzio-bot» (GitHub secret). Tokens are never printed.
#   META=check      who the token is and which page / Instagram it can use
#   META=facebook   newest "Publicado" watch not yet on Facebook (U empty): photos post + video, marks U = Sí
#   META=instagram  newest "Publicado" watch not yet on Instagram (Q empty): carousel (video 2nd), marks Q = Sí
# Same choice of watch, captions and marks as the Make scenarios. PUBLICAR=si publishes; anything else only prints.
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
GRAPH = "https://graph.facebook.com/v23.0"
PAGE, IG = "1270319586174146", "17841418825394135"  # Kabuzio Watches, @kabuzio_deal
PUBLISH = os.environ.get("PUBLICAR", "no").lower() in ("si", "sí", "yes", "true", "1")
NAME, PRICE, IMG, LINK, STATE, BRAND, IG_DONE, COUPON, FB_DONE, VIDEO, EXTRA, LINK_FB, HEAD, SPECS = \
    0, 1, 3, 4, 7, 12, 16, 19, 20, 21, 22, 35, 40, 41


def graph(path, params=None, post=False, token=None):
    params = dict(params or {}, access_token=token or os.environ["META_TOKEN"])
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(GRAPH + path, data, method="POST") if post else \
        urllib.request.Request(GRAPH + path + "?" + data.decode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Meta {path}: {e.code} {e.read()[:500]!r}")


def check():
    me = graph("/me", {"fields": "id,name"})
    print("Token de:", me.get("name"), me.get("id"))
    perms = graph("/me/permissions").get("data", [])
    print("Permisos:", ", ".join(p["permission"] for p in perms if p.get("status") == "granted") or "(no se pueden leer)")
    pages = graph("/me/accounts", {"fields": "id,name,instagram_business_account{id,username}"}).get("data", [])
    for p in pages:
        ig = p.get("instagram_business_account") or {}
        print(f"Página: {p['name']} ({p['id']}) · Instagram: {ig.get('username', '—')} ({ig.get('id', '—')})")
    if not pages:
        print("No veo ninguna página: revisa que el usuario del sistema tenga la página asignada.")


# ---------- the watch ----------
def pick(done_col):
    from telegram import TAB, google_token, sheets
    tok = google_token()
    rows = sheets(tok, f"values/{TAB}!A1:CZ?valueRenderOption=FORMATTED_VALUE").get("values", [])
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    want = os.environ.get("FILA_PUB", "").strip()  # "Publicar ahora" from the panel: this exact row
    cands = [(int(want), rows[int(want) - 1])] if want else \
        [(n, r) for n, r in enumerate(rows[1:], start=2) if g(r, STATE) == "Publicado" and not g(r, done_col)]
    if not cands:
        return tok, None, None, g
    n, r = cands[-1]  # Make: sortOrder desc, the lowest one in the sheet
    return tok, n, r, g


def media(r, g):
    pics = []
    for u in (g(r, IMG) + " " + g(r, EXTRA)).split():
        if u not in pics:
            pics.append(u)
    from fotos import limpias  # only clean photos, no infographics with text
    return [u + "_800x800.jpg" for u in limpias(pics, g(r, BRAND))[:10]], g(r, VIDEO)


def headline(r, g):
    from textos import headline as h, specs
    return g(r, HEAD) or h(g(r, NAME), g(r, BRAND)) or g(r, NAME), g(r, SPECS) or " · ".join(specs(g(r, NAME)))


def mark(tok, n, col, value):
    from telegram import TAB, sheets
    letter = chr(65 + col)
    sheets(tok, "values:batchUpdate", {"valueInputOption": "USER_ENTERED",
                                       "data": [{"range": f"{TAB}!{letter}{n}", "values": [[value]]}]}, method="POST")


# ---------- Facebook ----------
def facebook():
    from telegram import item_of
    tok, n, r, g = pick(FB_DONE)
    if not n:
        print("Facebook: no hay relojes nuevos.")
        return
    pics, video = media(r, g)
    head, feats = headline(r, g)
    link = g(r, LINK)
    if g(r, LINK_FB) and item_of(g(r, LINK_FB)) == item_of(link):  # its own Facebook link only if it opens the same watch
        link = g(r, LINK_FB)
    from cupones import linea_ig
    coupon = ("\n" + linea_ig(r).replace("DM you", "message you").rstrip()) if linea_ig(r) else f"\nCoupon: {g(r, COUPON)}" if g(r, COUPON) else ""
    # a coupon from AliExpress is asked for in a comment (fb_respuestas.py sends it by private message)
    text = (f"{head}\n{feats + chr(10) if feats else ''}\n💰 Now {g(r, PRICE)} · Buyer Protection · Worldwide shipping\n"
            f"👉 View the piece: {link}{coupon}\n"
            f"More hand-picked pieces every day on Telegram: https://t.me/KabuzioDeal\n"
            f"Full collection: https://gus1227.github.io\n\n#watchdeals #watches #quietluxury #Kabuzio")
    print(f"Facebook fila {n}: {g(r, NAME)}\nfotos: {len(pics)}, video: {'sí' if video else 'no'}\n---\n{text}\n---")
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    page_tok = graph(f"/{PAGE}", {"fields": "access_token"})["access_token"]
    ids = [graph(f"/{PAGE}/photos", {"url": u, "published": "false"}, post=True, token=page_tok)["id"] for u in pics]
    params = {"message": text}
    for i, pid in enumerate(ids):
        params[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    post = graph(f"/{PAGE}/feed", params, post=True, token=page_tok)
    print("Facebook post:", post.get("id"))
    mark(tok, n, FB_DONE, "Sí")
    if video:
        try:
            v = graph(f"/{PAGE}/videos", {"file_url": video, "description": text}, post=True, token=page_tok)
            print("Facebook video:", v.get("id"))
        except SystemExit as e:  # Make ignores video errors too
            print("Video falló:", e)


# ---------- Instagram ----------
def wait_ready(cid):
    for _ in range(40):  # videos need a while on Meta's side
        st = graph(f"/{cid}", {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            return True
        if st in ("ERROR", "EXPIRED"):
            return False
        time.sleep(10)
    return False


def instagram():
    tok, n, r, g = pick(IG_DONE)
    if not n:
        print("Instagram: no hay relojes nuevos.")
        return
    pics, video = media(r, g)
    head, feats = headline(r, g)
    brand = g(r, BRAND).lstrip("#").lower()
    from cupones import linea_ig
    caption = (f"{head}\n{feats + chr(10) if feats else ''}\n💰 Now {g(r, PRICE)}\n{linea_ig(r)}\n"
               f"👆 Tap the link in our bio to get it · new watches every day\nAd · affiliate link\n.\n"
               f"#watchesofinstagram #watchdeals #quietluxury {('#' + brand) if brand else ''} #kabuzio")
    items = [("IMAGE", u) for u in pics[:1]] + ([("VIDEO", video)] if video else []) + [("IMAGE", u) for u in pics[1:]]
    items = items[:10]
    print(f"Instagram fila {n}: {g(r, NAME)}\npiezas: {len(items)} (video: {'sí' if video else 'no'})\n---\n{caption}\n---")
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    try:
        if len(items) >= 2:
            kids = []
            for kind, url in items:
                p = {"is_carousel_item": "true", **({"media_type": "VIDEO", "video_url": url} if kind == "VIDEO" else {"image_url": url})}
                try:
                    cid = graph(f"/{IG}/media", p, post=True)["id"]
                except SystemExit as e:
                    print("Pieza descartada:", e)
                    continue
                if kind == "VIDEO" and not wait_ready(cid):
                    print("El video no quedó listo: va sin video")
                    continue
                kids.append(cid)
            box = graph(f"/{IG}/media", {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": caption}, post=True)["id"]
        else:
            box = graph(f"/{IG}/media", {"image_url": pics[0], "caption": caption}, post=True)["id"]
        wait_ready(box)
        res = graph(f"/{IG}/media_publish", {"creation_id": box}, post=True)
    except SystemExit as e:  # Make marks the row «Revisar» when Instagram refuses it, and moves on
        print("Instagram falló:", e)
        mark(tok, n, IG_DONE, "Revisar")
        return
    print("Instagram post:", res.get("id"))
    mark(tok, n, IG_DONE, "Sí")



# ---------- music for Reels (Instagram Audio API: only audio cleared for third-party use) ----------
MOODS = ("cinematic", "luxury", "lofi", "piano")


def en_ingles(a):
    """Cheche: only English songs on Instagram. Instagram's music for our account (in Israel) comes with many
    Hebrew songs, so any audio whose title/artist has letters that are not plain English (Hebrew, Arabic…) is skipped."""
    texto = " ".join(str(v) for k, v in a.items() if isinstance(v, str) and k not in ("audio_id", "id"))
    return all(c.isascii() for c in texto if c.isalpha())


def ids_ingles(res):
    """Usable audio ids (English, 15 s or more) from an /ig_audio answer."""
    ok = [a for a in (res.get("audio") or res.get("data") or [])[:25]
          if (a.get("audio_id") or a.get("id")) and a.get("duration_in_ms", 30000) >= 15000 and en_ingles(a)]
    for a in ok:
        print("  canción OK:", a.get("title"), "·", a.get("display_artist") or a.get("artist") or "")
    return [a.get("audio_id") or a.get("id") for a in ok]


def musica(query=None):
    """audio_configuration for a REELS container (a JSON string), or "" when Meta returns nothing.
    Use: graph(f"/{IG}/media", {"media_type": "REELS", "video_url": url, "audio_configuration": musica(), ...}, post=True)"""
    import random
    for q in ([query] if query else random.sample(MOODS, len(MOODS))):
        try:
            res = graph("/ig_audio", {"audio_type": "music", "user_id": IG, "search_query": q})
        except SystemExit as e:
            print("Audio API:", e)
            return ""
        ids = ids_ingles(res)
        if ids:
            pick_id = random.choice(ids)
            print(f"Música «{q}»: {pick_id}")
            return json.dumps({"audio_id": pick_id, "audio_volume": 100, "video_volume": 0})
    return ""


def musica_prueba():
    for q in ("",) + MOODS:  # "" = trending
        p = {"audio_type": "music", "user_id": IG, **({"search_query": q} if q else {})}
        print(q or "(tendencias)", json.dumps(graph("/ig_audio", p))[:600])


if __name__ == "__main__":
    {"check": check, "facebook": facebook, "instagram": instagram, "musica": musica_prueba}[os.environ.get("META", "check")]()
