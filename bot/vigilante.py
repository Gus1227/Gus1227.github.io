# Kabuzio bot watchdog (vigilante.yml, every hour): if bot-horario has not done a turn for more than 5 h,
# Cheche gets one private message and a new bot-horario run is started.
import datetime, json, os, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aviso

STATE = os.path.join(HERE, "estado.json")
st = json.load(open(STATE))
last = datetime.datetime.strptime(st["hecho"], "%Y-%m-%dT%H").replace(tzinfo=datetime.timezone.utc)
hours = (datetime.datetime.now(datetime.timezone.utc) - last).total_seconds() / 3600
print(f"último turno {st['hecho']} UTC, hace {hours:.1f} h")
if hours > 5:
    repo, tok = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if repo and tok:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/bot-horario.yml/dispatches",
                                     json.dumps({"ref": "main"}).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"})
        urllib.request.urlopen(req, timeout=30)
        print("bot-horario relanzado")
    if st.get("aviso_parado") != st["hecho"]:
        aviso.enviar(f"🛑 <b>Gus está parado</b>: no publica desde hace {hours:.0f} h (último turno {st['hecho']} UTC).\n"
                     "Ya intenté arrancarlo otra vez. Si en 2 h no vuelve, avísale a Claude.")
        st["aviso_parado"] = st["hecho"]
        json.dump(st, open(STATE, "w"), indent=1)
        g = lambda *a: subprocess.run(["git", *a], cwd=HERE)
        g("add", STATE); g("commit", "-qm", "bot: aviso de parada"); g("pull", "-q", "--rebase", "origin", "main"); g("push", "-q", "origin", "HEAD:main")
