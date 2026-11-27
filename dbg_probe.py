import json, sources
from datetime import datetime, timezone, timedelta
g=sources._get
try:
    j=json.loads(g("https://api.elections.kalshi.com/trade-api/v2/series?category=Economics",headers={"Accept":"application/json"}))
    print("KSERIES", [ (s.get("ticker"),s.get("title")) for s in j.get("series",[]) if any(w in (s.get("title","")+s.get("ticker","")).lower() for w in ("fed","cpi","payroll","recession","inflation","jobs","rate"))][:40])
except Exception as e: print("KSERIES fail",e)
try:
    j=json.loads(g(sources.KALSHI_URL%"KXFED",headers={"Accept":"application/json"})); print("KXFED", json.dumps(j)[:600])
except Exception as e: print("KXFED fail",e)
rows=json.loads(g("https://publicreporting.cftc.gov/resource/gpe5-46if.json?$select=market_and_exchange_names,count(*)&$group=market_and_exchange_names&$where="+__import__('urllib.parse').parse.quote("upper(market_and_exchange_names) like '%NASDAQ%'")))
print("COTNAMES",rows)
now=datetime.now(timezone.utc)
u=("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query?filter=auction_date:gte:%s&sort=-auction_date&page[size]=5"%(now-timedelta(days=20)).strftime("%Y-%m-%d"))
print("AUCT", g(u)[:1200])
