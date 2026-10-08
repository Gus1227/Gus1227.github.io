# Kabuzio bot: community + sales agent (agents 7 and 11). Answers new comments on our Instagram posts:
#   - a public reply under the comment (never a link: «link in our bio»)
#   - a private message to the person with the link of THAT watch (Instagram private reply, once per comment)
#   - complaints are also written to the «Reportes» tab so Cheche sees them; spam is ignored
# Texts: bot/respuestas.json (same as /mnt/project-files/kabuzio/agentes/respuestas.json). Answered comment ids are
# kept in bot/respondidos.json. RESPONDER=si answers; anything else only prints what it would say.
import datetime, json, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meta import GRAPH, IG, PAGE, graph  # noqa: F401  (GRAPH kept for reference)
from cupones import corto, de

HERE = os.path.dirname(os.path.abspath(__file__))
TEXTS = json.load(open(os.path.join(HERE, "respuestas.json"), encoding="utf-8"))
DONE_FILE = os.path.join(HERE, "respondidos.json")
WRITE = os.environ.get("RESPONDER", "no").lower() in ("si", "sí", "1")
MAX_PER_RUN, DAYS = 15, 7  # Instagram allows a private reply only in the first 7 days
ME = "kabuzio_deal"


def rule(text):
    t = text.lower()
    if any(s in t for s in TEXTS["no_responder"]):
        return None
    for r in TEXTS["reglas"]:
        if any(k in t for k in r["claves"]):
            return r
    return {"id": "otro", **TEXTS["por_defecto"]}


def watch_of(caption, rows):
    """The sheet row of the watch in this post: its headline (AO) and price (B) are in the caption."""
    from telegram import PRICE
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    first = (caption or "").split("\n")[0].strip().lower()
    from textos import headline
    for r in reversed(rows[1:]):
        head = g(r, 40) or headline(g(r, 0), g(r, 12))  # AO, or the same headline meta.py builds when AO is empty
        if head and head.lower() == first and g(r, PRICE) and g(r, PRICE) in (caption or ""):
            return r
    return None


def fill(text, r, g):
    link = TEXTS["linktree"]
    if r is not None:
        link = g(r, 33) or g(r, 4) or link  # AH = Instagram link of the watch, else its main link
    return (text.replace("{link}", link).replace("{web}", TEXTS["web"])
            .replace("$PRICE", g(r, 1) if r is not None else "on the page")
            .replace("BRAND", re.sub(r"([a-z])([A-Z])", r"\1 \2", g(r, 12)) if r is not None and g(r, 12) else "piece"))


def deal(r, g, link):
    """Cheche (2026-10-08): the DM with the watch's link; over caro_desde ($400) it offers cheaper options too."""
    from textos import headline
    num = re.sub(r"[^0-9.]", "", g(r, 1).replace(",", ""))
    try:
        price = float(num)
    except ValueError:
        price = 0
    shown = (f"{price:.0f}" if price == int(price) else f"{price:.2f}") if price else g(r, 1).lstrip("$")
    text = TEXTS["dm_reloj_caro"] if price > TEXTS["caro_desde"] else TEXTS["dm_reloj"]
    name = g(r, 40) or headline(g(r, 0), g(r, 12))
    return text.replace("{nombre}", name).replace("{precio}", shown).replace("{link}", link)


def compose(ru, r, g):
    """Public and private answer; when the watch has a coupon, the private message carries its code."""
    cup = de(r) if r is not None else None
    if ru["id"] == "cupon" and not cup:
        ru = {**ru, "comentario": TEXTS["por_defecto"]["comentario"], "mensaje": [TEXTS["cupon_no_hay"]]}
    elif cup and ru["id"] in ("elogio", "otro"):  # the post asks to comment: any comment gets the code
        ru = TEXTS["reglas"][0]
    public = fill(random.choice(ru["comentario"]), r, g)
    if r is not None and ru["id"] not in ("queja", "recomendar"):  # we know the watch: «Here's your deal» DM
        private = deal(r, g, g(r, 33) or g(r, 4) or TEXTS["linktree"])
    else:
        private = fill(TEXTS["dm_tras_comentario"] if ru["id"] in ("elogio", "otro") else random.choice(ru["mensaje"]), r, g)
    if cup:
        if ru["id"] != "cupon":
            private += TEXTS["cupon_extra"]
        private = private.replace("{code}", cup["codigo"]).replace("{value}", corto(cup["valor"]))
    return ru, public, private


def report(tok, user, text, perma):
    from telegram import sheets
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    sheets(tok, "values/Reportes!A1:I1:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
           {"values": [[now, f"Instagram @{user}", "", "Queja en comentario", text, "", perma, "", "Nuevo"]]}, method="POST")


def main():
    from telegram import TAB, google_token, sheets
    done = json.load(open(DONE_FILE)) if os.path.exists(DONE_FILE) else []
    seen = set(done)
    tok = google_token()
    rows = sheets(tok, f"values/{TAB}!A1:AP?valueRenderOption=FORMATTED_VALUE").get("values", [])
    g = lambda r, i: (r[i] if r is not None and i < len(r) else "").strip()
    page_tok = graph(f"/{PAGE}", {"fields": "access_token"})["access_token"]
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS)
    media = graph(f"/{IG}/media", {"fields": "id,caption,timestamp,permalink", "limit": 25}).get("data", [])
    answered = 0
    for m in media:
        if datetime.datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")) < since:
            continue
        r = watch_of(m.get("caption"), rows)
        comments = graph(f"/{m['id']}/comments", {"fields": "id,text,username,timestamp,replies{username}", "limit": 50}).get("data", [])
        for c in comments:
            if c["id"] in seen or c.get("username") == ME:
                continue
            if any(x.get("username") == ME for x in (c.get("replies") or {}).get("data", [])):
                seen.add(c["id"]); done.append(c["id"])  # already answered (by hand or before)
                continue
            if answered >= MAX_PER_RUN:
                break
            ru = rule(c.get("text", ""))
            if ru is None:
                print(f"spam, no respondo: @{c.get('username')}: {c.get('text', '')[:80]}")
                seen.add(c["id"]); done.append(c["id"])
                continue
            ru, public, private = compose(ru, r, g)
            print(f"@{c.get('username')}: {c.get('text', '')[:80]}\n  [{ru['id']}] público: {public}\n  privado: {private[:120]}")
            if WRITE:
                try:
                    graph(f"/{c['id']}/replies", {"message": public}, post=True)
                except SystemExit as e:
                    print("Respuesta pública falló:", e)
                try:  # Instagram private reply: one message to whoever commented, sent from the page
                    graph(f"/{PAGE}/messages", {"recipient": json.dumps({"comment_id": c["id"]}),
                                                 "message": json.dumps({"text": private})}, post=True, token=page_tok)
                except SystemExit as e:
                    print("Mensaje privado falló:", e)
                if ru.get("avisar"):
                    report(tok, c.get("username"), c.get("text", ""), m.get("permalink", ""))
                seen.add(c["id"]); done.append(c["id"])
            answered += 1
    print("Comentarios respondidos:", answered, "" if WRITE else "(prueba: nada enviado)")
    if WRITE:
        json.dump(done[-3000:], open(DONE_FILE, "w"))


if __name__ == "__main__":
    main()
