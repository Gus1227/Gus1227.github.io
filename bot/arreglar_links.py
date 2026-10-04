# Pone a cada fila sus links por red correctos (AG:AL).
# Los links ya creados se reparten según el reloj que abren de verdad;
# si un reloj no tiene link propio en una red, se usa su Enlace (E).
import os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from telegram import google_token, sheets, item_of, TAB

WRITE = os.environ.get("ARREGLAR", "no") == "si"
token = google_token()
rows = sheets(token, f"values/{TAB}!A1:AL").get("values", [])[1:]
g = lambda r, i: (r[i] if i < len(r) else "").strip()

urls = set()
for r in rows:
    urls.add(g(r, 4))
    urls.update(g(r, c) for c in range(32, 38))
urls.discard("")
with ThreadPoolExecutor(12) as ex:
    item = dict(zip(urls, ex.map(item_of, urls)))

by_item = [{} for _ in range(6)]  # per column: item -> link
for r in rows:
    for k in range(6):
        u = g(r, 32 + k)
        if u and item.get(u):
            by_item[k].setdefault(item[u], u)

data, ok, fixed, fallback, skipped = [], 0, 0, 0, 0
for n, r in enumerate(rows, start=2):
    e = g(r, 4)
    if not any(g(r, 32 + k) for k in range(6)):
        continue
    want = item.get(e, "")
    new = []
    for k in range(6):
        u = by_item[k].get(want) if want else None
        if not u:
            u = e
            fallback += 1
        new.append(u)
    old = [g(r, 32 + k) for k in range(6)]
    if new == old:
        ok += 1
        continue
    fixed += 1
    data.append({"range": f"{TAB}!AG{n}:AL{n}", "values": [new]})
    print(f"fila {n:3} reloj {want or '?':17} {'arreglada' if want else 'sin número: uso Enlace'}")

print(f"\nYa bien: {ok}. Para arreglar: {fixed}. Huecos que usan Enlace: {fallback}.")
if WRITE and data:
    sheets(token, "values:batchUpdate", {"valueInputOption": "RAW", "data": data}, method="POST")
    print("Hoja actualizada.")
elif data:
    print("Modo prueba: no se cambió la hoja.")
