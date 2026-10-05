# Kabuzio bot: Instagram carousels by theme (4:5, 1080x1350): a cover, 4 watches of one style, a closing slide.
# Themes take turns (Diver, Automatic, Chronograph, Sapphire & 316L, Pilot/Field): 3–4 a week as the content guide says.
# Files go to c/1.jpg … c/6.jpg and c/carrusel.json (caption + image URLs) so the Instagram step only has to post them.
#   CARRUSEL=<theme> picks one (default: the next one after the last made)   CARRUSEL_SI=si commits and pushes
import json, os, random, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(__file__))
from historia import card, info
from reel import SANS, SERIF, get
from telegram import IMG, NAME, PRICE, STATE, TAB, BRAND_M, SALES, google_token, num, sheets

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SIZE = (1080, 1350)
SITE = "https://gus1227.github.io/c/"
THEMES = [  # (key, regex on the title, cover title, cover subtitle, hashtags) — collector language, no diving claims
    ("coveted", r"\bdiv(e|er|ers|ing)\b|200m|300m|20bar|30bar", "The Most Coveted", "The pieces everyone is asking about", "#watchcollector #wristcheck"),
    ("automatic", r"automatic|mechanical|nh3[458]|pt5000|sw200|miyota", "Collector's Picks", "Mechanical character for every day", "#automaticwatch #watchcollector"),
    ("chrono", r"chronograph|vk6[34]", "Worth a Second Look", "Details that reward attention", "#chronograph #wristcheck"),
    ("sapphire", r"sapphire.*316\s?l|316\s?l.*sapphire", "The Essentials", "Sapphire, steel and nothing extra", "#sapphirecrystal #watchcollector"),
    ("classic", r"pilot|aviat|flieger|field|dress", "Quiet Classics", "Clean dials that never date", "#classicwatch #quietluxury"),
]
STATE_FILE = os.path.join(os.path.dirname(__file__), "estado.json")


def main():
    rows = sheets(google_token(), f"values/{TAB}!A1:AM?valueRenderOption=FORMATTED_VALUE").get("values", [])
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    pub = [r for r in rows[1:] if g(r, STATE) == "Publicado" and g(r, IMG) and num(g(r, PRICE)) >= 60]
    st = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
    want = os.environ.get("CARRUSEL", "").strip()
    keys = [t[0] for t in THEMES]
    last = keys.index(st["carrusel"]) if st.get("carrusel") in keys else -1
    order = [t for t in THEMES if t[0] == want] or THEMES[last + 1:] + THEMES
    for key, rx, title, sub, tags in order:
        pool = [r for r in pub if re.search(rx, g(r, NAME).lower())]
        # Cheche's rule (2026-10-03): a multi-watch post is ONE brand; other brands only fill the gaps
        pool.sort(key=lambda r: -num(g(r, SALES)))
        brands = {}
        for r in pool:
            brands.setdefault(g(r, BRAND_M), []).append(r)
        main_brand = max(brands, key=lambda b: len(brands[b])) if brands else ""
        picks = brands.get(main_brand, [])[:4]
        picks += [r for r in pool if r not in picks][:4 - len(picks)]
        if len(picks) >= 4:
            break
    else:
        print("Carrusel: ningún tema tiene 4 relojes.")
        return
    os.makedirs(os.path.join(ROOT, "c"), exist_ok=True)
    gray, files, names = "0xBBBBBB", [], []
    with tempfile.TemporaryDirectory() as d:
        cover = [get(info(r)[3], os.path.join(d, f"c{i}.jpg")) for i, r in enumerate(picks)]
        out = os.path.join(ROOT, "c", "1.jpg")
        card(d, [("K A B U Z I O", SERIF, 30, 90, gray), (title, SERIF, 78, 160, "white"), (sub, SANS, 34, 270, gray),
                 ("Swipe  →", SANS, 34, 1250, gray)], out,
             [(cover[0], 90, 360, 440), (cover[1], 550, 360, 440), (cover[2], 90, 810, 440), (cover[3], 550, 810, 440)], SIZE)
        files.append(out)
        for i, r in enumerate(picks):
            head, spec, price, _ = info(r)
            names.append(f"{i + 1}. {head} · {price}")
            out = os.path.join(ROOT, "c", f"{i + 2}.jpg")
            card(d, [(f"{i + 1} / 4", SANS, 30, 70, gray), (head, SERIF, min(60, int(60 * 30 / max(len(head), 1))), 120, "white"),
                     (spec, SANS, 32, 1090, gray), (f"Now {price}", SERIF, 66, 1160, "white")],
                 out, [(cover[i], 115, 220, 850)], SIZE)
            files.append(out)
        out = os.path.join(ROOT, "c", "6.jpg")
        card(d, [("Which one is yours?", SERIF, 70, 470, "white"), ("Tell us in the comments: 1, 2, 3 or 4", SANS, 36, 590, gray),
                 ("All four are in the link in our bio", SANS, 36, 700, gray), ("Buyer Protection · Worldwide shipping", SANS, 30, 1180, gray)],
             out, [], SIZE)
        files.append(out)
    caption = (f"{title}. {sub}.\n\n" + "\n".join(names) +
               "\n\nWhich one is yours? 1, 2, 3 or 4 👇\n👆 Tap the link in our bio to get it · new watches every day\n"
               f"Ad · affiliate link\n.\n#watchesofinstagram #quietluxury {tags} #kabuzio")
    json.dump({"tema": key, "caption": caption, "images": [SITE + os.path.basename(f) for f in files]},
              open(os.path.join(ROOT, "c", "carrusel.json"), "w"), ensure_ascii=False, indent=1)
    print(f"Carrusel «{title}»:\n{caption}")
    if os.environ.get("CARRUSEL_SI", "no").lower() in ("si", "sí", "1"):
        run = lambda *a: subprocess.run(["git", *a], cwd=ROOT)
        run("pull", "-q", "--rebase", "origin", "main")
        st = json.load(open(STATE_FILE))
        st["carrusel"] = key
        json.dump(st, open(STATE_FILE, "w"), indent=1)
        run("add", STATE_FILE, *files, os.path.join(ROOT, "c", "carrusel.json"))
        run("commit", "-qm", f"bot: carrusel {key}")
        run("push", "-q", "origin", "HEAD:main")


if __name__ == "__main__":
    main()
