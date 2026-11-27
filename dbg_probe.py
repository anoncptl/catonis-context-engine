import json, sources, traceback
g=sources._get
try:
    j=json.loads(g(sources.KALSHI_URL%"KXFED",headers={"Accept":"application/json"}))
    print("KTOP", list(j.keys()), len(j.get("markets") or []), len(j.get("events") or []))
    ms = j.get("markets") or [m for ev in j.get("events") or [] for m in ev.get("markets") or []]
    print("KM", len(ms), json.dumps({k:v for k,v in (ms[0] if ms else {}).items() if 'price' in k or 'bid' in k or k in ('close_time','yes_sub_title','status')})[:600])
except Exception: traceback.print_exc()
T="https://www.treasurydirect.gov/TA_WS/securities/"
for u in ("auctioned?format=json&type=Note&days=30","upcoming?format=json"):
    try:
        d=json.loads(g(T+u)); print("TD",u, len(d), json.dumps([{k:x.get(k) for k in ("securityTerm","auctionDate","highYield","bidToCoverRatio","indirectBidderAccepted","totalAccepted","primaryDealerAccepted","offeringAmount","type")} for x in d[:3]])[:700])
    except Exception as e: print("TD fail",u,e)
