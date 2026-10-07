# Kabuzio bot: TikTok and Pinterest through the Zernio API.
# Same posts as Make: TikTok = scenario 7728023 (photos as a video with our music + video post, marks R = "Sí"),
# Pinterest = scenario 7763492 (1 pin from pins/q/<n>.json every 2 h).
import datetime, json, os, re, sys, time, urllib.error, urllib.request

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
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def slideshow(pics, name):
    """The photos as a vertical video with our own music (no lyrics), saved in t/<name>.mp4 and pushed to the web.
    TikTok's automatic music for photo posts picks songs for Israel (Hebrew), so Cheche wants ours instead."""
    import subprocess
    from musica_libre import with_music
    os.makedirs(os.path.join(ROOT, "t"), exist_ok=True)
    tmp, files = os.path.join(ROOT, "t", "tmp"), []
    os.makedirs(tmp, exist_ok=True)
    for i, u in enumerate(pics):
        f = os.path.join(tmp, f"{i}.jpg")
        try:
            req = urllib.request.Request(u + "_800x800.jpg", headers={"User-Agent": "Mozilla/5.0"})
            open(f, "wb").write(urllib.request.urlopen(req, timeout=60).read())
            files.append(f)
        except Exception as e:
            print("foto falló:", u, e)
    if not files:
        raise SystemExit("TikTok: no se pudo bajar ninguna foto")
    each = 2.5
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{f}'\nduration {each}\n" for f in files) + f"file '{files[-1]}'\n")
    silent, out = os.path.join(tmp, "v.mp4"), os.path.join(ROOT, "t", f"{name}.mp4")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                        "-vf", "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:white,fps=30,format=yuv420p",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-t", f"{each * len(files):.1f}", silent],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpeg fotos: " + r.stderr[-400:])
    with_music(silent, out, name)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    run = lambda *a: subprocess.run(["git", *a], cwd=ROOT)
    old = sorted((os.path.join(ROOT, "t", f) for f in os.listdir(os.path.join(ROOT, "t")) if f.endswith(".mp4")),
                 key=os.path.getmtime)[:-3]  # keep the repo small: only the last 3
    for f in old:
        run("rm", "-q", "--cached", f)
        os.remove(f)
    run("add", out)
    run("commit", "-qm", f"bot: TikTok fotos con música ({name})")
    run("pull", "-q", "--rebase", "origin", "main")
    run("push", "-q", "origin", "HEAD:main")
    url = f"https://gus1227.github.io/t/{name}.mp4"
    for _ in range(40):  # GitHub Pages needs a minute or two
        try:
            if urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30).status == 200:
                return url
        except Exception:
            pass
        time.sleep(15)
    raise SystemExit("TikTok: el video de fotos no llegó a la web")


def tiktok():
    token = google_token()
    rows = sheets(token, f"values/{TAB}!A1:CZ?valueRenderOption=FORMATTED_VALUE").get("values", [])
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    # Make takes the LAST published row that has not gone to TikTok yet
    want = os.environ.get("FILA_PUB", "").strip()  # "Publicar ahora" from the panel
    pick = [(int(want), rows[int(want) - 1])] if want else \
        [(n, r) for n, r in enumerate(rows[1:], start=2) if g(r, STATE) == "Publicado" and not g(r, TT_DONE)]
    if not pick:
        print("TikTok: no hay relojes nuevos.")
        return
    # the most recently published one (I = Fecha_pub, as a date serial number)
    dates = sheets(token, f"values/{TAB}!I1:I?valueRenderOption=UNFORMATTED_VALUE").get("values", [])
    when = lambda n: (dates[n - 1][0] if n - 1 < len(dates) and dates[n - 1] and isinstance(dates[n - 1][0], (int, float)) else 0)
    n, r = max(pick, key=lambda t: (when(t[0]), t[0]))
    pics = []
    for u in (g(r, IMG) + " " + g(r, EXTRA)).split():
        if u not in pics:
            pics.append(u)
    from fotos import limpias  # only clean photos, no infographics with text
    pics = limpias(pics, g(r, BRAND))[:10]
    from textos import headline, kind, specs, tag
    head, feats = headline(g(r, NAME), g(r, BRAND)), specs(g(r, NAME), 3)
    from textos import tiktok_seo
    words, tags = tiktok_seo(g(r, NAME), g(r, BRAND))  # TikTok search keywords (Cheche)
    desc = (f"{head}\n{' · '.join(feats)}{chr(10) if feats else ''}{g(r, PRICE)}\n{words}\n\n"
            f"👆 Tap the link in our bio to get it · new watches every day\n\n{tags}")
    title = f"{head} · {' · '.join(feats[:2])}" if feats else head
    video = g(r, VIDEO)
    print(f"TikTok fila {n}: {g(r, NAME)}\nfotos: {len(pics)}, video: {'sí' if video else 'no'}\n---\n{desc}\n---")
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    accs = zernio("/accounts")
    accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
    acc = next(a["_id"] for a in accs if str(a.get("platform", "")).lower() == "tiktok")
    if pics:
        # photos as a video with our own music (TikTok's automatic music was Hebrew; without it, no music at all)
        res = zernio("/posts", {"content": desc, "mediaItems": [{"type": "video", "url": slideshow(pics, f"fila{n}")}],
                                "platforms": [{"platform": "tiktok", "accountId": acc}],
                                "tiktokSettings": {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True,
                                                   "allow_duet": False, "allow_stitch": False,
                                                   "content_preview_confirmed": True, "express_consent_given": True},
                                "publishNow": True})
        print("TikTok fotos (video con música):", json.dumps(res)[:300])
    if video and not os.environ.get("SOLO_FOTOS"):  # SOLO_FOTOS=si: re-post only the photo video
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
def pin_of_row(fila):
    """Pin of one watch (by its sheet row): same key as feed.yml (last part of Enlace)."""
    token = google_token()
    link = sheets(token, f"values/{TAB}!E{fila}").get("values", [[""]])[0][0]
    wid = re.sub(r"[^A-Za-z0-9_-]", "", link.rstrip("/").split("/")[-1])
    queue = json.load(open(os.path.join(os.path.dirname(__file__), "..", "pins", "queue.json"), encoding="utf-8"))
    q = next((q for q in queue if q["k"] == wid), None)
    if not q:
        raise SystemExit(f"Pinterest: ese reloj no tiene pin todavía (se crea en la próxima vuelta de feed.yml).")
    return json.loads(q["b"])


def pinterest():
    if os.environ.get("FILA_PUB"):  # "Publicar ahora" of one watch from the panel
        body = pin_of_row(int(os.environ["FILA_PUB"]))
        print("Pinterest (reloj elegido):", body["platforms"][0]["platformSpecificData"]["title"])
        if PUBLISH:
            print("Pinterest:", json.dumps(zernio("/posts", body))[:300])
        return
    # same turn number as Make 7763492: round((unix - 1791128378) / 7200) + 77
    # the bot clock passes the next pin number (PIN); by hand it uses Make's formula
    manual = not os.environ.get("PIN")
    estado = os.path.join(os.path.dirname(__file__), "estado.json")
    n = int(os.environ.get("PIN") or json.load(open(estado))["pin"])
    pins = os.path.join(os.path.dirname(__file__), "..", "pins")
    f = os.path.join(pins, "q", f"{n}.json")
    if not os.path.exists(f):
        if n >= len(json.load(open(os.path.join(pins, "queue.json")))):
            raise SystemExit(f"Pinterest: la cola terminó (pin {n}).")
        print(f"Pinterest: pin {n} apagado, paso al siguiente.")
        return
    body = json.load(open(f, encoding="utf-8"))
    print(f"Pinterest pin {n}: {body['platforms'][0]['platformSpecificData']['title']}")
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    print("Pinterest:", json.dumps(zernio("/posts", body))[:300])
    if manual:  # by hand: move the bot clock to the next pin so it is not posted twice
        import subprocess
        d = os.path.dirname(estado)
        subprocess.run(["git", "pull", "-q", "--rebase", "origin", "main"], cwd=d)
        st = json.load(open(estado))
        st["pin"] = max(st["pin"], n + 1)
        json.dump(st, open(estado, "w"), indent=1)
        subprocess.run(["git", "commit", "-qam", f"bot: pin {n} a mano"], cwd=d)
        subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=d)


if __name__ == "__main__":
    if os.environ.get("ZERNIO_KEY") and not PUBLISH:
        accs = zernio("/accounts")
        accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
        print("Llave OK. Cuentas en Zernio:", [(a.get("platform"), a.get("_id")) for a in accs])
    if "tiktok" in REDES:
        tiktok()
    if "pinterest" in REDES:
        pinterest()
