# Kabuzio bot: trending songs on TikTok (Cheche, 2026-10-12: "always the same generic music; use trending music,
# never Hebrew"). The trending tracks of TikTok's Commercial Music Library (licensed for business accounts) in the
# US and UK charts, through Zernio. Never the Israeli chart (Hebrew); only titles/artists in plain English letters.
# Rotates by the hour: each post takes a different song from the top of the chart.
# Instagram's Audio API has no real hits for our business account (tested 2026-10-12), so Instagram, Facebook,
# Pinterest and Telegram keep our own music (musica_libre.py). If anything fails here, TikTok keeps it too.
#   python3 bot/tendencias.py        prints today's list (nothing is posted)
import os, re, sys, time

sys.path.insert(0, os.path.dirname(__file__))
COUNTRIES = ("US", "GB")
TOP = 30
# library tracks that do not fit a watch ("quiet luxury"): funny, kids, horror, karaoke, Latin (Spanish lyrics)…
NO = re.compile(r"comic|karaoke|cute|funny|kids|child|horror|scary|christmas|halloween|cartoon|meme|game|baby|"
                r"strange|silly|anime|countdown|alarm|santa|holiday|latin|\(\d{5,}\)", re.I)


def ingles(*texts):
    """Only plain English letters (no Hebrew, Arabic, Cyrillic…) in title and artist."""
    return all(c.isascii() for c in " ".join(t or "" for t in texts) if c.isalpha())


def chart(acc):
    from zernio import zernio
    seen, out = set(), []
    for cc in COUNTRIES:
        try:
            res = zernio(f"/accounts/{acc}/tiktok/commercial-music?countryCode={cc}")
        except SystemExit as e:
            print(f"Música TikTok {cc}:", e)
            continue
        for t in res.get("tracks") or res.get("data") or []:
            sid = (t.get("clip") or {}).get("id") or t.get("id")
            name = str(t.get("name")).lower()
            words = " ".join([str(t.get("name")), str(t.get("artist"))] + [str(x) for x in t.get("genres") or []])
            if sid and name not in seen and ingles(t.get("name"), t.get("artist")) and not NO.search(words):
                seen.add(name)
                out.append(t)
    out.sort(key=lambda t: t.get("rank") or 999)
    return out[:TOP]


def tiktok_music(acc, shift=0):
    """tiktokSettings fields with a trending song, or {} (then our own music inside the video is heard)."""
    try:
        songs = chart(acc)
    except Exception as e:
        print("Música TikTok:", e)
        return {}
    if not songs:
        return {}
    t = songs[(int(time.time() // 3600) * 7 + shift) % len(songs)]  # a different song every post, no state needed
    sid = (t.get("clip") or {}).get("id") or t.get("id")
    print(f"Música TikTok (tendencia): {t.get('name')} · {t.get('artist')} ({sid})")
    # our own music stays inside the file as a backup: volume 0 so only the trending song is heard
    return {"musicSoundInfo": {"musicSoundId": str(sid), "musicSoundVolume": 100}, "videoOriginalSoundVolume": 0}


def tiktok_acc():
    from zernio import zernio
    accs = zernio("/accounts")
    accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
    return next(a["_id"] for a in accs if str(a.get("platform", "")).lower() == "tiktok")


if __name__ == "__main__":
    acc = tiktok_acc()
    songs = chart(acc)
    print(f"TikTok: {len(songs)} canciones en tendencia (US/GB, sin hebreo)")
    for t in songs:
        print(f"  {t.get('rank')}. {t.get('name')} · {t.get('artist')} {t.get('genres')}")
    print("Ahora tocaría:", tiktok_music(acc))
