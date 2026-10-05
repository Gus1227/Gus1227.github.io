# Kabuzio bot clock. GitHub's own cron is late or skips runs, so one run stays awake ~5.5 h,
# posts at every even UTC hour (minute 5) and then starts the next run itself.
# What it already did is kept in bot/estado.json (pushed to the repo), so a second run never posts twice.
#   every 2 h: AliExpress data + Revisar tab; Telegram 2 a day (08, 18 UTC); Pinterest 8 a day; TikTok 3 a day (06, 12, 18 UTC)
#   1 Reel a day (16 UTC) on Instagram, Facebook, TikTok and Pinterest
#   Instagram: 3 Stories a day (10, 14, 20 UTC) and a themed carousel Mon/Wed/Fri/Sun (12 UTC)
#   with estado.json "meta": true also Facebook (16, 22 UTC) and Instagram (18, 00 UTC)
import datetime, json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "estado.json")
UTC = datetime.timezone.utc
LIMIT = time.time() + 5.5 * 3600


def git(*a):
    return subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True)


def load():
    git("pull", "-q", "--rebase", "origin", "main")
    return json.load(open(STATE))


def save(st, msg):
    json.dump(st, open(STATE, "w"), indent=1)
    git("add", *[f for f in (STATE, os.path.join(HERE, "..", "stats.json"), os.path.join(HERE, "..", "catalogo.csv"), os.path.join(HERE, "fotos.json"), os.path.join(HERE, "respondidos.json")) if os.path.exists(f)])
    git("commit", "-qm", msg)
    for _ in range(4):
        if git("push", "-q", "origin", "HEAD:main").returncode == 0:
            return
        git("pull", "-q", "--rebase", "origin", "main")
        time.sleep(5)
    print("No pude guardar estado.json")


def run(script, **env):
    print(f"== {script} {env}", flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, script)], env={**os.environ, "PUBLICAR": "si", **env})
    return r.returncode == 0


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
    run("catalogo.py")  # the website reads this copy: fast and always fresh
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
    st = {**load(), "pin": st["pin"], **({"tiktok": key} if tiktok else {})}
    save(st, f"bot: turno {key} hecho")


def main():
    while True:
        turn(slot_now())
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
