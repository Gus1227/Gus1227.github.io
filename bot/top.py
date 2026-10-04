# Kabuzio bot: a pinned «Top 3» message in the Telegram channel, refreshed once a day.
# The 3 best sellers among the watches posted in the last 7 days (different brands when possible).
# The same message is edited every day (no new post, no notification); if it is not pinned anymore, a new one is sent
# and pinned silently. TOP=si writes; anything else only prints.
import datetime, html, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
from telegram import (CHAT, IMG, NAME, PRICE, STATE, TAB, google_token, good_link, sheets, tg)

WRITE = os.environ.get("TOP", "no").lower() in ("si", "sí", "1")
HEAD = "🏆 Kabuzio Top 3"
SALES, BRAND = 13, 12  # N = Ventas, M = Marca


def sold(v):
    m = re.search(r"\d[\d,]*(\.\d+)?", str(v or ""))
    return int(float(m.group().replace(",", ""))) if m else 0


def when(v):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(str(v).strip(), fmt)
        except ValueError:
            pass
    return None


def pick(rows):
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    pub = [r for r in rows[1:] if g(r, STATE) == "Publicado" and g(r, IMG)]
    week = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    recent = [r for r in pub if (when(g(r, 8)) or datetime.datetime.min) >= week]
    pool = sorted(recent if len(recent) >= 3 else pub, key=lambda r: -sold(g(r, SALES)))
    top, brands = [], set()
    for r in pool:  # different brands first
        if g(r, BRAND) not in brands or not g(r, BRAND):
            top.append(r)
            brands.add(g(r, BRAND))
        if len(top) == 3:
            break
    for r in pool:
        if len(top) == 3:
            break
        if r not in top:
            top.append(r)
    return top


def caption(top):
    g = lambda r, i: html.escape((r[i] if i < len(r) else "").strip(), quote=False)
    medal = ["🥇", "🥈", "🥉"]
    lines = [f"<b>{HEAD}</b> · the best sellers this week\n"]
    for i, r in enumerate(top):
        n = sold(r[SALES] if SALES < len(r) else "")
        lines.append(f"{medal[i]} <b>{g(r, NAME)[:70]}</b>\n💰 {g(r, PRICE)}{f' · 🔥 {n}+ sold' if n else ''}\n"
                     f"👉 <a href=\"{html.escape(good_link(r))}\">Get it here</a>\n")
    lines.append("🌐 All watches: gus1227.github.io\n#top #watches #Kabuzio")
    return "\n".join(lines)


def main():
    rows = sheets(google_token(), f"values/{TAB}!A1:AL5000").get("values", [])
    top = pick(rows)
    if not top:
        print("Top: no hay relojes publicados.")
        return
    cap, photo = caption(top), top[0][IMG].strip() + "_800x800.jpg"
    print(cap)
    if not WRITE:
        return
    pinned = (tg("getChat", {"chat_id": CHAT}).get("result") or {}).get("pinned_message") or {}
    if (pinned.get("caption") or "").startswith(HEAD):
        res = tg("editMessageMedia", {"chat_id": CHAT, "message_id": pinned["message_id"],
                                      "media": {"type": "photo", "media": photo, "caption": cap, "parse_mode": "HTML"}})
        if res.get("ok") or "not modified" in str(res.get("description", "")):
            print("Top actualizado (mensaje", pinned["message_id"], ")")
            return
        print("No se pudo editar:", res)
    res = tg("sendPhoto", {"chat_id": CHAT, "photo": photo, "caption": cap, "parse_mode": "HTML", "disable_notification": True})
    if not res.get("ok"):
        raise SystemExit(f"Telegram: {res}")
    mid = res["result"]["message_id"]
    tg("pinChatMessage", {"chat_id": CHAT, "message_id": mid, "disable_notification": True})
    print("Top nuevo y fijado:", mid)


if __name__ == "__main__":
    main()
