import json, sources
from datetime import datetime, timezone, timedelta
up=json.loads(sources._get(sources.TD_URL%"upcoming?format=json"))
print("UPD", [(x.get("securityTerm"),x.get("type"),x.get("auctionDate"),x.get("competitiveAuctionCloseDate")) for x in up][:12])
print("AUC10", json.dumps(sources.auctions(datetime.now(timezone.utc)+timedelta(days=0)))[:800])
