# Kabuzio bot: answers new comments on our Facebook page (same texts as Instagram, bot/respuestas.json):
#   - a public reply under the comment (no link: the link is already in the post)
#   - a private message with the link of THAT watch (Messenger private reply), if Meta allows it
# Answered comment ids go to bot/respondidos.json too (prefixed «fb:»). RESPONDER=si answers; anything else only prints.
import datetime, json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meta import PAGE, graph
from respuestas import DAYS, DONE_FILE, MAX_PER_RUN, TEXTS, WRITE, compose, report, rule, watch_of


def main():
    from telegram import TAB, google_token, sheets
    done = json.load(open(DONE_FILE)) if os.path.exists(DONE_FILE) else []
    seen = set(done)
    tok = google_token()
    rows = sheets(tok, f"values/{TAB}!A1:AP?valueRenderOption=FORMATTED_VALUE").get("values", [])
    g = lambda r, i: (r[i] if r is not None and i < len(r) else "").strip()
    page_tok = graph(f"/{PAGE}", {"fields": "access_token"})["access_token"]
    since = int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS)).timestamp())
    posts = graph(f"/{PAGE}/published_posts", {"fields": "id,message,permalink_url", "since": since, "limit": 50},
                  token=page_tok).get("data", [])
    for p in posts:
        p["comments"] = graph(f"/{p['id']}/comments", {"fields": "id,message,from,comments.limit(20){from}", "limit": 50},
                              token=page_tok)
    print(f"Facebook: {len(posts)} posts de los últimos {DAYS} días")
    answered = 0
    for p in posts:
        r = watch_of(p.get("message"), rows)
        for c in (p.get("comments") or {}).get("data", []):
            key, who = "fb:" + c["id"], c.get("from") or {}
            if key in seen or who.get("id") == PAGE:
                continue
            if any((x.get("from") or {}).get("id") == PAGE for x in (c.get("comments") or {}).get("data", [])):
                seen.add(key); done.append(key)  # already answered (by hand or before)
                continue
            if answered >= MAX_PER_RUN:
                break
            ru = rule(c.get("message", ""))
            if ru is None:
                print(f"spam, no respondo: {c.get('message', '')[:80]}")
                seen.add(key); done.append(key)
                continue
            if r is None and ru["id"] in ("precio", "marca"):  # unknown watch: no price or brand to give
                ru = next(x for x in TEXTS["reglas"] if x["id"] == "link")
            ru, public, private = compose(ru, r, g)
            public = public.replace("our bio", "the post")
            print(f"{who.get('name', 'alguien')}: {c.get('message', '')[:80]}\n  [{ru['id']}] público: {public}\n  privado: {private[:120]}")
            if WRITE:
                try:
                    graph(f"/{c['id']}/comments", {"message": public}, post=True, token=page_tok)
                except SystemExit as e:
                    print("Respuesta pública falló:", e)
                    continue
                try:
                    graph(f"/{PAGE}/messages", {"recipient": json.dumps({"comment_id": c["id"]}),
                                                 "message": json.dumps({"text": private})}, post=True, token=page_tok)
                except SystemExit as e:
                    print("Mensaje privado falló:", e)
                if ru.get("avisar"):
                    report(tok, who.get("name", "Facebook"), c.get("message", ""), p.get("permalink_url", ""))
                seen.add(key); done.append(key)
            answered += 1
    print("Comentarios de Facebook respondidos:", answered, "" if WRITE else "(prueba: nada enviado)")
    if WRITE:
        json.dump(done[-3000:], open(DONE_FILE, "w"))


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if "pages_read_user_content" not in str(e):
            raise
        print("Facebook: falta el permiso pages_read_user_content en META_TOKEN; no se leen comentarios todavía.")
