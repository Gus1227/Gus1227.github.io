# Corrige el texto (y el link) de los posts de Telegram ya publicados, usando los datos actuales de la hoja.
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from telegram import google_token, sheets, caption, tg, TAB, CHAT, STATE, DATE, TG_ID

DAY = os.environ.get("DIA", "")
token = google_token()
rows = sheets(token, f"values/{TAB}!A1:AL").get("values", [])
g = lambda r, i: (r[i] if i < len(r) else "").strip()
print("Ejemplos de la columna S:", [g(r, TG_ID) for r in rows[1:12]])
for n, r in enumerate(rows[1:], start=2):
    mid = re.sub(r"\D", "", g(r, TG_ID))
    if g(r, STATE) != "Publicado" or not mid.isdigit() or DAY not in g(r, DATE):
        continue
    res = tg("editMessageCaption", {"chat_id": CHAT, "message_id": int(mid), "caption": caption(r), "parse_mode": "HTML"})
    print(f"fila {n:3} mensaje {mid}: {'corregido' if res.get('ok') else res.get('description')}")
