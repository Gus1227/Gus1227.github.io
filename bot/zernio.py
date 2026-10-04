# Kabuzio bot: TikTok and Pinterest through the Zernio API.
# Same posts as Make: TikTok = scenario 7728023 (photo carousel with music + video post, marks R = "Sí"),
# Pinterest = scenario 7763492 (1 pin from pins/q/<n>.json every 2 h).
import datetime, json, os, sys, time, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from telegram import NAME, PRICE, IMG, STATE, VIDEO, EXTRA, TAB, google_token, sheets

API = "https://zernio.com/api/v1"
REDES = os.environ.get("REDES", "").split()  # "tiktok" and/or "pinterest"
PUBLISH = os.environ.get("PUBLICAR", "no").lower() in ("si", "sí", "yes", "true", "1")
BRAND, TT_DONE = 12, 17  # M = marca, R = salió en TikTok


def zernio(path, body=None):
    req = urllib.request.Request(API + path, json.dumps(body).encode() if body is not None else None,
                                 method="POST" if body is not None else "GET",
                                 headers={"Authorization": f"Bearer {os.environ['ZERNIO_KEY']}",
                                          "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Zernio {path}: {e.code} {e.read()[:500]!r}")


# ---------- TikTok ----------
def tiktok():
    token = google_token()
    rows = sheets(token, f"values/{TAB}!A1:CZ?valueRenderOption=FORMATTED_VALUE").get("values", [])
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    # Make takes the LAST published row that has not gone to TikTok yet
    pick = [(n, r) for n, r in enumerate(rows[1:], start=2) if g(r, STATE) == "Publicado" and not g(r, TT_DONE)]
    if not pick:
        print("TikTok: no hay relojes nuevos.")
        return
    n, r = pick[-1]
    pics = []
    for u in (g(r, IMG) + " " + g(r, EXTRA)).split():
        if u not in pics:
            pics.append(u)
    pics = pics[:10]
    brand = f"#{g(r, BRAND).lower()}" if g(r, BRAND) else ""
    desc = (f"⌚ {g(r, NAME)}\n💰 Now {g(r, PRICE)}\n\n🔗 Link in bio\n📲 More deals every day on Telegram @KabuzioDeal\n\n"
            f"#ad #watches #watchtok {brand} #kabuziodeal")
    video = g(r, VIDEO)
    print(f"TikTok fila {n}: {g(r, NAME)}\nfotos: {len(pics)}, video: {'sí' if video else 'no'}\n---\n{desc}\n---")
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    accs = zernio("/accounts")
    accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
    acc = next(a["_id"] for a in accs if str(a.get("platform", "")).lower() == "tiktok")
    if pics:
        res = zernio("/posts", {"content": f"⌚ {g(r, NAME)[:80]}",
                                "mediaItems": [{"type": "image", "url": u + "_800x800.jpg"} for u in pics],
                                "platforms": [{"platform": "tiktok", "accountId": acc}],
                                "tiktokSettings": {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True,
                                                   "media_type": "photo", "photo_cover_index": 0, "description": desc,
                                                   "auto_add_music": True, "content_preview_confirmed": True,
                                                   "express_consent_given": True},
                                "publishNow": True})
        print("TikTok fotos:", json.dumps(res)[:300])
    if video:
        try:
            res = zernio("/posts", {"content": desc, "mediaItems": [{"type": "video", "url": video}],
                                    "platforms": [{"platform": "tiktok", "accountId": acc}],
                                    "tiktokSettings": {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True,
                                                       "allow_duet": False, "allow_stitch": False,
                                                       "content_preview_confirmed": True, "express_consent_given": True},
                                    "publishNow": True})
            print("TikTok video:", json.dumps(res)[:300])
        except SystemExit as e:  # Make ignores video errors too
            print("Video falló:", e)
    sheets(token, "values:batchUpdate", {"valueInputOption": "USER_ENTERED",
                                         "data": [{"range": f"{TAB}!R{n}", "values": [["Sí"]]}]}, method="POST")
    print("TikTok publicado y marcado en la hoja (R).")


# ---------- Pinterest ----------
def pinterest():
    # same turn number as Make 7763492: round((unix - 1791128378) / 7200) + 77
    n = round((time.time() - 1791128378) / 7200) + 77
    f = os.path.join(os.path.dirname(__file__), "..", "pins", "q", f"{n}.json")
    if not os.path.exists(f):
        print(f"Pinterest: no hay pin {n} (está apagado o la cola terminó).")
        return
    body = json.load(open(f, encoding="utf-8"))
    print(f"Pinterest pin {n}: {body['platforms'][0]['platformSpecificData']['title']}")
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    print("Pinterest:", json.dumps(zernio("/posts", body))[:300])


if __name__ == "__main__":
    if os.environ.get("ZERNIO_KEY") and not PUBLISH:
        accs = zernio("/accounts")
        accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
        print("Llave OK. Cuentas en Zernio:", [(a.get("platform"), a.get("_id")) for a in accs])
    if "tiktok" in REDES:
        tiktok()
    if "pinterest" in REDES:
        pinterest()
