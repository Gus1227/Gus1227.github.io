# Kabuzio bot: seller coupons from the AliExpress API (ali.py revision keeps bot/cupones.json fresh once a day).
# Instagram posts of a watch with a coupon ask people to comment; respuestas.py then sends the code by private message.
import datetime, json, os, re

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cupones.json")
PID = 23  # column X


def todos():
    return json.load(open(FILE)) if os.path.exists(FILE) else {}


def corto(value):
    """«On order over USD 90.0 , get USD 9.00 off» -> «$9 off orders over $90»."""
    m = re.search(r"over USD ([\d.]+).*?USD ([\d.]+) off", value or "")
    f = lambda x: ("%.2f" % float(x)).rstrip("0").rstrip(".")
    return f"${f(m.group(2))} off orders over ${f(m.group(1))}" if m else (value or "").strip()


def de(r):
    """Valid coupon of a sheet row, or None."""
    pid = (r[PID] if len(r) > PID else "").strip()
    c = todos().get(pid)
    if not c or c.get("fin", "") < datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"):
        return None
    price = re.sub(r"[^0-9.]", "", (r[1] if len(r) > 1 else "").replace(",", ""))
    try:  # a coupon the watch alone cannot reach is no help
        if float(c.get("minimo") or 0) > float(price or 0):
            return None
    except ValueError:
        pass
    return c


def linea_ig(r):
    c = de(r)
    return f"🎟 Extra coupon: {corto(c['valor'])} · comment COUPON and we'll DM you the code\n" if c else ""


def guardar(prods):
    """prods: products of aliexpress.affiliate.productdetail.get (only the ones that were read today)."""
    data = todos()
    for p in prods:
        pid, info = str(p["product_id"]), p.get("promo_code_info")
        if info and info.get("promo_code"):
            data[pid] = {"codigo": info["promo_code"], "valor": info.get("code_value", ""),
                         "minimo": info.get("code_mini_spend", ""), "fin": info.get("code_availabletime_end", "")}
        else:
            data.pop(pid, None)
    json.dump(dict(sorted(data.items())), open(FILE, "w"), indent=1, ensure_ascii=False)
    return data
