# Kabuzio bot: how much material Gus has left, so the automation never runs dry (Cheche, 2026-10-10).
# Counts the watches still waiting for each network, the pins and the Reels Cheche picked (🎬), and finds
# what is missing to keep posting (watches without a photo, picked Reels without a video).
#   every day 06 UTC (09:00 Israel): short summary to Cheche's private Telegram
#   any turn: a warning as soon as something will run out in less than DIAS days or a photo/video is missing
#             (once per problem; it speaks again only when the problem changes)
#   RESERVA=ver  prints the summary;  RESERVA=si  also sends it now
import glob, json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from telegram import IMG, NAME, PRICE, STATE, TAB, VIDEO, google_token, num, sheets

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DIAS = 3  # warn when a network has less than 3 days left
IG_DONE, TT_DONE, FB_DONE, FOTOS_WEB, PID = 16, 17, 20, 29, 23
# posts a day, the same as horario.py
POR_DIA = {"Telegram": 2, "TikTok": 3, "Instagram": 2, "Facebook": 2, "Pinterest": 8, "Reels 🎬": 1}


def contar(st):
    tok = google_token()
    got = sheets(tok, f"values:batchGet?ranges={TAB}!A1:AN&ranges=Revisar!D2:D3000&valueRenderOption=FORMATTED_VALUE")
    rows, rev = (v.get("values", []) for v in got["valueRanges"])
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    filas = list(enumerate(rows[1:], start=2))
    pend = [(n, r) for n, r in filas if g(r, STATE) == "Pendiente"]
    publ = [(n, r) for n, r in filas if g(r, STATE) == "Publicado"]
    hechos = set(st.get("reels", []))
    elegidos = [(n, r) for n, r in filas if any(t.startswith("reel") for t in g(r, FOTOS_WEB).split())
                and g(r, STATE) in ("Publicado", "Pendiente") and g(r, PID).lstrip("'") not in hechos]
    auto = [1 for n, r in publ if num(g(r, PRICE)) >= 60 and g(r, IMG) and g(r, PID).lstrip("'") not in hechos]
    pin = int(st.get("pin", 0))
    pins = sum(1 for f in glob.glob(os.path.join(ROOT, "pins", "q", "*.json"))
               if os.path.basename(f)[:-5].isdigit() and int(os.path.basename(f)[:-5]) >= pin)
    quedan = {"Telegram": len(pend), "Pinterest": pins, "Reels 🎬": len(elegidos)}
    # TikTok, Instagram and Facebook take the published watches they have not had yet; Telegram feeds them 2 a day
    for red, col in (("TikTok", TT_DONE), ("Instagram", IG_DONE), ("Facebook", FB_DONE)):
        quedan[red] = len(pend) + sum(1 for n, r in publ if not g(r, col))
    falta = {
        "sin foto": [n for n, r in pend + elegidos if not g(r, IMG)],
        "sin video": [n for n, r in elegidos if not g(r, VIDEO)],
    }
    return quedan, falta, len([1 for v in rev if v and v[0].strip()]), len(auto)


def problemas(quedan, falta, revisar):
    out = []
    for red, n in quedan.items():
        dias = n / POR_DIA[red]
        if dias < DIAS:
            que = {"Telegram": "Acepta relojes nuevos en la pestaña Revisar de la hoja.",
                   "Reels 🎬": "Marca «🎬 Hacer un Reel» en más relojes del editor (si no, Gus usa el más vendido).",
                   "Pinterest": "Los pines salen de la web: acepta relojes nuevos en Revisar."}.get(red, "Acepta relojes nuevos en la pestaña Revisar.")
            out.append(f"{red}: {'no queda nada' if not n else f'quedan {n} (menos de {DIAS} días)'}. {que}")
    for que, filas in falta.items():
        if filas:
            fs = ", ".join(str(n) for n in sorted(set(filas))[:10])
            out.append(f"{len(set(filas))} {'relojes sin foto' if que == 'sin foto' else 'Reels elegidos sin video'} (fila {fs}). "
                       + ("Ponle una foto en la columna D." if que == "sin foto" else "Saldrá solo con fotos; si quieres video, ponlo en la columna V."))
    if quedan["Telegram"] / POR_DIA["Telegram"] < DIAS and revisar == 0:
        out.append("La pestaña Revisar está vacía: Gus busca más relojes en el próximo turno.")
    return out


def texto(quedan, falta, revisar, auto, titulo):
    lines = [f"📦 <b>Gus</b> · {titulo}"]
    for red, n in quedan.items():
        lines.append(f"{'⚠️' if n / POR_DIA[red] < DIAS else '✅'} {red}: {n} ({n // POR_DIA[red]} días)")
    lines.append(f"🎬 Reels automáticos de reserva: {auto}")
    lines.append(f"👀 Esperando que los aceptes en Revisar: {revisar}")
    pr = problemas(quedan, falta, revisar)
    if pr:
        lines += ["", "<b>Hace falta:</b>"] + [f"• {p}" for p in pr]
    else:
        lines += ["", "Todo bien, no hace falta nada."]
    return "\n".join(lines)


def revisar(st, hour):
    """Called by horario.py every turn with its estado. Sends the daily summary and the warnings."""
    import aviso
    quedan, falta, rev, auto = contar(st)
    pr = problemas(quedan, falta, rev)
    sig = " | ".join(p.split(".")[0] for p in pr)  # what is wrong, without the numbers that change every turn
    sig = "".join(c for c in sig if not c.isdigit())
    if hour == 6:
        aviso.enviar(texto(quedan, falta, rev, auto, "reserva de hoy"))
    elif sig and sig != st.get("reserva_aviso"):
        aviso.enviar(texto(quedan, falta, rev, auto, "⚠️ se acaba el material"))
    elif not sig and st.get("reserva_aviso"):
        aviso.enviar("✅ <b>Gus</b> · la reserva vuelve a estar bien.")
    st["reserva_aviso"] = sig
    print(texto(quedan, falta, rev, auto, "reserva").replace("<b>", "").replace("</b>", ""))


if __name__ == "__main__":
    st = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "estado.json")))
    q, f, rv, au = contar(st)
    msg = texto(q, f, rv, au, "reserva de ahora")
    print(msg.replace("<b>", "").replace("</b>", ""))
    if os.environ.get("RESERVA", "ver") == "si":
        import aviso
        aviso.enviar(msg)
