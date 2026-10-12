# Kabuzio bot: trending songs (Cheche, 2026-10-12: "the same generic music every time; use trending music, never Hebrew").
# TikTok: the 100 trending tracks of TikTok's Commercial Music Library (licensed for business accounts), US/UK charts,
#   through Zernio. Instagram: the US/UK top songs (Apple Music charts) searched in Instagram's own music (Audio API),
#   title and artist must match.
# Never the Israeli charts (Hebrew). Only titles/artists in plain English letters. Rotates: a song is not repeated
# until the last USADAS songs have been used (bot/musica_usada.json).
# If anything fails, the callers keep our own music (musica_libre.py), so a post never goes out silent.
#   python3 bot/tendencias.py        prints today's lists (nothing is posted)
import json, os, random, re, sys

sys.path.insert(0, os.path.dirname(__file__))
HERE = os.path.dirname(os.path.abspath(__file__))
USED = os.path.join(HERE, "musica_usada.json")
COUNTRIES = ("US", "GB")
USADAS = 25
# library tracks that do not fit a watch ("quiet luxury"): funny, kids, horror, karaoke…
NO = re.compile(r"comic|karaoke|cute|funny|kids|child|horror|scary|christmas|halloween|cartoon|meme|game|baby|"
                r"strange|silly|anime|countdown|alarm|santa|latin|\(\d{5,}\)", re.I)


def ingles(*texts):
    """Only plain English letters (no Hebrew, Arabic, Cyrillic…) in title and artist."""
    return all(c.isascii() for c in " ".join(t or "" for t in texts) if c.isalpha())


def _used():
    try:
        return json.load(open(USED))
    except Exception:
        return []


def _mark(key):
    used = [k for k in _used() if k != key] + [key]
    json.dump(used[-USADAS:], open(USED, "w"), indent=0)


def _rotate(items, key):
    """Best-ranked song not used lately (a little random inside the top, so every post sounds different)."""
    used = set(_used())
    fresh = [x for x in items if key(x) not in used] or items
    return random.choice(fresh[:8]) if fresh else None


def tiktok_chart(acc):
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
            words = " ".join([str(t.get("name")), str(t.get("artist"))] + [str(x) for x in t.get("genres") or []])
            if sid and sid not in seen and ingles(t.get("name"), t.get("artist")) and not NO.search(words):
                seen.add(sid)
                out.append(t)
    out.sort(key=lambda t: t.get("rank") or 999)
    return out


def tiktok_music(acc):
    """tiktokSettings fields for a trending song, or {} (then our own music inside the video stays)."""
    t = _rotate(tiktok_chart(acc), lambda t: "tt:" + str(t.get("name")).lower())
    if not t:
        return {}
    sid = (t.get("clip") or {}).get("id") or t.get("id")
    _mark("tt:" + str(t.get("name")).lower())
    print(f"Música TikTok (tendencia): {t.get('name')} · {t.get('artist')} ({sid})")
    # our own music is still inside the video: volume 0 so only the trending song is heard
    return {"musicSoundInfo": {"musicSoundId": str(sid), "musicSoundVolume": 100}, "videoOriginalSoundVolume": 0}


_HITS = []


def hits():
    """The most played songs right now in the US and UK (Apple Music charts, free public feed): real global hits."""
    import urllib.request
    if _HITS:
        return _HITS
    seen, out = set(), []
    for cc in ("us", "gb"):
        url = f"https://rss.applemarketingtools.com/api/v2/{cc}/music/most-played/50/songs.json"
        for _ in range(3):
            try:
                feed = json.load(urllib.request.urlopen(url, timeout=60))["feed"]["results"]
                break
            except Exception as e:
                print("Éxitos", cc, e)
                feed = []
        for r in feed:
            k = r["name"].lower()
            if k not in seen and ingles(r["name"], r["artistName"]):
                seen.add(k)
                out.append({"name": r["name"], "artist": r["artistName"]})
    _HITS.extend(out)
    return out


def instagram_audio():
    """audio_configuration (JSON string) with a global hit found in Instagram's music, or "" if none matched."""
    from meta import IG, graph
    try:
        chart = hits()
        if os.environ.get("ZERNIO_KEY"):  # TikTok's trending library songs are often in Instagram's library too
            from zernio import zernio
            accs = zernio("/accounts")
            accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
            acc = next(a["_id"] for a in accs if str(a.get("platform", "")).lower() == "tiktok")
            chart = tiktok_chart(acc) + chart
    except Exception as e:
        print("Música Instagram: sin lista de tendencias:", e)
        return ""
    used = set(_used())
    simple = lambda s: re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
    tries = [t for t in chart if "ig:" + simple(t.get("name")) not in used]
    if not os.environ.get("DEBUG"):
        tries = tries[:30]
        random.shuffle(tries)
    for t in tries[:8 if not os.environ.get("DEBUG") else 40]:
        name, artist = simple(t.get("name")), simple(t.get("artist")).split(" ")[0]
        try:
            res = graph("/ig_audio", {"audio_type": "music", "user_id": IG, "search_query": f"{t.get('name')} {t.get('artist')}"})
        except SystemExit as e:
            print("Audio API:", e)
            return ""
        if os.environ.get("DEBUG"):
            print(f"  buscar «{t.get('name')} {t.get('artist')}» →",
                  [(a.get("title"), a.get("display_artist")) for a in (res.get("audio") or res.get("data") or [])][:5])
        for a in res.get("audio") or res.get("data") or []:
            aid = a.get("audio_id") or a.get("id")
            title, by = a.get("title"), a.get("display_artist") or ""
            if (aid and ingles(title, by) and a.get("duration_in_ms", 30000) >= 15000
                    and simple(title).startswith(name[:20]) and artist in simple(by)):
                _mark("ig:" + name)
                print(f"Música Instagram (tendencia): {title} · {by} ({aid})")
                return json.dumps({"audio_id": aid, "audio_volume": 100, "video_volume": 0})
    print("Música Instagram: ninguna tendencia coincidió; queda nuestra música.")
    return ""


if __name__ == "__main__":
    from zernio import zernio
    accs = zernio("/accounts")
    accs = accs.get("accounts", accs) if isinstance(accs, dict) else accs
    acc = next(a["_id"] for a in accs if str(a.get("platform", "")).lower() == "tiktok")
    chart = tiktok_chart(acc)
    print(f"TikTok: {len(chart)} canciones en tendencia (US/GB, sin hebreo)")
    for t in chart[:25]:
        print(f"  {t.get('rank')}. {t.get('name')} · {t.get('artist')} {t.get('genres')}")
    print("Éxitos US/UK:", ", ".join(f"{h['name']} · {h['artist']}" for h in hits()[:15]))
    if os.environ.get("META_TOKEN"):
        os.environ["DEBUG"] = "1"
        print("Instagram:", instagram_audio() or "nada")
