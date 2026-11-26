"""
Post each new brief to a Discord channel through a webhook (send-only, no bot).

Set the GitHub secret DISCORD_WEBHOOK_URL to turn it on. Without it, nothing is posted.
Plain text, no links: a title, then three sections (What happened, Dominant driver, Detail).
Discord allows 2,000 characters per message, so a long brief is split at section breaks.
"""
import json, os, time, urllib.request

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


LIMIT = 1990


def text_sections(brief):
    """The three sections as plain text."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    try:
        day = datetime.fromisoformat(brief["made_utc"]).astimezone(ZoneInfo("Europe/Vienna")).strftime("%A %d %B %Y")
    except Exception:
        day = brief.get("id", "")
    w = brief.get("what_happened") or {}
    title = "# Context Engine · %s" % day
    happened = "## What happened\n**%s**\n%s" % ((brief.get("headline") or "").strip(), (w.get("summary") or "").strip())
    driver = "## Dominant driver\n**%s**\n%s" % ((brief.get("dominant_driver") or "").strip().capitalize(), (brief.get("driver_reason") or "").strip())
    detail = "## Detail\n" + "\n".join("**%s:** %s" % (lab, (w.get(k) or "").strip())
                                       for k, lab in (("market_action", "Market"), ("macro", "Macro"),
                                                      ("geopolitics", "Geopolitics"), ("company_news", "Company news")) if w.get(k))
    if brief.get("unconfirmed"):
        detail += "\n**Unconfirmed:** " + "; ".join(brief["unconfirmed"])
    return [title, happened, driver, detail]


def _chunks(text):
    """Split one section that is too long for a single message: whole lines first, sentences only if a line is too long."""
    head, _, body = text.partition("\n")
    units = []
    for line in body.split("\n"):
        if len(line) <= LIMIT - len(head) - 20:
            units.append(line)
        else:
            cur = ""
            for sent in line.replace(". ", ".\u0000").split("\u0000"):
                if cur and len(cur) + len(sent) + 1 > LIMIT - len(head) - 20:
                    units.append(cur.rstrip()); cur = ""
                cur += sent + " "
            if cur.strip():
                units.append(cur.rstrip())
    out, cur = [], head
    for u in units:
        if len(cur) + 1 + len(u) > LIMIT:
            out.append(cur)
            cur = head + " (continued)"
        cur += "\n" + u
    out.append(cur)
    return out


def messages(brief):
    """Group the sections into as few messages as fit, never splitting a section unless it alone is too long."""
    msgs, cur = [], ""
    for sec in text_sections(brief):
        for piece in (_chunks(sec) if len(sec) > LIMIT else [sec]):
            if cur and len(cur) + 2 + len(piece) > LIMIT:
                msgs.append(cur); cur = ""
            cur = (cur + "\n\n" + piece) if cur else piece
    if cur:
        msgs.append(cur)
    return msgs


def post(brief, sources_ok=None, sources_total=None, scrub=lambda s: s):
    hook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not hook:
        return "not set up (no DISCORD_WEBHOOK_URL secret)"
    sent = 0
    for msg in messages(brief):
        payload = {"username": "Context Engine", "content": msg, "allowed_mentions": {"parse": []}, "flags": 4}  # 4 = no link previews
        req = urllib.request.Request(hook, data=scrub(json.dumps(payload)).encode(), method="POST", headers={
            "Content-Type": "application/json", "User-Agent": "DiscordBot (context-engine, 1.0)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            sent += 1
        time.sleep(1)
    return "posted %d message%s" % (sent, "" if sent == 1 else "s")
