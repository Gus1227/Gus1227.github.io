# Kabuzio bot: copies the public «Catalogo» CSV into catalogo.csv on this site, so the website loads it from
# GitHub Pages (fast, same address) instead of waiting for Google Sheets. Run every bot turn and by feed.yml.
import os, urllib.request

CSV = ("https://docs.google.com/spreadsheets/d/e/2PACX-1vQRH7X54O1GzNSUWnIgBT1545CXdQMaZ7HOzKOyJC6mZKyXG9gxJ9T5DBbAv0WzbkZXOdHrW8ubzUwS/"
       "pub?gid=596242979&single=true&output=csv")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "catalogo.csv")

if __name__ == "__main__":
    data = urllib.request.urlopen(CSV, timeout=60).read()
    if len(data) > 200 and data.lstrip()[:1] != b"<":  # never replace a good copy with an error page
        open(OUT, "wb").write(data)
        print("catalogo.csv:", len(data), "bytes")
    else:
        print("catalogo.csv: Google no dio el CSV, se queda el anterior")
