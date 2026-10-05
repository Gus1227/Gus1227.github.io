# Kabuzio bot: Instagram Stories and themed carousels (the files are made by historia.py and carrusel.py).
#   IG_EXTRA=historia:dia|historia:duelo|historia:top   posts s/<kind>.jpg as a Story
#   IG_EXTRA=carrusel                                   posts c/carrusel.json (6 slides + caption) as a carousel
# PUBLICAR=si publishes; anything else only prints. Before posting it waits until GitHub Pages serves the new
# file (same bytes as here), so Instagram never gets yesterday's picture.
import hashlib, json, os, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SITE = "https://gus1227.github.io/"
PUBLISH = os.environ.get("PUBLICAR", "no").lower() in ("si", "sí", "yes", "true", "1")


def live(path):
    """Public URL of a repo file once Pages serves this exact version (a ?v= keeps Instagram from caching)."""
    mine = hashlib.sha1(open(os.path.join(ROOT, path), "rb").read()).hexdigest()
    url = SITE + path
    for _ in range(40):
        try:
            got = urllib.request.urlopen(f"{url}?v={mine[:8]}{int(time.time())}", timeout=30).read()
            if hashlib.sha1(got).hexdigest() == mine:
                return f"{url}?v={mine[:10]}"
        except Exception:
            pass
        time.sleep(15)
    raise SystemExit(f"Pages todavía no tiene {path}")


def story(kind):
    from meta import IG, graph, wait_ready
    url = live(f"s/{kind}.jpg")
    print("Historia:", url)
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    cid = graph(f"/{IG}/media", {"media_type": "STORIES", "image_url": url}, post=True)["id"]
    wait_ready(cid)
    print("Historia publicada:", graph(f"/{IG}/media_publish", {"creation_id": cid}, post=True).get("id"))


def carousel():
    from meta import IG, graph, wait_ready
    data = json.load(open(os.path.join(ROOT, "c", "carrusel.json")))
    urls = [live("c/" + u.rsplit("/", 1)[-1]) for u in data["images"]]
    print(f"Carrusel «{data.get('tema')}»: {len(urls)} láminas\n{data['caption']}")
    if not PUBLISH:
        print("Modo prueba: no se publica nada.")
        return
    kids = [graph(f"/{IG}/media", {"is_carousel_item": "true", "image_url": u}, post=True)["id"] for u in urls]
    box = graph(f"/{IG}/media", {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": data["caption"]}, post=True)["id"]
    wait_ready(box)
    print("Carrusel publicado:", graph(f"/{IG}/media_publish", {"creation_id": box}, post=True).get("id"))


if __name__ == "__main__":
    what = os.environ.get("IG_EXTRA", "")
    if what.startswith("historia:"):
        story(what.split(":", 1)[1])
    elif what == "carrusel":
        carousel()
    else:
        raise SystemExit("IG_EXTRA = historia:dia | historia:duelo | historia:top | carrusel")
