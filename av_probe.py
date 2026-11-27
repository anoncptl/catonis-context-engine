"""Test the newer sources without making a brief or posting to Discord. Prints no keys."""
import json, os, sys
from datetime import datetime, timezone
import sources

now = datetime.now(timezone.utc)
secrets = [os.environ.get(k, "") for k in ("ALPHAVANTAGE_API_KEY", "EIA_API_KEY", "FRED_API_KEY")]


def show(name, fn):
    try:
        v = fn()
        txt = json.dumps(v)[:700]
        print("%s: ok %s" % (name, txt))
    except Exception as e:
        txt = "%s: FAILED %s" % (name, e)
        print(txt[:400])
        return
    for s in secrets:
        if s and len(s) > 5:
            assert s not in txt



show("kalshi_macro", sources.kalshi_macro)
show("cot", sources.cot)
show("auctions", lambda: sources.auctions(now))
show("gdpnow", lambda: sources.gdpnow(now))
show("eia", sources.eia)
