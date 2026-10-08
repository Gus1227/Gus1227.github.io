# Kabuzio bot: answers TikTok direct messages with the watch's link (Cheche, 2026-10-07), through Zernio.
# Every TikTok caption says «DM us K1234 for the link» (K + last 4 digits of the product id, textos.dm_code).
# TikTok only lets a business REPLY (it can't start a chat), so the person writes first and Gus answers.
# Answered message ids go to bot/respondidos.json (prefixed «ttdm:»). RESPONDER=si answers; anything else only prints.
import json, os, re, sys, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from respuestas import DONE_FILE, WRITE
from zernio import zernio

PID, LINK, LINK_TT = 23, 4, 34
WEB = "https://gus1227.github.io"


def watch_for(text, rows):
    g = lambda r, i: (r[i] if i < len(r) else "").strip().lstrip("'")
    for code in re.findall(r"\d{4}", text or ""):
        for r in reversed(rows[1:]):
            if g(r, PID).endswith(code):
                return r
    return None


def answer(text, rows):
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    r = watch_for(text, rows)
    if r is None:
        return (f"Hi! 👋 Here are all our hand-picked watches: {WEB}\n"
                f"If you saw one in a video, send us its code (like K1234) and we'll send you its direct link.")
    from respuestas import deal
    return deal(r, g, g(r, LINK_TT) or g(r, LINK))


def main():
    from telegram import TAB, google_token, sheets
    done = json.load(open(DONE_FILE)) if os.path.exists(DONE_FILE) else []
    seen = set(done)
    rows = sheets(google_token(), f"values/{TAB}!A1:AL?valueRenderOption=FORMATTED_VALUE").get("values", [])
    accs = zernio("/accounts")
    accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
    acc = next(a["_id"] for a in accs if str(a.get("platform", "")).lower() == "tiktok")
    res = zernio("/inbox/conversations?" + urllib.parse.urlencode({"accountId": acc, "limit": 50}))
    convs = [c for c in res.get("data", []) if str(c.get("platform", "tiktok")).lower() == "tiktok"]
    print(f"TikTok: {len(convs)} chats", json.dumps(res.get("meta", {}))[:300] if os.environ.get("DEBUG") else "")
    sent = 0
    for c in convs:
        msgs = zernio(f"/inbox/conversations/{urllib.parse.quote(str(c['id']))}/messages?"
                      + urllib.parse.urlencode({"accountId": acc, "sortOrder": "desc", "limit": 10})).get("messages", [])
        if not msgs or msgs[0].get("direction") != "incoming":
            continue  # nothing new: we already wrote last
        last = msgs[0]
        key = "ttdm:" + str(last["id"])
        if key in seen:
            continue
        text = " ".join(m.get("message") or "" for m in reversed(msgs) if m.get("direction") == "incoming")[-500:]
        reply = answer(text, rows)
        print(f"@{c.get('participantName')}: {(last.get('message') or '')[:80]}\n  → {reply[:120]}")
        if WRITE:
            try:
                zernio(f"/inbox/conversations/{urllib.parse.quote(str(c['id']))}/messages", {"accountId": acc, "message": reply})
            except SystemExit as e:
                print("DM falló:", e)
                continue
            seen.add(key); done.append(key)
        sent += 1
    print("DMs de TikTok respondidos:", sent, "" if WRITE else "(prueba: nada enviado)")
    if WRITE:
        json.dump(done[-3000:], open(DONE_FILE, "w"))


if __name__ == "__main__":
    main()
