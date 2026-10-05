# Kabuzio bot: keeps only clean photos (just the watch), drops AliExpress infographics with text on them
# («PRODUCT PARAMETER», «Case thickness…»). Cheche (2026-10-05): text on the photo takes the beauty away.
# Reads each photo with tesseract OCR: 3+ clear words that are not the brand or dial print = infographic.
# Results are cached in bot/fotos.json (one OCR per photo, ever). Without tesseract it changes nothing.
# If no photo is clean, the first one stays, so a post never goes out without a photo.
import json, os, re, shutil, subprocess, tempfile, urllib.request

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fotos.json")
DIAL = {"design", "chronograph", "automatic", "tachymetre", "tachymeter", "water", "resistant", "japan", "movt", "swiss",
        "quartz", "made", "china", "date", "day", "mechanical", "self", "winding", "diver", "pilot", "gmt", "limited"}
TEXTY = 3
_cache = None


def _load():
    global _cache
    if _cache is None:
        try:
            _cache = json.load(open(CACHE))
        except Exception:
            _cache = {}
    return _cache


def save():
    if _cache is not None:
        json.dump(_cache, open(CACHE, "w"), indent=0, sort_keys=True)


def words(url, brand=""):
    """Clear words printed on the photo (brand and dial print excluded); cached."""
    c = _load()
    if url in c:
        return c[url]
    if not shutil.which("tesseract"):
        return 0
    skip = DIAL | {w.lower() for w in re.findall(r"[A-Za-z]{3,}", re.sub(r"([a-z])([A-Z])", r"\1 \2", brand or ""))}
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
            src = url if url.endswith(".jpg") or url.startswith("file:") else url + "_800x800.jpg"
            req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.aliexpress.com/"})
            f.write(urllib.request.urlopen(req, timeout=40).read())
            f.flush()
            out = subprocess.run(["tesseract", f.name, "-", "--psm", "11", "tsv"], capture_output=True, text=True, timeout=60).stdout
    except Exception as e:
        print("OCR falló:", url, e)
        return 0
    n = 0
    for line in out.splitlines()[1:]:
        p = line.split("\t")
        if len(p) >= 12 and p[10].replace(".", "", 1).lstrip("-").isdigit() and float(p[10]) >= 85:
            w = re.sub(r"[^A-Za-z]", "", p[11]).lower()
            if len(w) >= 3 and w not in skip:
                n += 1
    c[url] = n
    return n


def limpias(urls, brand=""):
    """Same photos, in the same order, without the infographics (the first one stays if all have text)."""
    if not urls:
        return urls
    clean = [u for u in urls if words(u, brand) < TEXTY]
    save()
    print(f"fotos limpias: {len(clean)} de {len(urls)}" + ("" if shutil.which("tesseract") else " (sin OCR)"))
    return clean or urls[:1]


if __name__ == "__main__":
    import sys
    for u in sys.argv[1:]:
        print(words(u), u)
