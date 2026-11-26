"""Test the Alpha Vantage key: earnings calendar and QQQ 15-minute bars. Prints no key."""
import csv, io, json, os, sys, urllib.request
key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
if not key:
    sys.exit("ALPHAVANTAGE_API_KEY not set")
def get(q):
    with urllib.request.urlopen("https://www.alphavantage.co/query?%s&apikey=%s" % (q, key), timeout=60) as r:
        return r.read().decode()
e = get("function=EARNINGS_CALENDAR&horizon=3month")
if e.lstrip().startswith("{"):
    print("EARNINGS: error", e[:200].replace(key, "[key]"))
else:
    rows = list(csv.DictReader(io.StringIO(e)))
    print("EARNINGS: ok, %d rows; columns %s; sample %s" % (len(rows), list(rows[0].keys()) if rows else [], [r["symbol"] + " " + r["reportDate"] for r in rows if r["symbol"] in ("NVDA", "AVGO", "COST", "ADBE")][:4]))
import time; time.sleep(3)
j = json.loads(get("function=TIME_SERIES_INTRADAY&symbol=QQQ&interval=15min"))
meta = j.get("Meta Data")
if not meta:
    print("INTRADAY: error", json.dumps(j)[:300].replace(key, "[key]"))
else:
    ts = j.get("Time Series (15min)", {})
    keys = sorted(ts)
    print("INTRADAY: ok; meta %s; bars %d; first %s; last %s" % (json.dumps(meta), len(keys), keys[0] if keys else None, keys[-1] if keys else None))
    days = sorted({k[:10] for k in keys})[-3:]
    out = [[k, float(ts[k]["2. high"]), float(ts[k]["3. low"]), float(ts[k]["4. close"])] for k in keys if k[:10] in days]
    print("AVDATA " + json.dumps(out))
