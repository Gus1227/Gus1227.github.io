# One-off: make sure Ofertas has columns up to AN (Prioridad, Especificaciones).
# MARCAR=<fila> also marks that row as published at 2026-10-04 23:05 (the 20:05 UTC turn sent it but could not mark it).
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from telegram import google_token, sheets, TAB

tok = google_token()
meta = sheets(tok, "?fields=sheets.properties")
p = next(s["properties"] for s in meta["sheets"] if s["properties"]["title"] == TAB)
cols = p["gridProperties"]["columnCount"]
print("columnas:", cols)
if cols < 40:
    sheets(tok, ":batchUpdate", {"requests": [{"appendDimension": {"sheetId": p["sheetId"], "dimension": "COLUMNS", "length": 40 - cols}}]}, method="POST")
    print("añadidas", 40 - cols)
sheets(tok, "values:batchUpdate", {"valueInputOption": "USER_ENTERED", "data": [
    {"range": f"{TAB}!AM1:AN1", "values": [["Prioridad", "Especificaciones"]]}]}, method="POST")
f = os.environ.get("MARCAR")
if f:
    sheets(tok, "values:batchUpdate", {"valueInputOption": "USER_ENTERED", "data": [
        {"range": f"{TAB}!H{f}:I{f}", "values": [["Publicado", "2026-10-04 23:05:00"]]}]}, method="POST")
    print("fila", f, "marcada")
