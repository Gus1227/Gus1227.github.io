# Kabuzio bot: answers new comments on our TikTok posts through Zernio (same texts as Instagram, bot/respuestas.json).
# TikTok has no private reply, so only the public answer under the comment («link in our bio», never a link).
# Answered comment ids go to bot/respondidos.json too (prefixed «tt:»). RESPONDER=si answers; anything else only prints.
import datetime, json, os, random, sys, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from respuestas import DONE_FILE, MAX_PER_RUN, TEXTS, WRITE, fill, rule
from zernio import zernio

DAYS = 14


def watch_of(content, rows):
    """Sheet row of the watch in this TikTok: the caption starts with its headline (zernio.py and reel_publicar.py)."""
    from textos import headline
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    from telegram import PRICE
    text = " ".join((content or "").split()).lower()  # TikTok gives the caption back without line breaks
    best = None
    for r in reversed(rows[1:]):
        head = (g(r, 40) or headline(g(r, 0), g(r, 12))).lower()
        if head and text.startswith(head) and (not g(r, PRICE) or g(r, PRICE).lower() in text):
            if best is None or len(head) > len(best[0]):
                best = (head, r)
    if best:
        return best[1]
    return None


def main():
    from telegram import TAB, google_token, sheets
    done = json.load(open(DONE_FILE)) if os.path.exists(DONE_FILE) else []
    seen = set(done)
    rows = sheets(google_token(), f"values/{TAB}!A1:AP?valueRenderOption=FORMATTED_VALUE").get("values", [])
    g = lambda r, i: (r[i] if r is not None and i < len(r) else "").strip()
    accs = zernio("/accounts")
    accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
    acc = next(a["_id"] for a in accs if str(a.get("platform", "")).lower() == "tiktok")
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    q = urllib.parse.urlencode({"platform": "tiktok", "accountId": acc, "minComments": 1, "since": since, "limit": 50})
    posts = zernio(f"/inbox/comments?{q}").get("data", [])
    print(f"TikTok: {len(posts)} videos con comentarios")
    answered = 0
    for p in posts:
        r = watch_of(p.get("content"), rows)
        res = zernio(f"/inbox/comments/{p['id']}?accountId={acc}&limit=50")
        comments = res.get("data") or res.get("comments") or []
        if os.environ.get("DEBUG"):
            print("post:", json.dumps(p)[:300], "\nrespuesta:", json.dumps(res)[:900])
        for c in comments:
            key = "tt:" + str(c["id"])
            who = (c.get("from") or {})
            if key in seen or who.get("isOwner"):
                continue
            if any((x.get("from") or {}).get("isOwner") for x in c.get("replies") or []):
                seen.add(key); done.append(key)  # already answered (by hand or before)
                continue
            if answered >= MAX_PER_RUN:
                break
            ru = rule(c.get("message", ""))
            if ru is None or not c.get("canReply", True):
                print(f"no respondo: @{who.get('username')}: {c.get('message', '')[:80]}")
                seen.add(key); done.append(key)
                continue
            if r is None and ru["id"] in ("precio", "marca"):  # unknown watch: no price or brand to give
                ru = next(x for x in TEXTS["reglas"] if x["id"] == "link")
            public = fill(random.choice(ru["comentario"]), r, g)
            print(f"@{who.get('username')}: {c.get('message', '')[:80]}\n  [{ru['id']}] público: {public}")
            if WRITE:
                try:
                    zernio(f"/inbox/comments/{p['id']}", {"accountId": acc, "message": public, "commentId": c["id"]})
                except SystemExit as e:
                    print("Respuesta falló:", e)
                    continue
                seen.add(key); done.append(key)
            answered += 1
    print("Comentarios de TikTok respondidos:", answered, "" if WRITE else "(prueba: nada enviado)")
    if WRITE:
        json.dump(done[-3000:], open(DONE_FILE, "w"))


if __name__ == "__main__":
    main()
