# Revisa que los links por red (AG:AL) de cada fila lleven al mismo reloj que su product_id (X).
import os, re, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from telegram import google_token, sheets, TAB

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None
op = urllib.request.build_opener(NoRedirect)

def item_of(u):
    try:
        op.open(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20)
    except urllib.error.HTTPError as e:
        m = re.search(r"/item/(\d+)", e.headers.get("Location") or "")
        return m.group(1) if m else "?"
    except Exception:
        return "?"
    return "?"

token = google_token()
rows = sheets(token, f"values/{TAB}!A1:AL").get("values", [])
g = lambda r, i: (r[i] if i < len(r) else "").strip()
jobs = []
for n, r in enumerate(rows[1:], start=2):
    if g(r, 32):
        jobs.append((n, r))
with ThreadPoolExecutor(8) as ex:
    found = list(ex.map(lambda j: item_of(g(j[1], 32)), jobs))
bad = []
for (n, r), it in zip(jobs, found):
    want = g(r, 23)
    if not want:
        m = re.search(r"/item/(\d+)", g(r, 4))
        want = m.group(1) if m else ""
    ok = it == want
    if not ok:
        bad.append(n)
    print(f"{'OK ' if ok else 'MAL'} fila {n:3} {g(r,7):10} X={want or '-':17} AG→{it}")
print(f"\nRevisadas {len(jobs)} filas con Link_TG. Mal: {len(bad)}")
print("FILAS_MAL=" + ",".join(map(str, bad)))
