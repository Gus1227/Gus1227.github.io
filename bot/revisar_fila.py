# Ayuda para revisar una fila de Ofertas: muestra sus links y a dónde lleva cada uno.
import os, sys, urllib.request, re
sys.path.insert(0, os.path.dirname(__file__))
from telegram import google_token, sheets, TAB

n = int(os.environ["FILA"])
token = google_token()
head = sheets(token, f"values/{TAB}!A1:AL1").get("values", [[]])[0]
row = sheets(token, f"values/{TAB}!A{n}:AL{n}?valueRenderOption=FORMULA").get("values", [[]])[0]
for i, h in enumerate(head):
    v = row[i] if i < len(row) else ""
    if i in (0, 1, 4, 7, 23) or i >= 24:
        print(f"{i:2} {h}: {str(v)[:300]}")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None
op = urllib.request.build_opener(NoRedirect)
for i in (4, 32, 33, 34, 35, 36, 37):
    u = str(row[i]) if i < len(row) else ""
    if not u.startswith("http"):
        continue
    hops = []
    for _ in range(4):
        try:
            r = op.open(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20)
            body = r.read(20000).decode("utf-8", "ignore")
            m = re.search(r"(https?://[^\"'\s]*aliexpress[^\"'\s]*item[^\"'\s]*)", body)
            hops.append(f"200 {m.group(1)[:250] if m else ''}")
            break
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location")
            hops.append(f"{e.code} -> {str(loc)[:250]}")
            if not loc:
                break
            u = loc
        except Exception as e:
            hops.append(f"error {e}")
            break
    print(f"\n{head[i]}:\n  " + "\n  ".join(hops))
