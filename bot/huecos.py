# Lista las filas que tienen un link largo (Enlace) en lugar de su link corto por red,
# con el número del reloj, para crear sus links cortos.
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from telegram import google_token, sheets, item_of, TAB

token = google_token()
rows = sheets(token, f"values/{TAB}!A1:AL").get("values", [])[1:]
g = lambda r, i: (r[i] if i < len(r) else "").strip()
out = []
for n, r in enumerate(rows, start=2):
    cols = [k for k in range(6) if "/e/" not in g(r, 32 + k)]
    if not cols or not any(g(r, 32 + k) for k in range(6)):
        continue
    x = g(r, 23)
    it = x if x.isdigit() else item_of(g(r, 4))
    out.append(f"{n}:{it}:{''.join(str(k) for k in cols)}")
print("HUECOS=" + ";".join(out))
