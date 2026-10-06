# Kabuzio bot: publishes the newest Reel (r/ultimo.json, made by reel.py) on the networks Cheche picked in the editor.
#   REDES=instagram,facebook,tiktok,pinterest,telegram   PUBLICAR=si (anything else only prints)
# Where each Reel went is kept in r/publicados.json ({product id: {network: date}}), the editor shows it.
import datetime, json, os, subprocess, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from telegram import CHAT, NAME, PRICE, TAB, BRAND_M, caption as tg_caption, google_token, sheets, tg

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DONE = os.path.join(ROOT, "r", "publicados.json")
ALL = ["instagram", "facebook", "tiktok", "pinterest", "telegram"]
REDES = [x for x in os.environ.get("REDES", "").replace(",", " ").split() if x in ALL] or ALL
PUBLISH = os.environ.get("PUBLICAR", "no").lower() in ("si", "sí", "yes", "true", "1")
BOARD, PIN_ACC = "1089026822335308630", "6ac2543ed3257a1645992aa0"


def live(url):
    """GitHub Pages needs a minute or two after the push before the video can be downloaded."""
    for _ in range(40):
        try:
            if urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30).status == 200:
                return True
        except Exception:
            pass
        time.sleep(15)
    return False


def texts(r):
    from textos import headline, specs, tag
    g = lambda i: (r[i] if i < len(r) else "").strip()
    head, feats = headline(g(NAME), g(BRAND_M)), specs(g(NAME), 3)
    brand = tag(g(BRAND_M)) or ""
    from cupones import linea_ig
    ig = (f"{head}\n{' · '.join(feats) + chr(10) if feats else ''}\n💰 Now {g(PRICE)}\n{linea_ig(r)}\n"
          f"👆 Tap the link in our bio to get it · new watches every day\nAd · affiliate link\n.\n"
          f"#watchesofinstagram #watchdeals #quietluxury #reels {brand} #kabuzio")
    tt = (f"{head}\n{' · '.join(feats)}{chr(10) if feats else ''}{g(PRICE)}\n\n"
          f"👆 Tap the link in our bio to get it · new watches every day\n\n#ad #watches #watchtok #quietluxury {brand} #kabuzio")
    fb = (f"{head}\n{' · '.join(feats) + chr(10) if feats else ''}💰 Now {g(PRICE)}\n\n"
          f"Get it here 👉 {g(35) or g(4)}\nAd · affiliate link\n\n#Kabuzio #watches {brand}")
    title = (f"{head} · {' · '.join(feats[:2])}" if feats else head)[:100]
    return ig, tt, fb, title


def page_of(r):
    """The watch's own page on the web (same address as bot/paginas.py)."""
    import hashlib, re
    g = lambda i: (r[i] if i < len(r) else "").strip()
    link, name = g(4), g(NAME)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60].rstrip("-")
    return f"https://gus1227.github.io/w/{slug}-{hashlib.sha1(link.encode()).hexdigest()[:6]}.html"


def trending():
    """audio_configuration with one of Instagram's trending songs right now, or "" if Meta gives none."""
    import random
    from meta import IG, graph
    try:
        res = graph("/ig_audio", {"audio_type": "music", "user_id": IG})  # no search = trending
    except SystemExit as e:
        print("Audio API:", e)
        return ""
    ids = [a.get("audio_id") or a.get("id") for a in (res.get("audio") or res.get("data") or [])[:10]
           if (a.get("audio_id") or a.get("id")) and a.get("duration_in_ms", 30000) >= 15000]
    if not ids:
        return ""
    pick = random.choice(ids)
    print("Música en tendencia:", pick)
    return json.dumps({"audio_id": pick, "audio_volume": 100, "video_volume": 0})


def instagram(url, cap):
    from meta import IG, graph, musica, wait_ready
    cfg = trending() or musica()  # Instagram music (Audio API): trending first (Cheche), else a quiet mood
    cid = graph(f"/{IG}/media", {"media_type": "REELS", "video_url": url, "caption": cap, "share_to_feed": "true",
                                 **({"audio_configuration": cfg} if cfg else {})}, post=True)["id"]
    if not wait_ready(cid):
        raise SystemExit("Instagram: el video no quedó listo")
    return graph(f"/{IG}/media_publish", {"creation_id": cid}, post=True).get("id")


def facebook(url, cap):
    from meta import PAGE, graph
    page_tok = graph(f"/{PAGE}", {"fields": "access_token"})["access_token"]
    return graph(f"/{PAGE}/videos", {"file_url": url, "description": cap}, post=True, token=page_tok).get("id")


def tiktok(url, cap):
    from zernio import zernio
    accs = zernio("/accounts")
    accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
    acc = next(a["_id"] for a in accs if str(a.get("platform", "")).lower() == "tiktok")
    return zernio("/posts", {"content": cap, "mediaItems": [{"type": "video", "url": url}],
                             "platforms": [{"platform": "tiktok", "accountId": acc}],
                             "tiktokSettings": {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True,
                                                "allow_duet": False, "allow_stitch": False,
                                                "content_preview_confirmed": True, "express_consent_given": True},
                             "publishNow": True}).get("_id", "ok")


def pinterest(url, cap, title, link):
    from zernio import zernio
    return zernio("/posts", {"content": cap[:500], "mediaItems": [{"type": "video", "url": url}], "publishNow": True,
                             "platforms": [{"platform": "pinterest", "accountId": PIN_ACC,
                                            "platformSpecificData": {"title": title, "boardId": BOARD, "link": link}}]}).get("_id", "ok")


def telegram(url, r):
    res = tg("sendVideo", {"chat_id": CHAT, "video": url, "caption": tg_caption(r), "parse_mode": "HTML",
                           "supports_streaming": True})
    if not res.get("ok"):
        raise SystemExit(f"Telegram: {res.get('description')}")
    return res["result"]["message_id"]


def main():
    last = json.load(open(os.path.join(ROOT, "r", "ultimo.json")))
    n, pid, url = last["fila"], last["pid"], last["url"]
    url_m = last.get("url_m") or url  # with our own music: for the networks whose API can't add a song
    rows = sheets(google_token(), f"values/{TAB}!A1:AL?valueRenderOption=FORMATTED_VALUE").get("values", [])
    r = rows[n - 1]
    ig, tt, fb, title = texts(r)
    print(f"Reel fila {n} ({pid}) → {', '.join(REDES)}\n{url}\n---\n{ig}\n---")
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    if not live(url) or not live(url_m):
        raise SystemExit("El video todavía no está en la web: prueba otra vez en unos minutos.")
    done, ok = {}, []
    for red in REDES:
        try:
            res = {"instagram": lambda: instagram(url, ig), "facebook": lambda: facebook(url_m, fb),
                   "tiktok": lambda: tiktok(url_m, tt), "pinterest": lambda: pinterest(url_m, ig, title, page_of(r) + "?src=pin"),
                   "telegram": lambda: telegram(url_m, r)}[red]()
            print(f"{red}: publicado ({res})")
            done[red] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
            ok.append(red)
        except (SystemExit, Exception) as e:  # one network failing never stops the others
            print(f"{red}: falló: {e}")
    run = lambda *a: subprocess.run(["git", *a], cwd=ROOT)
    run("pull", "-q", "--rebase", "origin", "main")
    pub = json.load(open(DONE)) if os.path.exists(DONE) else {}
    pub.setdefault(pid, {}).update(done)
    json.dump(pub, open(DONE, "w"), indent=1, sort_keys=True)
    run("add", DONE)
    run("commit", "-qm", f"bot: reel fila {n} publicado en {', '.join(ok) or 'nada'}")
    run("push", "-q", "origin", "HEAD:main")
    if len(ok) < len(REDES):
        raise SystemExit(f"Publicado en {len(ok)} de {len(REDES)} redes (mira arriba cuál falló).")


if __name__ == "__main__":
    main()
