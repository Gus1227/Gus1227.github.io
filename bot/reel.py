# Kabuzio bot: media agent. Builds a vertical Reel (1080x1920, ~15 s) for one watch with ffmpeg:
# the AliExpress video first (if any), then the photos with a slow zoom on black, and quiet text:
# KABUZIO on top, the clean headline and real specs, the price and «Link in bio» at the bottom.
# The file goes to r/<product id>.mp4 in this repo, so GitHub Pages serves it to Instagram, Facebook and TikTok.
#   REEL_FILA=<row>  that row;  empty = the next «Pendiente» of the queue (same order as Telegram)
#   REEL=si          also commit and push the file
import os, subprocess, sys, tempfile, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from telegram import EXTRA, IMG, NAME, PRICE, PRIO, STATE, TAB, VIDEO, BRAND_M, google_token, num, sheets

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
W, H, FPS = 1080, 1920, 30
PHOTO_S, VIDEO_S, MAX_PHOTOS, KEEP, FADE = 3.6, 5, 4, 30, 0.7
FX = ["fade", "smoothleft", "fadeblack", "smoothup"]  # quiet transitions, they take turns
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


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


def text_layer(d, head, spec, price):
    files = {}
    for k, v in {"brand": "K A B U Z I O", "head": head, "spec": spec, "price": price, "cta": "Link in bio"}.items():
        files[k] = os.path.join(d, k + ".txt")
        open(files[k], "w").write(v)
    t = lambda k, font, size, y, color="white": (
        f"drawtext=fontfile={font}:textfile={files[k]}:fontsize={size}:fontcolor={color}:x=(w-text_w)/2:y={y}"
        ":shadowcolor=black@0.8:shadowx=2:shadowy=2")  # readable over a bright video too
    return ",".join([t("brand", SERIF, 34, 120, "0xBBBBBB"), t("head", SERIF, min(58, int(58 * 30 / max(len(head), 1))), 200), t("spec", SANS, 32, 290, "0xCCCCCC"),
                     t("price", SERIF, 72, H - 330), t("cta", SANS, 36, H - 225, "0xCCCCCC")])


def build(r, out):
    from textos import headline, specs
    g = lambda i: (r[i] if i < len(r) else "").strip()
    pics = list(dict.fromkeys((g(IMG) + " " + g(EXTRA)).split()))[:MAX_PHOTOS]
    head = headline(g(NAME), g(BRAND_M))[:34]
    spec = ""
    for f in specs(g(NAME), 3):  # whole specs only, never cut in the middle
        if len(spec) + len(f) + 3 <= 52:
            spec = f"{spec} · {f}" if spec else f
    price = f"Now ${num(g(PRICE)):.2f}" if num(g(PRICE)) else g(PRICE)
    with tempfile.TemporaryDirectory() as d:
        clips = []
        if g(VIDEO):
            try:
                video_clip(get(g(VIDEO), os.path.join(d, "v.mp4")), os.path.join(d, "c0.mp4"))
                clips.append(os.path.join(d, "c0.mp4"))
            except Exception as e:  # a broken video never stops the Reel
                print("Video descartado:", e)
        for i, u in enumerate(pics):
            try:
                src = get(u if u.endswith(".jpg") else u + "_800x800.jpg", os.path.join(d, f"p{i}.jpg"))
                photo_clip(src, os.path.join(d, f"c{i + 1}.mp4"), i)
                clips.append(os.path.join(d, f"c{i + 1}.mp4"))
            except Exception as e:
                print("Foto descartada:", u, e)
        if not clips:
            raise SystemExit("Reel: sin fotos ni video")
        if len(clips) > 1 and clips[0].endswith("c0.mp4"):  # video second: first photo, video, other photos
            clips[0], clips[1] = clips[1], clips[0]
        durs = [float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", c],
                                     capture_output=True, text=True).stdout.strip() or PHOTO_S) for c in clips]
        # soft crossfade between every two parts
        chain, last, t = [], "[0:v]", 0.0
        for i in range(1, len(clips)):
            t += durs[i - 1] - FADE
            chain.append(f"{last}[{i}:v]xfade=transition={FX[i % len(FX)]}:duration={FADE}:offset={t:.2f}[x{i}]")
            last = f"[x{i}]"
        chain.append(f"{last}{text_layer(d, head, spec, price)}[v]")
        ins = [a for c in clips for a in ("-i", c)]
        ff(*ins, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", ";".join(chain),
           "-map", "[v]", "-map", f"{len(clips)}:a", "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out)
    print(f"Reel listo: {out} ({len(clips)} partes) · {head} · {spec} · {price}")


def main():
    want = os.environ.get("REEL_FILA", "").strip()
    rows = sheets(google_token(), f"values/{TAB}!A1:AM?valueRenderOption=FORMATTED_VALUE").get("values", [])
    if want:
        n = int(want)
    else:
        pend = [(n, r) for n, r in enumerate(rows[1:], start=2) if len(r) > STATE and r[STATE].strip() == "Pendiente"]
        if not pend:
            print("Reel: no hay relojes Pendiente.")
            return
        n = min(pend, key=lambda t: (num(t[1][PRIO]) if len(t[1]) > PRIO and t[1][PRIO].strip() else 1e9, t[0]))[0]
    r = rows[n - 1]
    pid = (r[23] if len(r) > 23 else "").strip().lstrip("'") or f"fila{n}"
    os.makedirs(os.path.join(ROOT, "r"), exist_ok=True)
    out = os.path.join(ROOT, "r", f"{pid}.mp4")
    build(r, out)
    print("URL: https://gus1227.github.io/r/" + pid + ".mp4")
    if os.environ.get("REEL", "no").lower() in ("si", "sí", "1"):
        run = lambda *a: subprocess.run(["git", *a], cwd=ROOT)
        keep = sorted((os.path.join(ROOT, "r", f) for f in os.listdir(os.path.join(ROOT, "r"))), key=os.path.getmtime)
        for f in keep[:-KEEP]:  # the repo must stay small: only the newest Reels are kept
            run("rm", "-q", "--cached", f)
            os.remove(f)
        run("add", out)
        run("commit", "-qm", f"bot: reel fila {n}")
        run("pull", "-q", "--rebase", "origin", "main")
        run("push", "-q", "origin", "HEAD:main")


if __name__ == "__main__":
    main()
