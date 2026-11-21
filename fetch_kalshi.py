"""Pulls open Kalshi sports markets (incl. player props) -> data/markets.json
Uses only Kalshi's public market-data API (no key needed)."""
import json, sys, time, datetime, urllib.request, urllib.error

BASE = "https://api.elections.kalshi.com/trade-api/v2"
PROP_WORDS = ("passing yards", "rushing yards", "receiving yards", "touchdown", "receptions",
              "points", "rebounds", "assists", "threes", "strikeouts", "hits", "shots",
              "aces", "fantasy", "home run", "saves", "goals scored", "double")
SPORTS = [  # (label, keywords searched in series ticker + title)
    ("NFL", ("NFL",)), ("NBA", ("NBA",)), ("NHL", ("NHL",)), ("MLB", ("MLB",)),
    ("College", ("NCAAF", "NCAAB", "NCAAM", "NCAAW", "COLLEGE", "CFB", "CBB")),
    ("Tennis", ("TENNIS", "ATP", "WTA")), ("UFC", ("UFC", "MMA")),
    ("Golf", ("PGA", "GOLF", "LIV")),
    ("Soccer", ("SOCCER", "EPL", "MLS", "UCL", "LALIGA", "BUNDES", "SERIEA", "LIGUE", "WORLDCUP", "FIFA")),
]

def get(path, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0 kalshi-board"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 + i * 3); continue
            raise
        except Exception:
            time.sleep(1 + i)
    return None

def cents(m, key):
    """Kalshi has sent prices as integer cents or dollar strings; handle both."""
    v = m.get(key + "_dollars")
    if v not in (None, ""):
        try: return round(float(v) * 100)
        except ValueError: pass
    v = m.get(key)
    if isinstance(v, (int, float)):
        return round(v * 100) if isinstance(v, float) and v <= 1 else int(v)
    return 0

def sport_of(series):
    blob = (series.get("ticker", "") + " " + (series.get("title") or "")).upper()
    for label, keys in SPORTS:
        if any(k in blob for k in keys): return label
    return "Other"

def main():
    d = get("/series?category=Sports")
    if not d:
        print("Could not load series list"); sys.exit(1)
    series = d.get("series") or []
    print(len(series), "sports series")
    out, seen = [], set()
    for s in series:
        t = s["ticker"]
        cursor = ""
        while True:
            r = get(f"/markets?series_ticker={t}&status=open&limit=200" + (f"&cursor={cursor}" if cursor else ""))
            if not r: break
            for m in r.get("markets", []):
                if m["ticker"] in seen: continue
                seen.add(m["ticker"])
                price = cents(m, "yes_ask") or cents(m, "last_price") or cents(m, "yes_bid")
                if not (0 < price < 100): continue
                title = m.get("title") or ""
                sub = m.get("yes_sub_title") or ""
                blob = (title + " " + (s.get("title") or "")).lower()
                out.append({"t": m["ticker"], "n": sub or title, "m": title, "sp": sport_of(s),
                            "prop": any(w in blob for w in PROP_WORDS), "pr": price,
                            "c": m.get("close_time") or m.get("expected_expiration_time"),
                            "v": m.get("volume") or 0})
            cursor = r.get("cursor")
            if not cursor: break
        time.sleep(0.15)
    out.sort(key=lambda x: (x["c"] or "", -x["v"]))
    json.dump({"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source": "Kalshi public API",
               "markets": out}, open("data/markets.json", "w"), separators=(",", ":"))
    print(len(out), "markets saved;", sum(x["prop"] for x in out), "look like props")

main()
