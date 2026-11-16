"""
Post each new brief to a Discord channel through a webhook (send-only, no bot).

Set the GitHub secret DISCORD_WEBHOOK_URL to turn it on. Without it, nothing is posted.
One text card per new brief: headline, summary, driver, leader, the three scenarios,
the next scheduled events and a link to the full page.
"""
import json, os, urllib.request

H_LABEL = {"next_day": "Next session", "next_week": "Next 5 sessions", "next_month": "Next 21 sessions"}


def page_url():
    if os.environ.get("CONTEXT_ENGINE_PAGE_URL"):
        return os.environ["CONTEXT_ENGINE_PAGE_URL"]
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return "https://%s.github.io/%s/" % (owner.lower(), name)
    return None


def _cut(text, n):
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def card(brief, sources_ok=None, sources_total=None):
    w = brief.get("what_happened") or {}
    fields = [
        {"name": "Dominant driver", "value": _cut("**%s**\n%s" % (brief.get("dominant_driver", "?"), brief.get("driver_reason", "")), 1000), "inline": True},
        {"name": "Leader", "value": _cut("**%s**\n%s" % (brief.get("leader", "?"), brief.get("leader_reason", "")), 1000), "inline": True},
    ]
    for h in ("next_day", "next_week", "next_month"):
        o = (brief.get("outlook") or {}).get(h)
        if not o:
            continue
        p = o.get("probs_normalized") or {s.get("name"): s.get("prob") for s in o.get("scenarios", [])}
        hp = o.get("history_probs") or {}
        lines = []
        for name in ("bear", "base", "bull"):
            cond = {"bear": "< %+.2f%%", "bull": "> %+.2f%%"}.get(name)
            rng = (cond % (o["lower_pct"] if name == "bear" else o["upper_pct"])) if cond else "%+.2f%% to %+.2f%%" % (o["lower_pct"], o["upper_pct"])
            val = p.get(name)
            val = int(val) if isinstance(val, float) and val.is_integer() else val
            hist = " (history %s%%)" % hp[name] if hp.get(name) is not None else ""
            lines.append("`%-4s` %s%% · NDX %s%s" % (name, val, rng, hist))
        fields.append({"name": "%s · confidence %s" % (H_LABEL[h], o.get("confidence", "?")), "value": _cut("\n".join(lines), 1000), "inline": False})
    ev = brief.get("scheduled_events") or []
    if ev:
        fields.append({"name": "Scheduled (CET)", "value": _cut("\n".join("`%s` %s" % (e.get("when_vienna", ""), e.get("event", "")) for e in ev[:6]), 1000), "inline": False})
    wl = brief.get("watch_list") or []
    if wl:
        fields.append({"name": "Watch", "value": _cut("\n".join("• " + x for x in wl[:4]), 1000), "inline": False})
    flags = brief.get("number_flags") or []
    foot = "%s · %s" % (brief.get("slot_label", ""), brief.get("id", ""))
    if sources_total:
        foot += " · %d/%d sources" % (sources_ok, sources_total)
    foot += " · numbers check %s" % ("clean" if not flags else "%d unsourced" % len(flags))
    url = page_url()
    embed = {"title": _cut(brief.get("headline") or "Context Engine", 250), "description": _cut(w.get("summary", ""), 1500),
             "color": 0xE8E8E8, "fields": fields, "footer": {"text": _cut(foot, 2000)}}
    if url:
        embed["url"] = url
    content = "New Context Engine brief" + (": <%s>" % url if url else "")
    return {"username": "Context Engine", "content": content, "embeds": [embed], "allowed_mentions": {"parse": []}}


def post(brief, sources_ok=None, sources_total=None, scrub=lambda s: s):
    hook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not hook:
        return "not set up (no DISCORD_WEBHOOK_URL secret)"
    body = scrub(json.dumps(card(brief, sources_ok, sources_total))).encode()
    req = urllib.request.Request(hook, data=body, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "DiscordBot (context-engine, 1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return "posted (HTTP %s)" % r.status
