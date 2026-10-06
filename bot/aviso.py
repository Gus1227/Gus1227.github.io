# Kabuzio bot: private messages from Gus to Cheche through @Kabuzio_Deal_Bot (errors, sales, the weekly backup).
# Cheche's private chat id lives in estado.json "aviso_chat" (Cheche writes «gus aviso» to the bot once).
#   AVISO=buscar  shows who wrote «gus aviso» to the bot (to fill aviso_chat)
#   AVISO=prueba  sends a test message
#   AVISO=copia   sends the backup of the sheet now
import datetime, json, os, sys, urllib.parse, urllib.request, uuid

sys.path.insert(0, os.path.dirname(__file__))
from telegram import SHEET, google_token, sheets, tg

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estado.json")


def chat():
    return os.environ.get("TG_AVISO") or json.load(open(STATE)).get("aviso_chat")


def enviar(texto):
    """Private message to Cheche. Never breaks the caller: an alert must not stop a turn."""
    try:
        to = chat()
        if not to:
            print("aviso (sin chat):", texto)
            return False
        res = tg("sendMessage", {"chat_id": to, "text": texto[:4000], "parse_mode": "HTML", "disable_web_page_preview": True})
        if not res.get("ok"):
            print("aviso falló:", res.get("description"))
        return bool(res.get("ok"))
    except Exception as e:
        print("aviso falló:", e)
        return False


def documento(nombre, datos, texto):
    to = chat()
    if not to:
        print("aviso (sin chat): copia no enviada")
        return False
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{to}\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{texto}\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{nombre}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + datos + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/sendDocument", body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    res = json.load(urllib.request.urlopen(req, timeout=120))
    print("copia enviada" if res.get("ok") else f"copia falló: {res}")
    return bool(res.get("ok"))


def copia():
    """Backup of the whole sheet: the .xlsx (with formulas) and, if that fails, every tab as JSON with formulas."""
    day = datetime.date.today().isoformat()
    try:
        tok = google_token("https://www.googleapis.com/auth/drive.readonly")
        req = urllib.request.Request(f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=xlsx",
                                     headers={"Authorization": f"Bearer {tok}"})
        datos = urllib.request.urlopen(req, timeout=120).read()
        if datos[:2] != b"PK":
            raise ValueError("no es un xlsx")
        return documento(f"Kabuzio_Database_{day}.xlsx", datos, f"🗂 Copia semanal de la hoja ({day}). Guárdala por si acaso.")
    except Exception as e:
        print("xlsx no se pudo, hago JSON:", e)
    tok = google_token()
    tabs = [s["properties"]["title"] for s in sheets(tok, "?fields=sheets.properties")["sheets"]]
    data = {}
    for t in tabs:
        data[t] = sheets(tok, "values/" + urllib.parse.quote(t) + "?valueRenderOption=FORMULA").get("values", [])
    datos = json.dumps(data, ensure_ascii=False).encode()
    return documento(f"Kabuzio_Database_{day}.json", datos, f"🗂 Copia semanal de la hoja ({day}). Guárdala por si acaso.")


def buscar():
    res = tg("getUpdates", {"limit": 100})
    for u in res.get("result", []):
        m = u.get("message") or {}
        c = m.get("chat") or {}
        if c.get("type") == "private" and "gus aviso" in (m.get("text") or "").lower():
            print("chat:", c.get("id"), c.get("first_name"), c.get("username"), m.get("date"))
    print("fin" if res.get("ok") else res)


if __name__ == "__main__":
    hacer = os.environ.get("AVISO", "buscar")
    if hacer == "buscar":
        buscar()
    elif hacer == "prueba":
        print(enviar("✅ Hola Cheche, soy Gus. Desde ahora te aviso aquí si algo falla, cuando entra una venta y cada lunes con la copia de la hoja."))
    elif hacer == "copia":
        if not copia():
            raise SystemExit("la copia de la hoja no se pudo enviar")
