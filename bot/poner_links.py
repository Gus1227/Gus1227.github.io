# Escribe en AG:AL los links cortos de bot/links_nuevos.json ({"fila": {"columna 0-5": "link"}}).
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from telegram import google_token, sheets, TAB

COLS = "AG AH AI AJ AK AL".split()
new = json.load(open(os.path.join(os.path.dirname(__file__), "links_nuevos.json")))
data = [{"range": f"{TAB}!{COLS[int(k)]}{n}", "values": [[u]]} for n, cols in new.items() for k, u in cols.items()]
if data:
    sheets(google_token(), "values:batchUpdate", {"valueInputOption": "RAW", "data": data}, method="POST")
print(f"Escritos {len(data)} links cortos en {len(new)} filas.")
