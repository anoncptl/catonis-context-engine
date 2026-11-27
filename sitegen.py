"""
Static website for the Context Engine: plain black page, white text, no external files.

  site/index.html      latest brief, data, calendar and source health
  site/record.html     forecast record: every graded scenario and Brier scores
  site/archive.html    list of every brief
  site/b/<id>.html     each brief on its own page
"""
import html, json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

VIENNA = ZoneInfo("Europe/Vienna")
H_LABEL = {"next_day": "Next session", "next_week": "Next 5 sessions", "next_month": "Next 21 sessions"}

CSS = """
:root{--bg:#000;--panel:#0a0a0a;--line:#232323;--fg:#f2f2f2;--muted:#8d8d8d;--dim:#5c5c5c;--up:#bfe9cf;--down:#f3b2b2;--warn:#ecdcae;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 var(--sans)}
a{color:var(--fg);text-decoration-color:var(--dim);text-underline-offset:3px}a:hover{text-decoration-color:var(--fg)}
.wrap{max-width:1100px;margin:0 auto;padding:22px 16px 60px}
header{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:flex-end;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:16px}
.brand{font:600 12px var(--mono);letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
h1{font-size:26px;line-height:1.2;margin:6px 0 0;letter-spacing:-.01em}
nav{display:flex;gap:6px;flex-wrap:wrap}nav a{font:500 12px var(--mono);letter-spacing:.08em;text-transform:uppercase;text-decoration:none;border:1px solid var(--line);padding:6px 10px;color:var(--muted)}
nav a.on,nav a:hover{color:var(--fg);border-color:var(--fg)}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0}.chip{font:12px var(--mono);border:1px solid var(--line);padding:4px 9px;color:var(--muted)}.chip b{color:var(--fg);font-weight:500}
.chip.bad{border-color:#5a2a2a;color:var(--down)}
h2{font:600 12px var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin:0 0 12px}
section{margin-top:22px}.panel{background:var(--panel);border:1px solid var(--line);padding:18px}
.grid{display:grid;gap:12px}.g2{grid-template-columns:repeat(2,minmax(0,1fr))}.g3{grid-template-columns:repeat(3,minmax(0,1fr))}
.big{font-size:21px;line-height:1.3;font-weight:600;margin:0 0 6px}
.lead{font-size:17px;line-height:1.55;margin:0}
p{margin:0 0 10px}.muted{color:var(--muted)}.small{font-size:13px}.mono{font-family:var(--mono)}
dl{display:grid;grid-template-columns:150px 1fr;gap:6px 16px;margin:12px 0 0}dt{color:var(--muted);font:12px var(--mono);letter-spacing:.06em;text-transform:uppercase;padding-top:3px}dd{margin:0}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font:500 11px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}td.n{font-family:var(--mono);white-space:nowrap}
.scroll{overflow-x:auto}
.h{border:1px solid var(--line);background:var(--panel);padding:16px}.h h3{margin:0;font-size:16px}.h .cut{font:12px var(--mono);color:var(--muted);margin:4px 0 12px}
.sc{border-top:1px solid var(--line);padding:10px 0}.sc .row{display:flex;justify-content:space-between;gap:10px;font:600 13px var(--mono);text-transform:uppercase;letter-spacing:.08em}
.bar{height:4px;background:#1b1b1b;margin:6px 0 8px;position:relative}.bar i{position:absolute;inset:0 auto 0 0;background:var(--fg)}.bar u{position:absolute;top:-3px;width:2px;height:10px;background:var(--muted)}
.sc p{font-size:14px;margin:0 0 4px}.inv{color:var(--muted);font-size:13px}
.bear .row span:first-child{color:var(--down)}.bull .row span:first-child{color:var(--up)}
.ok{color:var(--up)}.fail{color:var(--down)}.warn{color:var(--warn)}
ul{margin:0;padding-left:18px}li{margin:3px 0}
details{border:1px solid var(--line);background:var(--panel);padding:12px 16px}summary{cursor:pointer;font:600 12px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
details[open] summary{margin-bottom:10px}
.flag{border-left:2px solid var(--warn);padding:4px 0 4px 10px;margin:6px 0;font-size:14px}
footer{margin-top:40px;border-top:1px solid var(--line);padding-top:14px;color:var(--dim);font-size:12px}
@media(max-width:760px){.g2,.g3{grid-template-columns:1fr}dl{grid-template-columns:1fr}dt{padding-top:8px}h1{font-size:22px}}
"""


def e(x):
    return html.escape("" if x is None else str(x))


def fmt_time(iso):
    try:
        return datetime.fromisoformat(iso).astimezone(VIENNA).strftime("%a %d %b %Y, %H:%M %Z")
    except Exception:
        return e(iso)


def page(title, body, active, prefix=""):
    nav = "".join('<a class="%s" href="%s%s">%s</a>' % ("on" if k == active else "", prefix, href, lab)
                  for k, href, lab in (("latest", "index.html", "Latest"), ("record", "record.html", "Record"), ("archive", "archive.html", "Archive"), ("sources", "sources.html", "Sources")))
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"robots\" content=\"noindex\"><title>%s</title><style>%s</style></head><body><div class=\"wrap\">"
            "<header><div><div class=\"brand\">Context Engine</div><h1>%s</h1></div><nav>%s</nav></header>%s"
            "<footer>Personal research tool. Built from public sources: Cboe Insights, US Treasury, FRED, BLS, SEC EDGAR, the Federal Reserve, "
            "Kalshi, Polymarket, GDELT and Google News. No live prices. Scenarios are conditional and graded automatically; they are not advice.</footer>"
            "</div></body></html>") % (e(title), CSS, e(title), nav, body)


def render_brief(b, prefix=""):
    out = []
    flags = b.get("number_flags") or []
    out.append('<div class="meta"><span class="chip">%s</span><span class="chip">Made <b>%s</b></span>'
               '<span class="chip">Reference close <b>%s</b></span>%s</div>' % (
                   e(b.get("slot_label")), fmt_time(b.get("made_utc")), e(b.get("ref_date")),
                   '<span class="chip bad">%d unsourced number%s</span>' % (len(flags), "" if len(flags) == 1 else "s") if flags else
                   '<span class="chip">Numbers check <b>clean</b></span>'))
    w = b.get("what_happened") or {}
    out.append('<section class="grid g2"><div class="panel"><h2>What happened</h2><p class="big">%s</p><p class="lead">%s</p></div>'
               '<div class="panel"><h2>Dominant driver</h2><p class="big">%s</p><p>%s</p><h2 style="margin-top:16px">Leader</h2>'
               '<p class="big">%s</p><p>%s</p></div></section>' % (
                   e(b.get("headline")), e(w.get("summary")), e(b.get("dominant_driver")), e(b.get("driver_reason")),
                   e(b.get("leader")), e(b.get("leader_reason"))))
    out.append('<section class="panel"><h2>Detail</h2><dl><dt>Market</dt><dd>%s</dd><dt>Macro</dt><dd>%s</dd><dt>Geopolitics</dt><dd>%s</dd>'
               '<dt>Company news</dt><dd>%s</dd></dl></section>' % (e(w.get("market_action")), e(w.get("macro")),
                                                                     e(w.get("geopolitics")), e(w.get("company_news"))))
    hz = []
    for h in ("next_day", "next_week", "next_month"):
        o = (b.get("outlook") or {}).get(h)
        if not o:
            continue
        hp = o.get("history_probs") or {}
        sc = []
        for s in sorted(o.get("scenarios", []), key=lambda s: ["bear", "base", "bull"].index(s.get("name")) if s.get("name") in ("bear", "base", "bull") else 3):
            n = s.get("name", "")
            p = (o.get("probs_normalized") or {}).get(n, s.get("prob"))
            p = int(p) if isinstance(p, float) and p.is_integer() else p
            cond = {"bear": "below %+.2f%%" % o["lower_pct"], "bull": "above %+.2f%%" % o["upper_pct"],
                    "base": "%+.2f%% to %+.2f%%" % (o["lower_pct"], o["upper_pct"])}.get(n, "") if isinstance(o.get("lower_pct"), (int, float)) else ""
            hist = ' · history %s%%' % hp[n] if hp.get(n) is not None else ""
            sc.append('<div class="sc %s"><div class="row"><span>%s %s</span><span>%s%%</span></div>'
                      '<div class="bar"><i style="width:%s%%"></i>%s</div><p>%s</p><p class="inv">Invalid if: %s</p></div>' % (
                          e(n), e(n), '<span class="muted" style="text-transform:none;letter-spacing:0;font-weight:400">%s%s</span>' % (e(cond), e(hist)),
                          e(p), e(p), '<u style="left:%s%%"></u>' % hp[n] if hp.get(n) is not None else "", e(s.get("text")), e(s.get("invalidation"))))
        hz.append('<div class="h"><h3>%s</h3><div class="cut">Nasdaq-100 change vs the %s close · confidence %s</div>%s<p class="small muted" style="margin-top:8px">%s</p></div>' % (
            H_LABEL[h], e(b.get("ref_date")), e(o.get("confidence")), "".join(sc), e(o.get("confidence_reason"))))
    if hz:
        out.append('<section><h2>Scenarios · graded automatically</h2><div class="grid g3">%s</div>'
                   '<p class="small muted" style="margin-top:8px">The grey tick on each bar is how often that outcome happened historically with VIX in the same range. '
                   'If the engine keeps beating that tick on the record page, its probabilities add something. If not, they do not.</p></section>' % "".join(hz))
    ev = b.get("scheduled_events") or []
    if ev:
        out.append('<section class="panel"><h2>Scheduled events (engine)</h2><div class="scroll"><table><tr><th>When (CET)</th><th>Event</th><th>Why it matters</th><th>Source</th></tr>%s</table></div></section>' % "".join(
            '<tr><td class="n">%s</td><td>%s</td><td>%s</td><td class="muted small">%s</td></tr>' % (e(x.get("when_vienna")), e(x.get("event")), e(x.get("why_it_matters")), e(x.get("source"))) for x in ev))
    ov = b.get("overlap_with_previous") or {}
    out.append('<section class="grid g3">%s</section>' % "".join(
        '<div class="panel"><h2>%s</h2><ul>%s</ul></div>' % (lab, "".join("<li>%s</li>" % e(i) for i in (ov.get(k) or [])) or "<li class=muted>none</li>")
        for k, lab in (("continuing", "Continuing"), ("new", "New"), ("fading", "Fading"))))
    out.append('<section class="grid g2"><div class="panel"><h2>Echo check</h2><p>%s</p></div><div class="panel"><h2>Watch next session</h2><ul>%s</ul></div></section>' % (
        e(ov.get("echo_check")), "".join("<li>%s</li>" % e(i) for i in (b.get("watch_list") or [])) or "<li class=muted>none</li>"))
    if flags:
        out.append('<section class="panel"><h2>Numbers the engine could not match to a source</h2>%s<p class="small muted">'
                   'These figures are in the brief but not in any input it was given. Treat them as unverified.</p></section>' % "".join(
                       '<div class="flag"><b class="mono">%s</b> · %s</div>' % (e(f["number"]), e(f["context"])) for f in flags))
    out.append('<section class="panel"><h2>Record</h2><p>%s</p><p class="small"><a href="%srecord.html">Full forecast record</a></p></section>' % (
        e(b.get("record_comment")), prefix))
    posts = b.get("posts_used") or []
    if posts:
        out.append('<section class="panel"><h2>Cboe posts read</h2><div class="scroll"><table><tr><th>Date</th><th>Title</th><th>Text</th></tr>%s</table></div></section>' % "".join(
            '<tr><td class="n">%s</td><td><a href="%s">%s</a>%s</td><td class="small muted">%s</td></tr>' % (
                e(p.get("date") or "–"), e(p.get("url")), e(p.get("title")), ' <span class="muted small">(%s)</span>' % e(p.get("tag")) if p.get("tag") and p.get("tag") != "new" else (' <span class="muted small">(seen before)</span>' if p.get("older") else ""),
                "full article" if p.get("text_source") == "full_article" else "summary only") for p in posts))
    return "".join(out)


def render_status(st):
    out = []
    F = st.get("facts") or []
    if F:
        groups = {}
        for f in F:
            groups.setdefault(f["group"], []).append(f)
        rows = "".join('<tr><th colspan="5" style="padding-top:16px">%s</th></tr>' % e(g) + "".join(
            '<tr><td>%s</td><td class="n">%s %s</td><td class="n muted">%s</td><td class="n">%s</td><td class="small muted">%s</td></tr>' % (
                e(f["label"]), e(f["value"]), e(f["unit"]), e(f.get("change") or ""), e(f["as_of"]), e(f["source"])) for f in fs)
            for g, fs in groups.items())
        out.append('<section class="panel"><h2>Key numbers · every one with its source and date</h2><div class="scroll"><table>'
                   '<tr><th>What</th><th>Value</th><th>Change</th><th>As of</th><th>Source</th></tr>%s</table></div></section>' % rows)
    ch = st.get("checks") or []
    if ch:
        out.append('<section class="panel"><h2>Cross-source checks</h2><div class="scroll"><table><tr><th>What</th><th>Date</th><th>Source A</th><th>Source B</th><th>Result</th></tr>%s</table></div></section>' % "".join(
            '<tr><td>%s</td><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td><td class="%s">%s, %s</td></tr>' % (
                e(c["what"]), e(c["date"]), e(c["a"]), e(c["b"]), "ok" if c["agree"] else "warn", "agree" if c["agree"] else "DISAGREE", e(c["note"])) for c in ch))
    cal = st.get("calendar") or []
    if cal:
        out.append('<section class="panel"><h2>Official calendar · next 14 days</h2><div class="scroll"><table><tr><th>CET</th><th>New York</th><th>Event</th><th>Source</th></tr>%s</table></div></section>' % "".join(
            '<tr><td class="n">%s</td><td class="n muted">%s</td><td>%s</td><td class="small muted">%s%s</td></tr>' % (
                e(c["when_vienna"]), e(c["when_new_york"]), e(c["event"]), e(c["source"]), " · " + e(c["time_note"]) if c.get("time_note") else "") for c in cal))
    ern = st.get("earnings") or []
    if ern:
        out.append('<section class="panel"><h2>Earnings · largest Nasdaq-100 names, next 45 days</h2><div class="scroll"><table><tr><th>Date</th><th>Company</th><th>When</th><th>EPS estimate</th></tr>%s</table></div></section>' % "".join(
            '<tr><td class="n">%s</td><td><b class="mono">%s</b> <span class="muted small">%s</span></td><td class="small muted">%s</td><td class="n">%s</td></tr>' % (
                e(x["day"]), e(x["ticker"]), e(x["name"]), e(x["timing"] or "time not given"), e(x["estimate_eps"] if x["estimate_eps"] is not None else "–")) for x in ern))
    cons = st.get("consensus") or []
    if cons:
        out.append('<details><summary>Consensus forecasts · unofficial</summary><div class="scroll"><table><tr><th>CET</th><th>Event</th><th>Forecast</th><th>Previous</th></tr>%s</table></div></details>' % "".join(
            '<tr><td class="n">%s</td><td>%s</td><td class="n">%s</td><td class="n muted">%s</td></tr>' % (
                e(c["when_vienna"]), e(c["event"]), e(c.get("forecast") or "–"), e(c.get("previous") or "–")) for c in cons))
    ed = st.get("edgar") or []
    out.append('<section class="panel"><h2>SEC 8-K filings · 10 largest Nasdaq-100 companies, last 4 days</h2>%s</section>' % (
        '<div class="scroll"><table><tr><th>Filed</th><th>Company</th><th>Items</th><th>Excerpt</th></tr>%s</table></div>' % "".join(
            '<tr><td class="n">%s</td><td class="n"><a href="%s">%s</a></td><td class="small">%s</td><td class="small muted">%s</td></tr>' % (
                e(f["filed"]), e(f["link"]), e(f["ticker"]), e("; ".join(f["items"])), e((f.get("excerpt") or "")[:260])) for f in ed)
        if ed else '<p class="muted">No 8-K filings in the window.</p>'))
    odds = st.get("odds") or []
    if odds:
        out.append('<section class="panel"><h2>Fed decision odds · prediction markets</h2><div class="grid g3">%s</div>'
                   '<p class="small muted" style="margin-top:8px">Market prices from public data, not CME FedWatch.</p></section>' % "".join(
                       '<div><p class="small"><b>%s</b> · %s%s</p><table>%s</table></div>' % (
                           e(o["venue"]), e(o["event"]), " · " + e(o["close"]) if o.get("close") else "",
                           "".join('<tr><td class="small">%s</td><td class="n">%s%%</td></tr>' % (e(m["outcome"]), e(m["prob_pct"])) for m in o["markets"])) for o in odds))
    fed = st.get("fed") or []
    if fed:
        out.append('<section class="panel"><h2>Federal Reserve · last 7 days</h2><ul>%s</ul></section>' % "".join(
            '<li><span class="mono small muted">%s</span> <a href="%s">%s</a></li>' % (e(f["time_vienna"]), e(f["link"]), e(f["title"])) for f in fed))
    for key, lab in (("gdelt", "Global and geopolitical headlines (GDELT) · unverified"), ("headlines", "Market headlines since the last close (Google News) · unverified")):
        hs = st.get(key) or []
        if hs:
            out.append('<details><summary>%s · %d</summary><ul>%s</ul></details>' % (lab, len(hs), "".join(
                '<li><span class="mono small muted">%s</span> <a href="%s">%s</a> <span class="muted small">%s</span></li>' % (
                    e(h.get("time_vienna")), e(h.get("link")), e(h.get("headline")), e(h.get("publisher"))) for h in hs)))
    stt = st.get("status") or {}
    n_ok = sum(1 for v in stt.values() if v["ok"])
    out.append('<section class="panel" id="health"><h2>Source health · %d of %d working · checked %s</h2><div class="scroll"><table><tr><th>Source</th><th>Status</th><th>Detail</th></tr>%s</table></div>'
               '<p class="small muted" style="margin-top:8px">Failed sources are skipped. The brief only uses what worked.</p></section>' % (
                   n_ok, len(stt), fmt_time(st.get("utc")), "".join(
                       '<tr><td>%s</td><td class="%s mono small">%s</td><td class="small muted">%s</td></tr>' % (
                           e(v["name"]), "ok" if v["ok"] else "fail", "working" if v["ok"] else "failed", e(v["detail"])) for v in stt.values())))
    return "".join(out), n_ok, len(stt)


def render_record(ledger):
    res = [x for x in ledger if x["status"] == "resolved"]
    opn = [x for x in ledger if x["status"] == "open"]
    out = ['<section class="panel"><h2>How to read this</h2><p>Every brief makes three forecasts on one number: the Nasdaq-100 change from a reference close '
           'to the close 1, 5 or 21 sessions later, split into bear, base and bull by two cut points. Code grades them from FRED closes.</p>'
           '<p class="small muted">Brier score: 0 is perfect, 2 is the worst. Equal odds (one third each) always score 0.667. '
           '"History" uses how often each outcome happened in the past with VIX in the same range. The engine is only useful if its score is below both.</p></section>']
    rows = []
    for h in ("next_day", "next_week", "next_month"):
        r = [x for x in res if x["horizon"] == h]
        if not r:
            rows.append('<tr><td>%s</td><td class="n" colspan="5"><span class="muted">no graded forecasts yet</span></td></tr>' % H_LABEL[h]); continue
        hb = [x["brier_history"] for x in r if x.get("brier_history") is not None]
        avg = sum(x["brier"] for x in r) / len(r)
        hist = sum(hb) / len(hb) if hb else None
        top = sum(max(x["probs"], key=x["probs"].get) == x["outcome"] for x in r)
        verdict = "n/a" if hist is None else ("beats history" if avg < hist else "worse than history")
        rows.append('<tr><td>%s</td><td class="n">%d</td><td class="n"><b>%.3f</b></td><td class="n">%s</td><td class="n muted">%.3f</td><td class="n">%d/%d · %s</td></tr>' % (
            H_LABEL[h], len(r), avg, "%.3f" % hist if hist is not None else "–", sum(x["brier_equal"] for x in r) / len(r), top, len(r), verdict))
    out.append('<section class="panel"><h2>Scoreboard</h2><div class="scroll"><table><tr><th>Horizon</th><th>Graded</th><th>Engine Brier</th><th>History Brier</th><th>Equal odds</th><th>Top pick right</th></tr>%s</table></div>'
               '<p class="small muted" style="margin-top:8px">%d forecasts still open. A fair verdict needs at least 20 graded forecasts per horizon.</p></section>' % ("".join(rows), len(opn)))
    if res:
        out.append('<section class="panel"><h2>Graded forecasts</h2><div class="scroll"><table><tr><th>Ref close</th><th>Horizon</th><th>Cut points</th><th>Bear / base / bull</th><th>Actual</th><th>Outcome</th><th>Brier</th><th>History</th></tr>%s</table></div></section>' % "".join(
            '<tr><td class="n">%s</td><td>%s</td><td class="n">%+.2f / %+.2f</td><td class="n">%s / %s / %s</td><td class="n">%+.2f%%</td><td class="mono small">%s</td><td class="n">%.3f</td><td class="n muted">%s</td></tr>' % (
                e(x["ref_date"]), H_LABEL[x["horizon"]], x["lower_pct"], x["upper_pct"], e(x["probs"]["bear"]), e(x["probs"]["base"]), e(x["probs"]["bull"]),
                x["change_pct"], e(x["outcome"]), x["brier"], "%.3f" % x["brier_history"] if x.get("brier_history") is not None else "–")
            for x in sorted(res, key=lambda x: (x["end_date"], x["horizon"]), reverse=True)))
    if opn:
        out.append('<section class="panel"><h2>Open forecasts</h2><div class="scroll"><table><tr><th>Ref close</th><th>Horizon</th><th>Cut points</th><th>Bear / base / bull</th><th>History</th></tr>%s</table></div></section>' % "".join(
            '<tr><td class="n">%s</td><td>%s</td><td class="n">%+.2f / %+.2f</td><td class="n">%s / %s / %s</td><td class="n muted">%s</td></tr>' % (
                e(x["ref_date"]), H_LABEL[x["horizon"]], x["lower_pct"], x["upper_pct"], e(x["probs"]["bear"]), e(x["probs"]["base"]), e(x["probs"]["bull"]),
                "%s / %s / %s" % (x["history_probs"]["bear"], x["history_probs"]["base"], x["history_probs"]["bull"]) if x.get("history_probs") else "–")
            for x in sorted(opn, key=lambda x: x["ref_date"], reverse=True)))
    return "".join(out)


def build(data_dir, site_dir):
    data_dir, site_dir = Path(data_dir), Path(site_dir)
    (site_dir / "b").mkdir(parents=True, exist_ok=True)
    briefs = []
    for f in sorted((data_dir / "briefs").glob("*.json")) if (data_dir / "briefs").exists() else []:
        try:
            briefs.append(json.loads(f.read_text()))
        except Exception:
            continue
    briefs.sort(key=lambda b: b.get("made_utc", ""))
    st = json.loads((data_dir / "latest_status.json").read_text()) if (data_dir / "latest_status.json").exists() else {}
    ledger = json.loads((data_dir / "forecasts.json").read_text()) if (data_dir / "forecasts.json").exists() else []
    status_html, n_ok, n_all = render_status(st) if st else ("", 0, 0)
    latest = briefs[-1] if briefs else None
    import os, re as _re
    def _scrub(h):
        for n in ("ANTHROPIC_API_KEY", "FRED_API_KEY", "BLS_API_KEY", "CONTACT_EMAIL", "DISCORD_WEBHOOK_URL", "ALPHAVANTAGE_API_KEY", "EIA_API_KEY"):
            v = os.environ.get(n, "").strip()
            if len(v) >= 6:
                h = h.replace(html.escape(v), "[removed]").replace(v, "[removed]")
        h = _re.sub(r"https://(?:\w+\.)?discord(?:app)?\.com/api/webhooks/\S+", "[removed]", h)
        return _re.sub(r"sk-ant-[A-Za-z0-9_\-]{8,}", "[key removed]", h)
    _orig_write = Path.write_text
    def _w(self, data, *a, **k):
        return _orig_write(self, _scrub(data), *a, **k)
    Path.write_text = _w
    try:
        _build_pages(site_dir, briefs, st, ledger, status_html, n_ok, n_all, latest)
    finally:
        Path.write_text = _orig_write
    return len(briefs)


def _build_pages(site_dir, briefs, st, ledger, status_html, n_ok, n_all, latest):
    import minimal
    if latest:
        title = "Context Engine · " + datetime.fromisoformat(latest["made_utc"]).astimezone(VIENNA).strftime("%A %d %B %Y")
        (site_dir / "index.html").write_text(minimal.page(title, minimal.render(latest, st)))
    else:
        (site_dir / "index.html").write_text(minimal.page("Context Engine", "<h1>No brief yet</h1>"))
    (site_dir / "sources.html").write_text(page("Sources and data", status_html or "<p>No data yet.</p>", "latest"))
    (site_dir / "record.html").write_text(page("Forecast record", render_record(ledger), "record"))
    rows = "".join('<tr><td class="n"><a href="b/%s.html">%s</a></td><td>%s</td><td>%s</td><td class="small muted">%s · %s</td></tr>' % (
        e(b["id"]), e(b["id"]), e(b.get("slot_label")), e(b.get("headline")), e(b.get("dominant_driver")), e(b.get("leader")))
        for b in reversed(briefs))
    (site_dir / "archive.html").write_text(page("Archive", '<section class="panel"><h2>Every brief</h2><div class="scroll"><table><tr><th>Brief</th><th>Run</th><th>Headline</th><th>Driver · leader</th></tr>%s</table></div></section>' % (
        rows or '<tr><td colspan="4" class="muted">none yet</td></tr>'), "archive"))
    for b in briefs:
        t = "Context Engine · " + datetime.fromisoformat(b["made_utc"]).astimezone(VIENNA).strftime("%A %d %B %Y")
        (site_dir / "b" / ("%s.html" % b["id"])).write_text(minimal.page(t, minimal.render(b, None, "../")))
    (site_dir / ".nojekyll").write_text("")
    return len(briefs)
