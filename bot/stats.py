# Real numbers for the panel: followers per network, read straight from each app.
# Writes stats.json at the site root (public, no secrets), with a small daily history.
import datetime, json, os, sys, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "stats.json")


def get(url, headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=60))


def telegram():
    tok = os.environ["TG_TOKEN"]
    return {"seguidores": get(f"https://api.telegram.org/bot{tok}/getChatMemberCount?chat_id=@KabuzioDeal")["result"]}


def zernio():
    h = {"Authorization": f"Bearer {os.environ['ZERNIO_KEY']}"}
    accs = get("https://zernio.com/api/v1/accounts", h)
    accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
    out = {}
    for a in accs:
        if os.environ.get("DEBUG"):
            print(json.dumps(a)[:1500])
        n = None
        for k in ("followersCount", "followers_count", "followerCount", "followers"):
            v = a.get(k) if k in a else (a.get("metadata") or {}).get(k)
            if isinstance(v, (int, float)):
                n = int(v)
                break
        out[str(a.get("platform", "")).lower()] = {"seguidores": n, "usuario": a.get("username") or a.get("displayName")}
    return out


def main():
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    now = datetime.datetime.now(datetime.timezone.utc)
    st = {"actualizado": now.isoformat(timespec="minutes")}
    try:
        st["telegram"] = telegram()
    except Exception as e:
        print("Telegram:", e)
    try:
        st.update(zernio())
    except Exception as e:
        print("Zernio:", e)
    hist = old.get("historial", {})
    hist[now.strftime("%Y-%m-%d")] = {k: v.get("seguidores") for k, v in st.items() if isinstance(v, dict)}
    st["historial"] = dict(sorted(hist.items())[-90:])
    json.dump(st, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(st, ensure_ascii=False)[:800])


if __name__ == "__main__":
    main()
