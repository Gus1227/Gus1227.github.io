# Kabuzio bot: the «Revisar» tab (replaces Make scenario 7752416, the ENVIAR button).
#   1. rows with A (aceptar) ticked go to Ofertas as Pendiente; rows with A or B ticked leave Revisar
#      and their product id goes to «Vistos» so they never come back
#   2. if fewer than 50 are left, it searches AliExpress again (30 keywords) and refills up to 200
# The bot clock runs it every turn, so no button is needed. REVISAR=si writes; anything else only prints.
import datetime, os, re, sys, time

sys.path.insert(0, os.path.dirname(__file__))
from telegram import google_token, sheets
from ali import ali

WRITE = os.environ.get("REVISAR", "no").lower() in ("si", "sí", "yes", "1")
REV_ID = 777001  # sheetId of «Revisar»
KEYWORDS = ("automatic watch men,mechanical watch men,chronograph watch men,diver watch men,luxury watch men,"
            "skeleton watch men,pilot watch men,tourbillon watch men,gmt watch men,sapphire automatic watch,"
            "titanium watch men,ceramic watch men,moonphase watch men,tonneau watch men,field watch men,"
            "pagani design watch,san martin watch,addiesdive watch,berny watch,sugess watch,watchdives watch,"
            "tsar bomba watch,seagull movement watch,proxima watch,steeldive watch,heimdallr watch,phylida watch,"
            "cronos watch,merkur watch,baltany watch").split(",")
FAMOUS = re.compile(r"rolex|omega|invicta|casio|seiko|citizen|tissot|tag heuer|patek|audemars|cartier|hublot|"
                    r"breitling|g-shock|apple|rolx|1:1")
# Ofertas columns that are formulas (same in every row): copied from row 2
FORMULA_COLS = "F G J K L Y Z AA".split()


def col(c):
    return sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(c))) - 1


def main():
    tok = google_token()
    got = sheets(tok, "values:batchGet?ranges=Revisar!A1:Q3000&ranges=Vistos!A1:A20000&ranges=Ofertas!X1:X5000"
                      "&valueRenderOption=FORMATTED_VALUE")["valueRanges"]
    rev, vistos, ofx = (g.get("values", []) for g in got)
    g = lambda r, i: (r[i] if i < len(r) else "").strip()
    print("Cabecera:", rev[0] if rev else [])
    rows = rev[1:]
    acted = [(n, r) for n, r in enumerate(rows, start=2) if g(r, 0).upper() == "TRUE" or g(r, 1).upper() == "TRUE"]
    accepted = [(n, r) for n, r in acted if g(r, 0).upper() == "TRUE" and g(r, 1).upper() != "TRUE"]
    quedan = len([r for r in rows if any(c.strip() for c in r)]) - len(acted)
    print(f"Revisar: {len(rows)} filas, marcadas {len(acted)}, aceptadas {len(accepted)}, quedan {quedan}")

    if WRITE and rev and "ENVIAR" in g(rev[0], 2):  # the old Make button is gone: the bot does it every 2 h
        sheets(tok, "values/Revisar!C1?valueInputOption=RAW", {"values": [["✅ Gus lo pasa solo cada 2 h"]]}, method="PUT")

    # ---------- 1. accepted to Ofertas, ticked rows out ----------
    if acted:
        f2 = sheets(tok, "values/Ofertas!A2:AA2?valueRenderOption=FORMULA").get("values", [[]])[0]
        out = []
        for n, r in accepted:
            line = [""] * 27
            put = lambda c, v: line.__setitem__(col(c), v)
            for c in FORMULA_COLS:
                put(c, f2[col(c)] if col(c) < len(f2) else "")
            put("A", g(r, 3)); put("B", g(r, 5)); put("C", g(r, 6)); put("D", g(r, 12)); put("E", g(r, 11))
            put("H", "Pendiente"); put("M", g(r, 4).replace(" ", "")); put("N", g(r, 8)); put("O", g(r, 9))
            put("V", g(r, 10)); put("W", g(r, 13)); put("X", "'" + g(r, 14))
            out.append(line)
            print("  a Ofertas:", g(r, 3)[:70])
        if WRITE:
            if out:  # after the last row, like Make did
                sheets(tok, "values/Ofertas!A1:AA:append?valueInputOption=USER_ENTERED&insertDataOption=OVERWRITE",
                       {"values": out}, method="POST")
            reqs = [{"appendDimension": {"sheetId": REV_ID, "dimension": "ROWS", "length": 1}}] + [
                {"deleteDimension": {"range": {"sheetId": REV_ID, "dimension": "ROWS", "startIndex": n - 1, "endIndex": n}}}
                for n, _ in sorted(acted, reverse=True)]  # bottom first so row numbers stay right
            sheets(tok, ":batchUpdate", {"requests": reqs}, method="POST")
            sheets(tok, "values/Vistos!A:A:append?valueInputOption=RAW",
                   {"values": [[g(r, 14)] for _, r in acted if g(r, 14)]}, method="POST")
            print(f"Hecho: {len(out)} a Ofertas, {len(acted)} fuera de Revisar.")

    # ---------- 2. refill ----------
    if quedan >= 50:
        return
    needed = 200 - quedan
    seen = {c.strip().lstrip("'") for row in [r[14:15] for r in rows] + vistos + ofx for c in row}
    found = {}
    page = int(time.time() // 7200) % 5 + 1  # page 1 is always the same: each turn looks at another page
    print("página", page)
    for kw in KEYWORDS:
        try:
            res = ali("aliexpress.affiliate.product.query", keywords=kw, min_sale_price=60, page_no=page, page_size=50,
                      ship_to_country="IL", sort="LAST_VOLUME_DESC", target_currency="USD", target_language="EN",
                      tracking_id="kabuzioTG")
        except SystemExit as e:
            print(kw, e)
            continue
        for p in ((res.get("result") or {}).get("products") or {}).get("product", []):
            pid = str(p.get("product_id"))
            try:
                ok = float(p.get("target_sale_price") or 0) >= 60 and \
                     float(str(p.get("evaluate_rate") or "0").replace("%", "")) >= 85
            except ValueError:
                ok = False
            if ok and pid not in seen and pid not in found and not FAMOUS.search(p.get("product_title", "").lower()):
                found[pid] = p
    new = list(found.values())[:needed]
    print(f"Búsqueda: {len(found)} nuevos, se agregan {len(new)} (faltaban {needed})")
    if not (WRITE and new):
        return
    today = datetime.date.today().isoformat()
    lines = [["", "", '=IMAGE(INDIRECT("M"&ROW()))', p.get("product_title", ""), p.get("product_title", "").split(" ")[0],
              f"${p.get('target_sale_price', '')}", f"${p.get('target_original_price', '')}", p.get("discount", ""),
              str(p.get("lastest_volume", "")), p.get("evaluate_rate", ""), p.get("product_video_url", ""),
              p.get("promotion_link", ""), p.get("product_main_image_url", ""),
              " ".join((p.get("product_small_image_urls") or {}).get("string") or []),
              "'" + str(p.get("product_id")), "Nuevo", today] for p in new]
    res = sheets(tok, "values/Revisar!A:Q:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS",
                 {"values": lines}, method="POST")
    first = int(re.search(r"!A(\d+)", res["updates"]["updatedRange"]).group(1))
    rng = {"sheetId": REV_ID, "startRowIndex": first - 1, "endRowIndex": first - 1 + len(lines)}
    sheets(tok, ":batchUpdate", {"requests": [
        {"setDataValidation": {"range": {**rng, "startColumnIndex": 0, "endColumnIndex": 2},
                               "rule": {"condition": {"type": "BOOLEAN"}}}},
        {"updateDimensionProperties": {"range": {"sheetId": REV_ID, "dimension": "ROWS", "startIndex": first - 1,
                                                 "endIndex": first - 1 + len(lines)},
                                       "properties": {"pixelSize": 110}, "fields": "pixelSize"}}]}, method="POST")
    print(f"Agregados {len(lines)} a Revisar desde la fila {first}.")


if __name__ == "__main__":
    main()
