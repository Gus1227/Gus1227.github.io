# Kabuzio bot: media agent. Builds a vertical Reel (1080x1920, ~15 s) for one watch with ffmpeg:
# the AliExpress video first (if any), then the photos with a slow zoom on black, and quiet text:
# KABUZIO on top, the clean headline and real specs, the price and «Link in bio» at the bottom.
# The file goes to r/<product id>.mp4 in this repo, so GitHub Pages serves it to Instagram, Facebook and TikTok.
#   REEL_FILA=<row>  that row;  empty = the next watch Cheche ticked «🎬 Reel» in the editor (once per watch)
#   REEL=si          also commit and push the file
#   REEL_AUTO=si     if no watch is ticked 🎬, the best seller without a Reel (the daily automatic Reel)
import json, os, re, subprocess, sys, tempfile, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from telegram import EXTRA, IMG, NAME, PRICE, PRIO, SALES, STATE, TAB, VIDEO, BRAND_M, google_token, num, sheets

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estado.json")
W, H, FPS = 1080, 1920, 30
PHOTO_S, VIDEO_S, MAX_PHOTOS, KEEP, FADE = 3.6, 5, 4, 30, 0.7
MAX_OWN, FOTOS_WEB = 6, 29  # AD = Fotos_web: photo order from the editor, «reel» = Cheche picked it
FX = ["fade", "smoothleft", "fadeblack", "smoothup"]  # quiet transitions, they take turns
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
# Hook + answer (Cheche, 2026-10-05): the first 2 seconds promise a detail, the next seconds show it, so nobody is
# left waiting. Each pair is used only when the watch's title really has that detail (no invented specs).
# (regex on the title or None, hook, answer). They take turns, detail pairs first.
HOOKS = [(r"moon.?phase|\bmoon\b", "Nobody talks about\nthis detail.", "A moonphase dial.\nIt follows the moon."),
         (r"tourbillon", "Watch the heart\nof this piece.", "A tourbillon,\nturning in plain sight."),
         (r"skeleton", "See right\nthrough it.", "A skeleton dial:\nthe movement on show."),
         (r"meteorite", "This dial came\nfrom space.", "A real\nmeteorite dial."),
         (r"\bgmt\b|nh34", "One watch.\nTwo time zones.", "A GMT hand\nfor the traveller."),
         (r"chronograph", "Look at\nthe subdials.", "A working chronograph:\nstart, stop, reset."),
         (r"sapphire|saphire", "Look closer\nat the glass.", "Sapphire crystal.\nBuilt to resist scratches."),
         (r"automatic|self.?wind|mechanical|nh3[458]|pt5000", "This watch has\nno battery.", "Automatic movement:\npowered by your wrist."),
         (r"titanium", "Lighter than\nit looks.", "Titanium case:\nstrong and light."),
         (r"ceramic", "Look at\nthe bezel.", "Ceramic bezel:\nit keeps its shine."),
         (r"bgw.?9|c3 |super.?lum|luminous", "Wait until\nthe lights go off.", "Luminous hands:\nreadable in the dark."),
         (r"316\s?l", "Made to\nlast.", "316L stainless steel,\nthe same as fine watches."),
         (None, "Your next watch\nis right here.", ""),
         (None, "Stop scrolling.\nLook at this dial.", ""),
         (None, "Just found this piece.\nHad to show you.", "")]
HOOK_S, ANSWER_S = 2.0, 4.6  # hook until 2.0 s, its answer until 4.6 s, then name and price


def hook_for(name, k, sales=0):
    """(hook, answer) number k among the pairs that fit this watch (k = how many Reels were made before)."""
    t = " " + name.lower() + " "
    ok = [(h, a) for need, h, a in HOOKS if need and re.search(need, t)]
    if sales >= 1000:  # value without talking about price: how many people already bought it
        ok.append(("You didn't know\nabout this one.", f"{int(sales):,}+ people\nalready wear it."))
    ok = ok or [(h, a) for need, h, a in HOOKS if not need]
    return ok[k % len(ok)]


def ff(*a):
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpeg: " + r.stderr[-600:])


def get(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.aliexpress.com/"})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


def photo_clip(src, out, i):
    frames = int(PHOTO_S * FPS)
    zoom = "zoom+0.0007" if i % 2 == 0 else "if(eq(on,0),1.12,zoom-0.0007)"  # in, out, in...
    ff("-loop", "1", "-i", src, "-t", str(PHOTO_S), "-vf",
       f"scale=2000:2000:force_original_aspect_ratio=decrease,pad=2000:2000:(ow-iw)/2:(oh-ih)/2:color=black,"
       f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1000x1000:fps={FPS},"
       f"pad={W}:{H}:40:(oh-ih)/2-60:color=black,format=yuv420p,setsar=1",
       "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out)


def video_clip(src, out):
    ff("-i", src, "-t", str(VIDEO_S), "-an", "-vf",
       f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2-60:color=black,"
       f"fps={FPS},format=yuv420p,setsar=1", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out)


def text_layer(d, head, spec, price, hook=("", "")):
    hook, answer = hook
    files = {}
    for k, v in {"brand": "K A B U Z I O", "head": head, "spec": spec, "price": price, "cta": "Link in bio"}.items():
        files[k] = os.path.join(d, k + ".txt")
        open(files[k], "w").write(v)
    end = (ANSWER_S if answer else HOOK_S) if hook else 0
    t = lambda k, font, size, y, color="white": (
        f"drawtext=fontfile={font}:textfile={files[k]}:fontsize={size}:fontcolor={color}:x=(w-text_w)/2:y={y}"
        ":shadowcolor=black@0.8:shadowx=2:shadowy=2" + (f":enable='gte(t,{end})'" if end else ""))  # after the hook

    def card(name, text, t0, t1, dim):
        """Two centered lines of the same size in the black band above the photo (the watch stays clean), soft fade."""
        lines = text.split("\n")
        fs = min(68, int(960 / (0.62 * max(map(len, lines)))))  # always fits the width
        lh, mid = int(fs * 1.45), ((H - 1000) // 2 - 60) // 2 + 10  # line height; middle of the band above the photo
        top = mid - lh * len(lines) // 2
        on = f"between(t,{t0},{t1})"
        fade = f"if(lt(t,{t0 + 0.25}),(t-{t0})/0.25,if(gt(t,{t1 - 0.3}),({t1}-t)/0.3,1))"
        out = []
        for i, line in enumerate(lines):
            f = os.path.join(d, f"{name}{i}.txt")
            open(f, "w").write(line)
            out.append(f"drawtext=fontfile={SERIF}:textfile={f}:fontsize={fs}:fontcolor=white:alpha='{fade}'"
                       f":x=(w-text_w)/2:y={top + i * lh + (lh - fs) // 2}:shadowcolor=black@0.6:shadowx=2:shadowy=2:enable='{on}'")
        return out

    hooks = (card("hook", hook, 0, HOOK_S, 0.6) + (card("ans", answer, HOOK_S, ANSWER_S, 0.45) if answer else [])) if hook else []
    return ",".join(hooks + [t("brand", SERIF, 34, 120, "0xBBBBBB"), t("head", SERIF, min(58, int(58 * 30 / max(len(head), 1))), 200), t("spec", SANS, 32, 290, "0xCCCCCC"),
                     t("price", SERIF, 72, H - 330), t("cta", SANS, 36, H - 225, "0xCCCCCC")])


def media(r):
    """[(«photo»|«video», url)] for the Reel. If Cheche ordered the photos in the editor (Fotos_web, AD), exactly
    that order and only those; otherwise the clean photos (no text on them) with the video second."""
    g = lambda i: (r[i] if i < len(r) else "").strip()
    pics = list(dict.fromkeys((g(IMG) + " " + g(EXTRA)).split()))
    own = [t for t in g(FOTOS_WEB).split() if not t.startswith("reel")]
    if any("://" in t for t in own):
        seq = [("video", g(VIDEO)) if t == "video" else ("photo", t) for t in own if t != "video" or g(VIDEO)]
        return seq[:MAX_OWN]
    from fotos import limpias  # only clean photos, no infographics with text
    pics = limpias(pics, g(BRAND_M))[:MAX_PHOTOS]
    seq = [("photo", u) for u in pics]
    if g(VIDEO):
        seq.insert(1, ("video", g(VIDEO)))
    return seq


def build(r, out, k=0):
    from textos import headline, specs
    g = lambda i: (r[i] if i < len(r) else "").strip()
    seq = media(r)
    head = headline(g(NAME), g(BRAND_M))[:34]
    spec = ""
    for f in specs(g(NAME), 3):  # whole specs only, never cut in the middle
        if len(spec) + len(f) + 3 <= 52:
            spec = f"{spec} · {f}" if spec else f
    price = f"Now ${num(g(PRICE)):.2f}" if num(g(PRICE)) else g(PRICE)
    with tempfile.TemporaryDirectory() as d:
        clips = []
        for i, (kind, u) in enumerate(seq):  # in Cheche's order (editor) or: 1st photo, video, other photos
            out_i = os.path.join(d, f"c{i}.mp4")
            try:
                if kind == "video":
                    video_clip(get(u, os.path.join(d, f"v{i}.mp4")), out_i)
                else:
                    photo_clip(get(u if u.endswith(".jpg") else u + "_800x800.jpg", os.path.join(d, f"p{i}.jpg")), out_i, i)
                clips.append(out_i)
            except Exception as e:  # a broken photo or video never stops the Reel
                print("Parte descartada:", u, e)
        if not clips:
            raise SystemExit("Reel: sin fotos ni video")
        durs = [float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", c],
                                     capture_output=True, text=True).stdout.strip() or PHOTO_S) for c in clips]
        # soft crossfade between every two parts
        chain, last, t = [], "[0:v]", 0.0
        for i in range(1, len(clips)):
            t += durs[i - 1] - FADE
            chain.append(f"{last}[{i}:v]xfade=transition={FX[i % len(FX)]}:duration={FADE}:offset={t:.2f}[x{i}]")
            last = f"[x{i}]"
        hook = hook_for(g(NAME), k, num(g(SALES)) / (100 if g(SALES).endswith("%") else 1))  # «66200%» = 662 (cell format)
        chain.append(f"{last}{text_layer(d, head, spec, price, hook)}[v]")
        ins = [a for c in clips for a in ("-i", c)]
        ff(*ins, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", ";".join(chain),
           "-map", "[v]", "-map", f"{len(clips)}:a", "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out)
    print(f"Reel listo: {out} ({len(clips)} partes) · gancho: {hook!r} · {head} · {spec} · {price}")


def main():
    want = os.environ.get("REEL_FILA", "").strip()
    rows = sheets(google_token(), f"values/{TAB}!A1:AN?valueRenderOption=FORMATTED_VALUE").get("values", [])
    st = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
    if want:
        n = int(want)
    else:  # the next watch Cheche ticked «🎬 Reel» in the editor that has no Reel yet
        g = lambda r, i: (r[i] if i < len(r) else "").strip()
        def pos(r):  # «reel:3» = number 3 in Cheche's Reel queue (editor → 🎬 Reels)
            m = next((re.match(r"reel(?::(\d+))?$", t) for t in g(r, FOTOS_WEB).split() if t.startswith("reel")), None)
            return (int(m.group(1)) if m.group(1) else 9999) if m else 0
        picked = sorted((pos(r), n) for n, r in enumerate(rows[1:], start=2) if pos(r)
                        and g(r, STATE) in ("Publicado", "Pendiente") and g(r, 23).lstrip("'") not in st.get("reels", []))
        if not picked and os.environ.get("REEL_AUTO", "no").lower() in ("si", "sí", "1"):
            # the daily Reel with no 🎬 left: the best seller (AliExpress orders) that has no Reel yet
            sold = lambda r: num(g(r, SALES)) / (100 if g(r, SALES).endswith("%") else 1)
            picked = sorted((-sold(r), n) for n, r in enumerate(rows[1:], start=2)
                            if g(r, STATE) == "Publicado" and num(g(r, PRICE)) >= 60 and g(r, IMG)
                            and g(r, 23).lstrip("'") not in st.get("reels", []))
        if not picked:
            print("Reel: no hay relojes elegidos para Reel (🎬 en el editor).")
            return
        n = picked[0][1]
    r = rows[n - 1]
    pid = (r[23] if len(r) > 23 else "").strip().lstrip("'") or f"fila{n}"
    os.makedirs(os.path.join(ROOT, "r"), exist_ok=True)
    out = os.path.join(ROOT, "r", f"{pid}.mp4")
    build(r, out, len(st.get("reels", [])))
    print("URL: https://gus1227.github.io/r/" + pid + ".mp4")
    last = os.path.join(ROOT, "r", "ultimo.json")  # what reel_publicar.py and the Instagram step post: the newest Reel
    json.dump({"fila": n, "pid": pid, "url": f"https://gus1227.github.io/r/{pid}.mp4"}, open(last, "w"))
    if os.environ.get("REEL", "no").lower() in ("si", "sí", "1"):
        run = lambda *a: subprocess.run(["git", *a], cwd=ROOT)
        keep = sorted((os.path.join(ROOT, "r", f) for f in os.listdir(os.path.join(ROOT, "r"))), key=os.path.getmtime)
        keep = [f for f in keep if f.endswith(".mp4")]
        for f in keep[:-KEEP]:  # the repo must stay small: only the newest Reels are kept
            run("rm", "-q", "--cached", f)
            os.remove(f)
        run("pull", "-q", "--rebase", "origin", "main")
        st = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
        st["reels"] = (st.get("reels", []) + [pid])[-500:]  # this watch has its Reel now
        json.dump(st, open(STATE_FILE, "w"), indent=1)
        run("add", out, STATE_FILE, last)
        run("commit", "-qm", f"bot: reel fila {n}")
        run("push", "-q", "origin", "HEAD:main")


if __name__ == "__main__":
    main()
