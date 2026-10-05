# Kabuzio bot: Instagram Stories (1080x1920 JPG), 3 kinds that take turns during the day:
#   dia   «Watch of the day»: one watch, headline, real specs, price, «Link in bio»
#   duelo «This or that?»: two watches of the same style, «Reply 1 or 2» (the API has no poll sticker: replies come as DMs)
#   top   «Most loved this week»: the best seller of the week (Rendimiento / AliExpress orders)
# The API cannot add stickers (link, poll), so the text says what to do. Files go to s/<kind>.jpg (GitHub Pages).
#   HISTORIA=dia|duelo|top (default: all three)   HISTORIA_SI=si also commits and pushes
import os, random, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(__file__))
from reel import H, SANS, SERIF, W, ff, get
from fotos import limpias
from telegram import EXTRA, IMG, NAME, PRICE, STATE, TAB, BRAND_M, SALES, google_token, num, sheets, ventas

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def card(d, lines, out, pics, size=(W, H)):
    """lines: [(text, font, size, y, color)]; pics: [(file, x, y, size)] on black."""
    ins, chain = [], [f"color=black:s={size[0]}x{size[1]}[bg]"]
    last = "[bg]"
    for i, (f, x, y, s) in enumerate(pics):
        ins += ["-i", f]
        chain.append(f"[{i}:v]scale={s}:{s}:force_original_aspect_ratio=decrease,pad={s}:{s}:(ow-iw)/2:(oh-ih)/2:color=white[p{i}]")
        chain.append(f"{last}[p{i}]overlay={x}:{y}[o{i}]")
        last = f"[o{i}]"
    texts = []
    for j, (t, font, size, y, color) in enumerate(lines):
        tf = os.path.join(d, f"t{j}.txt")
        open(tf, "w").write(t)
        texts.append(f"drawtext=fontfile={font}:textfile={tf}:fontsize={size}:fontcolor={color}:x=(w-text_w)/2:y={y}")
    chain.append(f"{last}{','.join(texts)}[v]")
    ff(*ins, "-filter_complex", ";".join(chain), "-map", "[v]", "-frames:v", "1", "-q:v", "3", out)


def short(t, n=24):
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0]


def info(r):
    from textos import headline, specs
    g = lambda i: (r[i] if i < len(r) else "").strip()
    head = headline(g(NAME), g(BRAND_M))[:34]
    return head, " · ".join(specs(g(NAME), 2)), f"${num(g(PRICE)):.2f}", \
        (lambda u: u if u.endswith(".jpg") else u + "_800x800.jpg")(
        limpias(list(dict.fromkeys((g(IMG) + " " + g(EXTRA)).split())), g(BRAND_M))[0])


def main():
    rows = sheets(google_token(), f"values/{TAB}!A1:AM?valueRenderOption=FORMATTED_VALUE").get("values", [])
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    pub = [r for r in rows[1:] if g(r, STATE) == "Publicado" and g(r, IMG) and num(g(r, PRICE)) >= 60]
    if len(pub) < 2:
        print("Historias: faltan relojes publicados.")
        return
    kinds = (os.environ.get("HISTORIA") or "dia duelo top").split()
    os.makedirs(os.path.join(ROOT, "s"), exist_ok=True)
    gray, made = "0xBBBBBB", []
    with tempfile.TemporaryDirectory() as d:
        for kind in kinds:
            out = os.path.join(ROOT, "s", f"{kind}.jpg")
            if kind == "dia":
                head, spec, price, pic = info(random.choice(pub[-20:]))  # one of the newest
                card(d, [("WATCH OF THE DAY", SANS, 34, 150, gray), (head, SERIF, 62, 220, "white"),
                         (spec, SANS, 34, 1420, gray), (f"Now {price}", SERIF, 76, 1500, "white"),
                         ("Link in bio", SANS, 40, 1640, gray)], out, [(get(pic, os.path.join(d, "a.jpg")), 90, 360, 900)])
            elif kind == "duelo":
                by = {}
                for r in pub:  # two different brands, same family of style when possible
                    by.setdefault(g(r, BRAND_M), r)
                a, b = random.sample(list(by.values()) if len(by) >= 2 else pub, 2)
                (ha, _, pa, ia), (hb, _, pb, ib) = info(a), info(b)
                card(d, [("THIS OR THAT?", SERIF, 66, 200, "white"), ("Reply 1 or 2", SANS, 38, 300, gray),
                         ("1", SERIF, 60, 520, "white"), (f"{short(ha)}  ·  {pa}", SANS, 30, 1015, gray),
                         ("2", SERIF, 60, 1110, "white"), (f"{short(hb)}  ·  {pb}", SANS, 30, 1605, gray),
                         ("Link in bio", SANS, 36, 1720, gray)],
                     out, [(get(ia, os.path.join(d, "a.jpg")), 290, 590, 420), (get(ib, os.path.join(d, "b.jpg")), 290, 1180, 420)])
            elif kind == "top":
                best = max(pub, key=lambda r: ventas(g(r, SALES)))
                head, spec, price, pic = info(best)
                card(d, [("MOST LOVED", SANS, 34, 150, gray), (head, SERIF, 62, 220, "white"),
                         (f"{int(ventas(g(best, SALES))):,}+ orders · Buyer Protection", SANS, 34, 1420, gray),
                         (f"Now {price}", SERIF, 76, 1500, "white"), ("Link in bio", SANS, 40, 1640, gray)],
                     out, [(get(pic, os.path.join(d, "a.jpg")), 90, 360, 900)])
            else:
                continue
            made.append(out)
            print("Historia:", kind, "→ https://gus1227.github.io/s/" + kind + ".jpg")
    if made and os.environ.get("HISTORIA_SI", "no").lower() in ("si", "sí", "1"):
        run = lambda *a: subprocess.run(["git", *a], cwd=ROOT)
        run("add", *made)
        run("commit", "-qm", "bot: historias")
        run("pull", "-q", "--rebase", "origin", "main")
        run("push", "-q", "origin", "HEAD:main")


if __name__ == "__main__":
    main()
