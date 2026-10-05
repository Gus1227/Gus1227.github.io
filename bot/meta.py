# Kabuzio bot: Facebook page and Instagram through the Meta Graph API (to replace Make 7725903 and 7728023).
# META_TOKEN is the never-expiring token of the business system user «kabuzio-bot» (GitHub secret).
# Step 1 (now): META=check only reads who the token is and which page / Instagram it can use. Tokens are never printed.
import json, os, urllib.error, urllib.parse, urllib.request

GRAPH = "https://graph.facebook.com/v23.0"


def graph(path, params=None, post=False):
    params = dict(params or {}, access_token=os.environ["META_TOKEN"])
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(GRAPH + path, data if post else None, method="POST" if post else "GET")
    if not post:
        req = urllib.request.Request(GRAPH + path + "?" + data.decode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
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


if __name__ == "__main__":
    {"check": check}[os.environ.get("META", "check")]()
