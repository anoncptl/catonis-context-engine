import json, sources
g=sources._get
d=json.loads(g(sources.TD_URL%"auctioned?format=json&type=Note&days=30"))
print("TDKEYS", [k for k in d[0] if 'ate' in k.lower()][:20], {k:d[0][k] for k in d[0] if 'ate' in k.lower()})
print("FEDK", json.dumps(sources.kalshi())[:500])
