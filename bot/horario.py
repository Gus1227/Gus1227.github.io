# Kabuzio bot clock. GitHub's own cron is late or skips runs, so one run stays awake ~5.5 h,
# posts at every even UTC hour (minute 5) and then starts the next run itself.
# What it already did is kept in bot/estado.json (pushed to the repo), so a second run never posts twice.
#   every 2 h: AliExpress data + Revisar tab; Telegram 2 a day (08, 18 UTC); Pinterest 8 a day; TikTok 3 a day (06, 12, 18 UTC)
#   1 Reel a day (16 UTC) on Instagram, Facebook, TikTok and Pinterest
#   Instagram: 3 Stories a day (10, 14, 20 UTC) and a themed carousel Mon/Wed/Fri/Sun (12 UTC)
#   every turn: bot/reserva.py warns Cheche before the material runs out (summary at 06 UTC)
#   with estado.json "meta": true also Facebook (16, 22 UTC) and Instagram (18, 00 UTC)
import collections, datetime, html, json, os, subprocess, sys, time, traceback, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "estado.json")
UTC = datetime.timezone.utc
LIMIT = time.time() + 5.5 * 3600
FAILS = []  # scripts that crashed this turn: Cheche gets one private message (bot/aviso.py)


def git(*a):
    return subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True)


def load():
    git("pull", "-q", "--rebase", "origin", "main")
    return json.load(open(STATE))


def save(st, msg):
    json.dump(st, open(STATE, "w"), indent=1)
    git("add", *[f for f in (STATE, os.path.join(HERE, "..", "stats.json"), os.path.join(HERE, "..", "catalogo.csv"), os.path.join(HERE, "fotos.json"), os.path.join(HERE, "respondidos.json"), os.path.join(HERE, "cupones.json")) if os.path.exists(f)])
    git("commit", "-qm", msg)
    for _ in range(4):
        if git("push", "-q", "origin", "HEAD:main").returncode == 0:
            return
        git("pull", "-q", "--rebase", "origin", "main")
        time.sleep(5)
    print("No pude guardar estado.json")


def run(script, **env):
    print(f"== {script} {env}", flush=True)
    p = subprocess.Popen([sys.executable, "-u", os.path.join(HERE, script)], env={**os.environ, "PUBLICAR": "si", **env},
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = collections.deque(maxlen=4)
    for line in p.stdout:
        print(line, end="", flush=True)
        if line.strip():
            tail.append(line.strip()[:200])
    if p.wait() != 0:
        FAILS.append((script, " / ".join(tail)))
    return p.returncode == 0


def report(st, key):
    """One private message per problem: when a turn fails, and once more when it works again."""
    import aviso
    names = sorted({s for s, _ in FAILS})
    sig = ",".join(names)
    if sig and sig != st.get("aviso_fallo"):
        lines = "\n".join(f"• <b>{s}</b>: {html.escape(t[-300:])}" for s, t in FAILS)
        aviso.enviar(f"⚠️ <b>Gus</b> · turno {key} UTC: algo falló\n{lines}\n\nEl resto del turno siguió. Avísale a Claude si se repite.")
    elif not sig and st.get("aviso_fallo"):
        aviso.enviar(f"✅ <b>Gus</b> · turno {key} UTC: todo vuelve a funcionar.")
    st["aviso_fallo"] = sig
    FAILS.clear()


def slot_now():
    now = datetime.datetime.now(UTC)
    s = now.replace(hour=now.hour - now.hour % 2, minute=5, second=0, microsecond=0)
    return s if s <= now else s - datetime.timedelta(hours=2)


def turn(slot):
    key = slot.strftime("%Y-%m-%dT%H")
    st = load()
    if st.get("hecho") == key:
        return
    if datetime.datetime.now(UTC) - slot > datetime.timedelta(minutes=100):
        return  # too late for this turn, wait for the next one
    st["hecho"] = key
    save(st, f"bot: turno {key}")  # mark first: a crash never means a double post
    run("ali.py", ALI_HACER="completar links ventas")
    if slot.hour in (8, 18):  # 2 a day (11:00 and 21:00 Israel): the channel is the exclusive club, not a flood
        run("telegram.py")
    run("revisar.py", REVISAR="si")
    run("marcas.py", MARCAS="si")  # new rows take the first word of the title as brand: tidy it before posting
    run("textos.py", TEXTOS="si")  # headline + specs columns that Make uses for Instagram and Facebook
    if slot.hour % 6:  # 8 pins a day (no pin at 00, 06, 12, 18 UTC)
        if run("zernio.py", REDES="pinterest", PIN=str(st["pin"])):
            st["pin"] += 1
    run("stats.py")
    run("respuestas.py", RESPONDER="si")  # answer new Instagram comments (public + private message with the link)
    run("tiktok_respuestas.py", RESPONDER="si")  # and new TikTok comments (public answer, through Zernio)
    run("tiktok_dm.py", RESPONDER="si")  # and TikTok DMs («DM us K1234»): the watch's link in private
    run("fb_respuestas.py", RESPONDER="si")  # and Facebook page comments (public + private message)
    run("catalogo.py")  # the website reads this copy: fast and always fresh
    if slot.hour == 10:  # once a day (13:00 Israel): prices, watches that no longer exist, one «Price drop» post
        run("ali.py", ALI_HACER="revision")
    if slot.hour == 6:  # once a day, after the fresh sales: sort the queue by what sells
        run("rendimiento.py", RENDIMIENTO="si")
    if slot.hour == 16:  # 19:00 in Israel: refresh the pinned Top 3 in Telegram
        run("top.py", TOP="si")
    day = slot.strftime("%Y-%m-%d")
    stories = {10: "dia", 14: "duelo", 20: "top"}  # 13:00, 17:00 and 23:00 Israel
    if slot.hour in stories and st.get("historia") != key:
        st["historia"] = key
        save(st, f"bot: historia {key}")
        if run("historia.py", HISTORIA=stories[slot.hour], HISTORIA_SI="si"):
            run("ig_extra.py", IG_EXTRA="historia:" + stories[slot.hour])
    if slot.hour == 12 and slot.weekday() in (0, 2, 4, 6) and st.get("carrusel_dia") != day:  # Mon, Wed, Fri, Sun 15:00 Israel
        st["carrusel_dia"] = day
        save(st, f"bot: carrusel {day}")
        if run("carrusel.py", CARRUSEL_SI="si"):
            run("ig_extra.py", IG_EXTRA="carrusel")
    if slot.hour == 16 and st.get("reel") != day:  # 1 Reel a day (19:00 Israel): Cheche's 🎬 queue first, else the best seller
        st["reel"] = day
        save(st, f"bot: reel {day}")  # mark first: never two Reels the same day
        last = os.path.join(HERE, "..", "r", "ultimo.json")
        before = os.path.getmtime(last) if os.path.exists(last) else 0
        if run("reel.py", REEL="si", REEL_AUTO="si") and os.path.exists(last) and os.path.getmtime(last) > before:
            run("reel_publicar.py", REDES="instagram,facebook,tiktok,pinterest")
    if st.get("meta"):  # Facebook and Instagram by the Meta API (replaces Make 7725903 and 7728023)
        if slot.hour in (16, 22):  # 17:00 and 23:00 London: Europe evening, Americas afternoon
            run("meta.py", META="facebook")
        if slot.hour in (18, 0):  # 21:00 and 03:00 Israel: Israel evening, Americas evening
            run("meta.py", META="instagram")
    tiktok = slot.hour in (6, 12, 18) and st.get("tiktok") != key
    if tiktok:
        run("zernio.py", REDES="tiktok")
    if slot.hour == 6 and slot.weekday() == 0 and st.get("copia") != day:  # Monday: backup of the sheet to Cheche
        st["copia"] = day
        run("aviso.py", AVISO="copia")
    st = {**load(), "pin": st["pin"], "copia": st.get("copia"), **({"tiktok": key} if tiktok else {})}
    try:  # how much material is left: daily summary at 06 UTC, a warning before anything runs dry (bot/reserva.py)
        import reserva
        reserva.revisar(st, slot.hour)
    except Exception as e:
        FAILS.append(("reserva.py", str(e)[:200]))
    report(st, key)
    save(st, f"bot: turno {key} hecho")


def main():
    sys.path.insert(0, HERE)
    while True:
        try:
            turn(slot_now())
        except Exception:
            FAILS.clear()
            err = traceback.format_exc()
            print(err, flush=True)
            import aviso
            aviso.enviar("⚠️ <b>Gus</b> se cayó en un turno:\n<code>" + html.escape(err[-600:]) + "</code>\nSigo con el próximo turno.")
        nxt = slot_now() + datetime.timedelta(hours=2)
        if nxt.timestamp() > LIMIT:
            break
        print("Espero hasta", nxt, flush=True)
        time.sleep(max(0, nxt.timestamp() - time.time()))
    # hand over to a fresh run (allowed with the workflow's own token)
    repo, tok = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if repo and tok:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/bot-horario.yml/dispatches",
                                     json.dumps({"ref": "main"}).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"})
        urllib.request.urlopen(req, timeout=30)
        print("Siguiente vuelta lanzada.")


if __name__ == "__main__":
    main()
