"""
Hyperminimal brief page: one quiet column, black page, white type, numbers in mono.
Used for the main page (latest brief) and for each brief in the archive.
"""
import html
from datetime import datetime
from zoneinfo import ZoneInfo

CET = ZoneInfo("Europe/Vienna")


def e(x):
    return html.escape("" if x is None else str(x))


CSS = """
:root{--bg:#000;--fg:#f2f2f0;--mid:#9a9a96;--dim:#5e5e5b;--line:#1e1e1d;--down:#e8a3a0;--up:#a9d8b8;--base:#3a3a38;
--sans:"Inter",-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;color-scheme:dark}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 var(--sans)}
a{color:inherit;text-decoration-color:var(--dim);text-underline-offset:3px}
main{max-width:680px;margin:0 auto;padding-block:44px 110px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:44px}
.top{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font:500 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.top nav{display:flex;gap:14px}.top nav a{text-decoration:none}.top nav a:hover{color:var(--fg)}
h1{font-size:26px;line-height:1.25;font-weight:600;letter-spacing:-.015em;margin:10px 0 0;text-wrap:balance}
h2{font:500 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--dim);margin:0 0 12px}
p{margin:0}p+p{margin-top:10px}.lead{font-size:16.5px}.mid{color:var(--mid)}
section{min-width:0}
.nums{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:22px 16px}
.nums b{display:block;font:500 20px/1.2 var(--mono);font-variant-numeric:tabular-nums}
.nums span{display:block;font-size:12px;color:var(--mid);margin-top:3px}
.nums i{font-style:normal;font:400 12px var(--mono)}
.down{color:var(--down)}.up{color:var(--up)}
.driver{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.driver strong{display:block;font-size:18px;font-weight:600;margin-bottom:6px}
dl{display:grid;grid-template-columns:110px 1fr;gap:10px 18px;margin:0}dt{color:var(--dim);font-size:13px;padding-top:1px}dd{margin:0;min-width:0}
.chartbox{overflow-x:auto}.chartbox svg{display:block;width:100%;min-width:520px;height:auto}
.ch .ln{fill:none;stroke:var(--fg);stroke-width:1.5;stroke-linejoin:round}.ch .ref{stroke:var(--line);stroke-width:1}
.ch .dash{stroke:var(--dim);stroke-width:1;stroke-dasharray:2 3}.ch .pt{fill:var(--mid)}.ch .now{fill:var(--fg);stroke:var(--bg);stroke-width:2}
.ch .zu{fill:var(--up);opacity:.8}.ch .zn{fill:var(--base)}.ch .zb{fill:var(--down);opacity:.8}
.ch .fb{fill:var(--down);opacity:.16}.ch .fu{fill:var(--up);opacity:.16}.ch .fn{fill:var(--base);opacity:.55}.ch .edge{fill:none;stroke:var(--dim);stroke-width:1;stroke-dasharray:3 4}.ch .tick{stroke:var(--line);stroke-width:1}.ch .lb{fill:none;stroke:var(--down);stroke-width:1.4;opacity:.45;filter:blur(.6px)}.ch .lu{fill:none;stroke:var(--up);stroke-width:1.4;opacity:.45;filter:blur(.6px)}.why{font-size:14.5px;margin-top:14px}.ch .cu{fill:var(--up)}.ch .cb{fill:var(--down)}
.ch .lab{fill:var(--dim);font:400 10.5px var(--mono)}.ch .pu{fill:var(--up);font:500 11px var(--mono)}.ch .pn{fill:var(--mid);font:500 11px var(--mono)}.ch .pb{fill:var(--down);font:500 11px var(--mono)}
.note{font-size:12.5px;color:var(--dim);margin-top:14px}
.hz{border-top:1px solid var(--line)}.hz:last-of-type{border-bottom:1px solid var(--line)}
.hz summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:104px 1fr;grid-template-areas:"hl strip" ". hist" ". cuts";column-gap:18px;padding:18px 0 14px}
.hz summary::-webkit-details-marker{display:none}.hz summary:focus-visible{outline:1px solid var(--mid);outline-offset:4px}
.hl{grid-area:hl;font-size:14px;font-weight:500;align-self:center}.hl::after{content:"+";color:var(--dim);font:400 13px var(--mono);margin-left:8px}.hz[open] .hl::after{content:"\\2212"}
.strip,.hist{display:flex;gap:2px}.strip{grid-area:strip;height:22px}
.strip i{font:500 11px/22px var(--mono);font-style:normal;color:#000;text-align:center;min-width:0;overflow:hidden;font-variant-numeric:tabular-nums}
.hist{grid-area:hist;height:2px;margin-top:5px;opacity:.55}
.b{--c:var(--down)}.n{--c:var(--base)}.u{--c:var(--up)}
.strip i,.hist i{background:var(--c)}.strip i.n{color:var(--fg)}
.cuts{grid-area:cuts;position:relative;height:16px;margin-top:4px}
.cuts em{position:absolute;transform:translateX(-50%);font:400 11px var(--mono);font-style:normal;color:var(--dim);white-space:nowrap}
.if{list-style:none;margin:0;padding:0 0 18px 122px;display:grid;gap:12px}
.if li{border-left:2px solid var(--c);padding-left:12px}.if p{font-size:14px}.if small{display:block;font-size:12.5px;color:var(--dim);margin-top:2px}
.cal{display:grid;gap:8px}.cal div{display:grid;grid-template-columns:130px 1fr;gap:18px}
.cal time{font:400 13px var(--mono);color:var(--mid);font-variant-numeric:tabular-nums}
ul{margin:0;padding-left:18px;display:grid;gap:4px}
footer{font-size:12px;color:var(--dim);border-top:1px solid var(--line);padding-top:16px;display:grid;gap:6px}
@media(max-width:560px){.nums{grid-template-columns:repeat(2,minmax(0,1fr))}.driver{grid-template-columns:1fr}
dl,.cal div{grid-template-columns:1fr;gap:2px}dd{margin-bottom:10px}h1{font-size:22px}
.hz summary{grid-template-columns:1fr;grid-template-areas:"hl" "strip" "hist" "cuts";row-gap:8px}.hist{margin-top:0}.if{padding-left:0}}
"""

LIQUID_CSS = 'html.liquid{--glass:rgba(255,255,255,.055);--glass-hi:rgba(255,255,255,.16);--line:rgba(255,255,255,.09)}html.liquid body{background:#000;min-height:100vh;overflow-x:hidden}html.liquid .aura{position:fixed;inset:-20vmax;z-index:0;pointer-events:none;filter:blur(60px);opacity:.55}html.liquid .aura i{position:absolute;border-radius:50%;mix-blend-mode:screen;will-change:transform}html.liquid .aura i:nth-child(1){width:55vmax;height:55vmax;left:5%;top:0;background:radial-gradient(circle,#d8dce2 0,rgba(140,146,156,.5) 30%,transparent 62%);animation:f1 26s ease-in-out infinite alternate}html.liquid .aura i:nth-child(2){width:50vmax;height:50vmax;right:0;top:20%;background:radial-gradient(circle,#9aa0a8 0,rgba(90,94,102,.45) 35%,transparent 60%);animation:f2 31s ease-in-out infinite alternate}html.liquid .aura i:nth-child(3){width:45vmax;height:45vmax;left:25%;bottom:0;background:radial-gradient(circle,#c4c8ce 0,rgba(110,114,122,.4) 35%,transparent 60%);animation:f3 23s ease-in-out infinite alternate}html.liquid .aura i:nth-child(4){width:35vmax;height:35vmax;right:20%;bottom:15%;background:conic-gradient(from 0deg,#f4f5f7,#6d7178,#e2e4e8,#4a4d52,#f4f5f7);opacity:.35;animation:f1 37s ease-in-out infinite alternate-reverse}@keyframes f1{to{transform:translate(18vmax,22vmax) scale(1.15)}}@keyframes f2{to{transform:translate(-22vmax,14vmax) scale(.9)}}@keyframes f3{to{transform:translate(12vmax,-20vmax) scale(1.2)}}html.liquid .grain{position:fixed;inset:0;z-index:0;pointer-events:none;background:radial-gradient(ellipse at 50% 30%,rgba(0,0,0,.35),rgba(0,0,0,.8) 75%)}html.liquid main>section{background-image:linear-gradient(115deg,transparent 35%,rgba(235,238,242,.07) 48%,transparent 60%);background-size:250% 100%;animation:sheen 9s ease-in-out infinite}@keyframes sheen{0%{background-position:120% 0}55%,100%{background-position:-60% 0}}@media (prefers-reduced-motion:reduce){html.liquid main>section{animation:none}}html.liquid main{position:relative;z-index:1;gap:18px}html.liquid main>section,html.liquid main>footer{position:relative;background:var(--glass);border:1px solid rgba(255,255,255,.1);border-radius:26px;padding:24px 26px;\n backdrop-filter:blur(28px) saturate(170%);-webkit-backdrop-filter:blur(28px) saturate(170%);\n box-shadow:inset 0 1px 0 var(--glass-hi),inset 0 -1px 0 rgba(255,255,255,.03),0 20px 50px -20px rgba(0,0,0,.6);overflow:hidden;\n transition:transform .5s cubic-bezier(.2,.8,.2,1),background .4s}html.liquid main>section::before{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;\n background:radial-gradient(600px circle at var(--mx,50%) var(--my,-20%),rgba(255,255,255,.10),transparent 40%)}html.liquid main>section:hover{background:rgba(255,255,255,.075)}html.liquid main h1{font-size:34px;letter-spacing:-.03em;background:linear-gradient(180deg,#fff 30%,rgba(255,255,255,.62));-webkit-background-clip:text;background-clip:text;color:transparent}html.liquid main>footer{border-radius:20px;font-size:12px}html.liquid .nums>div{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:12px 14px}html.liquid .strip{border-radius:999px;overflow:hidden}html.liquid .strip i{backdrop-filter:blur(6px)}html.liquid .hz{border-color:rgba(255,255,255,.08)!important}html.liquid .chartbox svg{filter:drop-shadow(0 0 8px rgba(255,255,255,.25))}@media (max-width:560px){html.liquid main>section,html.liquid main>footer{padding:18px;border-radius:22px}html.liquid main h1{font-size:26px}}@media (prefers-reduced-motion:reduce){html.liquid .aura i{animation:none}}html:not(.liquid) .aura,html:not(.liquid) .grain{display:none}.tgl{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.28);border-radius:999px;padding:3px 11px;margin:-4px 0;color:var(--fg);font:inherit;font-weight:600;letter-spacing:inherit;text-transform:inherit;cursor:pointer;transition:background .2s,border-color .2s}.tgl:hover{background:rgba(255,255,255,.14);border-color:rgba(255,255,255,.5)}.tgl:focus-visible{outline:1px solid var(--fg);outline-offset:3px}'

THEMES_CSS = 'html.terminal{--bg:#050403;--fg:#ffb547;--mid:#c98a2e;--dim:#7a5a24;--line:#2a1f0e;--down:#ff5b4a;--up:#7dff9a;--base:#3a2c14;--sans:"IBM Plex Mono",ui-monospace,monospace}\nhtml.terminal body{background:var(--bg);text-shadow:0 0 6px rgba(255,181,71,.25)}\nhtml.terminal body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:5;background:repeating-linear-gradient(0deg,rgba(0,0,0,.18) 0 1px,transparent 1px 3px)}\nhtml.terminal h1{font-weight:500;text-transform:uppercase;letter-spacing:.02em;font-size:22px}\nhtml.terminal h1::before{content:"> ";color:var(--dim)}\nhtml.terminal main>section{border-top:1px dashed var(--line);padding-top:18px}\nhtml.terminal .strip i{color:#050403}\nhtml.terminal .ch .ln{stroke:var(--fg)}\nhtml.terminal .tgl,html.paper .tgl{border-color:currentColor;background:transparent;color:var(--fg)}\nhtml.paper{--bg:#f3eee4;--fg:#16140f;--mid:#4a463d;--dim:#8a8476;--line:#d9d1c1;--down:#b3372b;--up:#2f7a4a;--base:#d3cab8;color-scheme:light}\nhtml.paper body{background:var(--bg)}\nhtml.paper h1{font-family:"Newsreader",Georgia,serif;font-weight:500;font-size:34px;letter-spacing:-.01em}\nhtml.paper .lead{font-family:"Newsreader",Georgia,serif;font-size:19px;line-height:1.5}\nhtml.paper .driver strong{font-family:"Newsreader",Georgia,serif;font-size:21px;font-weight:500}\nhtml.paper main>section{border-top:1px solid var(--fg);padding-top:14px}\nhtml.paper .strip i{color:#fff}html.paper .strip i.n{color:var(--fg)}\nhtml.paper .ch .now{stroke:var(--bg)}\n'

PICKER_CSS = '.picker{position:fixed;left:50%;bottom:max(16px,env(safe-area-inset-bottom,0px));transform:translateX(-50%);z-index:10;display:flex;gap:4px;padding:5px;border-radius:999px;background:rgba(20,20,20,.75);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border:1px solid rgba(255,255,255,.15);font:500 12px "IBM Plex Mono",ui-monospace,monospace;box-shadow:0 8px 30px rgba(0,0,0,.35)}.picker button{border:0;background:none;color:#ddd;padding:7px 12px;border-radius:999px;cursor:pointer;font:inherit;text-shadow:none}.picker button:hover{color:#fff}.picker button[aria-pressed=true]{background:#f2f2f0;color:#000}.picker button:focus-visible{outline:1px solid #fff;outline-offset:2px}'

H_NAME = {"next_day": "Next session", "next_week": "Next week", "next_month": "Next month"}


def page(title, body, prefix=""):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="noindex">'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
            '<title>%s</title><style>%s%s</style>'
            '<script>try{var t=localStorage.getItem("ce-theme");if(t&&t!=="minimal")document.documentElement.classList.add(t)}catch(e){}</script>'
            '</head><body><div class="aura" aria-hidden="true"><i></i><i></i><i></i><i></i></div><div class="grain" aria-hidden="true"></div><main>%s</main>'
            '<div class="picker" role="group" aria-label="Theme"><button data-t="minimal">Minimal</button><button data-t="liquid">Liquid</button><button data-t="terminal">Terminal</button><button data-t="paper">Paper</button></div>'
            '<script>(function(){var r=document.documentElement,bs=document.querySelectorAll(".picker button");'
            'function cur(){var c=["liquid","terminal","paper"];for(var i=0;i<c.length;i++)if(r.classList.contains(c[i]))return c[i];return "minimal"}'
            'function mark(){var c=cur();bs.forEach(function(b){b.setAttribute("aria-pressed",b.dataset.t===c)})}mark();'
            'bs.forEach(function(b){b.onclick=function(){r.classList.remove("liquid","terminal","paper");if(b.dataset.t!=="minimal")r.classList.add(b.dataset.t);try{localStorage.setItem("ce-theme",b.dataset.t)}catch(e){}mark()}});'
            'document.querySelectorAll("main>section").forEach(function(el){el.addEventListener("pointermove",function(ev){var q=el.getBoundingClientRect();el.style.setProperty("--mx",ev.clientX-q.left+"px");el.style.setProperty("--my",ev.clientY-q.top+"px")})})})()</script>'
            '</body></html>') % (e(title), CSS, LIQUID_CSS + THEMES_CSS + PICKER_CSS, body)


def _fmt(v, dec=2):
    if isinstance(v, (int, float)):
        if abs(v) >= 1000:
            return "{:,.1f}".format(v) if dec else "{:,.0f}".format(v)
        return ("%." + str(dec) + "f") % v
    return e(v)


def _fact(facts, source=None, label_has=None):
    for f in facts or []:
        if source and f["source"] != source:
            continue
        if label_has and label_has.lower() not in f["label"].lower():
            continue
        return f
    return None


def key_numbers(facts):
    """Eight numbers that matter before the open, chosen in a fixed order from what the run has."""
    out = []

    def add(f, label, dec=2, pct=False, invert=False):
        if not f:
            return
        ch = f.get("change") or ""
        cls = ""
        if ch.startswith("+"):
            cls = "down" if invert else "up"
        elif ch.startswith("-") or ch.startswith("−"):
            cls = "up" if invert else "down"
        val = _fmt(f["value"], dec) + ("%" if pct else "")
        out.append((val, label, ch.replace("-", "−"), cls))
    add(_fact(facts, "FRED NASDAQ100"), "Nasdaq-100", 1)
    add(_fact(facts, "Cboe VIX") or _fact(facts, "FRED VIXCLS"), "VIX", 2, invert=True)
    add(_fact(facts, "Cboe VXN") or _fact(facts, "FRED VXNCLS"), "VXN", 2, invert=True)
    add(_fact(facts, "US Treasury", "10-year") or _fact(facts, "FRED DGS10"), "10-year", 2, pct=True, invert=True)
    odds = [f for f in (facts or []) if f["group"] == "Fed odds" and "decision" in f["label"].lower()]
    if odds:
        top = max(odds, key=lambda f: f["value"] if isinstance(f["value"], (int, float)) else 0)
        out.append((_fmt(top["value"], 1) + "%", "Fed: " + top["label"].split(":", 1)[-1].strip()[:22], "", ""))
    add(_fact(facts, "FRED PCEPILFE", "y/y"), "Core PCE y/y", 2, pct=True)
    add(_fact(facts, "Cboe COR1M"), "COR1M", 2)
    add(_fact(facts, "computed from FRED", "last 5 sessions"), "NDX vs SPX, 5 days", 2)
    return out[:8]


def chart(closes, outlook, ref_note):
    """Last closes as a line, plus next session's bear/base/bull band in index points from the last close."""
    if not closes or len(closes) < 5:
        return ""
    o = (outlook or {}).get("next_day") or {}
    p = o.get("probs_normalized") or {}
    last = closes[-1][1]
    lo_pct, up_pct = o.get("lower_pct"), o.get("upper_pct")
    has_band = isinstance(lo_pct, (int, float)) and isinstance(up_pct, (int, float))
    lo = last * (1 + lo_pct / 100) if has_band else last
    up = last * (1 + up_pct / 100) if has_band else last
    W, H, L, R, T, B = 680, 230, 8, 120, 14, 26
    n = len(closes)
    slot = (W - L - R) / n
    vals = [v for _, v in closes] + [lo, up]
    pad = (max(vals) - min(vals)) * 0.08 or 1
    ymin, ymax = min(vals) - pad, max(vals) + pad
    X = lambda i: L + i * slot
    Y = lambda v: T + (ymax - v) / (ymax - ymin) * (H - T - B)
    path = "M" + " L".join("%.1f %.1f" % (X(i), Y(v)) for i, (_, v) in enumerate(closes))
    hi = max(range(n), key=lambda i: closes[i][1])
    lw = min(range(n), key=lambda i: closes[i][1])
    xl, xn, bw, ext = X(n - 1), X(n), 14, 26
    d0 = datetime.fromisoformat(closes[0][0]).strftime("%-d %b")
    d1 = datetime.fromisoformat(closes[-1][0]).strftime("%-d %b")
    parts = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Nasdaq-100 closes %s to %s%s">' % (
        W, H, d0, d1, ", next session bear below %s, bull above %s" % (_fmt(lo, 0), _fmt(up, 0)) if has_band else ""),
        '<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="ref"/>' % (L, W - R + 30, Y(last), Y(last)),
        '<path d="%s" class="ln"/>' % path,
        '<circle cx="%.1f" cy="%.1f" r="2" class="pt"/><text x="%.1f" y="%.1f" class="lab" text-anchor="middle">%s</text>' % (X(hi), Y(closes[hi][1]), X(hi), Y(closes[hi][1]) - 7, _fmt(closes[hi][1], 0)),
        '<circle cx="%.1f" cy="%.1f" r="2" class="pt"/><text x="%.1f" y="%.1f" class="lab" text-anchor="middle">%s</text>' % (X(lw), Y(closes[lw][1]), X(lw), Y(closes[lw][1]) + 15, _fmt(closes[lw][1], 0))]
    if has_band:
        yu, yl = Y(up), Y(lo)
        parts += ['<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" class="dash"/>' % (xl, xn - bw / 2, Y(last), Y(last)),
                  '<rect x="%.1f" y="%.1f" width="%d" height="%d" class="zu"/>' % (xn - bw / 2, yu - ext, bw, ext),
                  '<rect x="%.1f" y="%.1f" width="%d" height="%.1f" class="zn"/>' % (xn - bw / 2, yu, bw, max(1, yl - yu)),
                  '<rect x="%.1f" y="%.1f" width="%d" height="%d" class="zb"/>' % (xn - bw / 2, yl, bw, ext),
                  '<text x="%.1f" y="%.1f" class="pu">%s%%</text>' % (xn + bw / 2 + 8, yu - ext / 2 + 4, _fmt(p.get("bull"), 0)),
                  '<text x="%.1f" y="%.1f" class="pn">%s%%</text>' % (xn + bw / 2 + 8, (yu + yl) / 2 + 4, _fmt(p.get("base"), 0)),
                  '<text x="%.1f" y="%.1f" class="pb">%s%%</text>' % (xn + bw / 2 + 8, yl + ext / 2 + 4, _fmt(p.get("bear"), 0)),
                  '<text x="%.1f" y="%.1f" class="lab">%s</text>' % (xn + bw / 2 + 44, yu + 4, _fmt(up, 0)),
                  '<text x="%.1f" y="%.1f" class="lab">%s</text>' % (xn + bw / 2 + 44, yl + 4, _fmt(lo, 0))]
    parts += ['<circle cx="%.1f" cy="%.1f" r="3.5" class="now"/>' % (xl, Y(last)),
              '<text x="%d" y="%d" class="lab">%s</text>' % (L, H - 6, d0),
              '<text x="%.1f" y="%d" class="lab" text-anchor="end">%s</text>' % (xl - 4, H - 6, d1),
              '<text x="%.1f" y="%d" class="lab" text-anchor="middle">next</text>' % (xn, H - 6) if has_band else "", "</svg>"]
    note = ("White line: daily closes. The bar on the right is the next session measured from the %s close: red below %s, grey between, "
            "green above %s, with the engine's odds beside each part.%s" % (d1, _fmt(lo, 0), _fmt(up, 0), ref_note)) if has_band else "White line: daily closes."
    return ('<section class="ch"><h2>Nasdaq-100 · last %d sessions%s</h2><div class="chartbox">%s</div><p class="note">%s</p></section>'
            % (n, " and the next session's range" if has_band else "", "".join(parts), note))


def _inv(t):
    t = (t or "").strip().rstrip(".")
    for pre in ("Invalid if ", "invalid if ", "Invalidated if ", "If "):
        if t.startswith(pre):
            t = t[len(pre):]
    return (t[:1].lower() + t[1:] if t[:2] != t[:2].upper() else t) + "."


def fan(closes, outlook, rates, ref_date, run_day="", why=""):
    """Outlook fan: last 10 closes, then the engine's bear/base/bull zones at 1, 5 and 21 sessions, in index points.
    Faint dashed edge: historical 10th to 90th percentile move in the same VIX range."""
    hz = [("next_day", 1, "Next session"), ("next_week", 5, "1 week"), ("next_month", 21, "1 month")]
    out = (outlook or {})
    hz = [(h, k, lab) for h, k, lab in hz if isinstance((out.get(h) or {}).get("lower_pct"), (int, float))]
    if not closes or len(closes) < 3 or not hz:
        return ""
    hist = closes[-10:]
    last = hist[-1][1]
    rh = ((rates or {}).get("horizons") or {})
    q = {h: (rh.get(h) or {}).get("same_regime") or {} for h, _, _ in hz}
    W, H, L, R, T, B = 680, 300, 8, 96, 18, 28
    xh = 150  # width of the history stub
    x0 = L + xh
    wf = W - R - x0
    X = lambda k: x0 + wf * (k / 21) ** 0.5
    pts = []
    for h, k, _ in hz:
        o = out[h]
        pts.append((k, o["lower_pct"], o["upper_pct"], q[h].get("p10", o["lower_pct"]), q[h].get("p90", o["upper_pct"])))
    lv = [v for _, v in hist] + [last * (1 + min(a, c) / 100) for _, a, b, c, d in pts] + [last * (1 + max(b, d) / 100) for _, a, b, c, d in pts]
    pad = (max(lv) - min(lv)) * 0.06
    ymin, ymax = min(lv) - pad, max(lv) + pad
    Y = lambda pct: T + (ymax - last * (1 + pct / 100)) / (ymax - ymin) * (H - T - B)
    Yv = lambda v: T + (ymax - v) / (ymax - ymin) * (H - T - B)
    poly = lambda top, bot: " ".join("%.1f,%.1f" % (X(k), Y(v)) for k, v in top) + " " + " ".join("%.1f,%.1f" % (X(k), Y(v)) for k, v in reversed(bot))
    lower = [(0, 0)] + [(k, a) for k, a, b, c, d in pts]
    upper = [(0, 0)] + [(k, b) for k, a, b, c, d in pts]
    p10 = [(0, 0)] + [(k, min(c, a)) for k, a, b, c, d in pts]
    p90 = [(0, 0)] + [(k, max(d, b)) for k, a, b, c, d in pts]
    sh = (xh - 10) / max(1, len(hist) - 1)
    hp = "M" + " L".join("%.1f %.1f" % (L + i * sh, Yv(v)) for i, (_, v) in enumerate(hist))
    g = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Outlook fan for the Nasdaq-100 from the %s close">' % (W, H, e(ref_date)),
         '<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="ref"/>' % (L, W - R, Yv(last), Yv(last)),
         '<polygon points="%s" class="fb"/>' % poly(lower, p10),
         '<polygon points="%s" class="fu"/>' % poly(p90, upper),
         '<polygon points="%s" class="fn"/>' % poly(upper, lower),
         '<polyline points="%s" class="lb"/>' % " ".join("%.1f,%.1f" % (X(k), Y(v)) for k, v in lower),
         '<polyline points="%s" class="lu"/>' % " ".join("%.1f,%.1f" % (X(k), Y(v)) for k, v in upper),
         '<polyline points="%s" class="edge"/>' % " ".join("%.1f,%.1f" % (X(k), Y(v)) for k, v in p10),
         '<polyline points="%s" class="edge"/>' % " ".join("%.1f,%.1f" % (X(k), Y(v)) for k, v in p90),
         '<path d="%s" class="ln"/>' % hp]
    for (h, k, lab), (_, a, b, c, d) in zip(hz, pts):
        x = X(k)
        pr = out[h].get("probs_normalized") or {}
        g.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" class="tick"/>' % (x, x, T, H - B))
        g.append('<text x="%.1f" y="%d" class="lab" text-anchor="middle">%s</text>' % (x, H - 8, lab))
        g.append('<text x="%.1f" y="%.1f" class="pu" text-anchor="%s">%s%%</text>' % (x - (8 if k == 21 else 0), Y(b) - 6, "end" if k == 21 else "middle", _fmt(pr.get("bull"), 0)))
        g.append('<text x="%.1f" y="%.1f" class="pb" text-anchor="%s">%s%%</text>' % (x - (8 if k == 21 else 0), Y(a) + 14, "end" if k == 21 else "middle", _fmt(pr.get("bear"), 0)))
        g.append('<circle cx="%.1f" cy="%.1f" r="2.5" class="cu"/><circle cx="%.1f" cy="%.1f" r="2.5" class="cb"/>' % (x, Y(b), x, Y(a)))
    k, a, b, c, d = pts[-1]
    xr = X(k) + 10
    g += ['<text x="%.1f" y="%.1f" class="lab">%s</text>' % (xr, Y(b) + 4, _fmt(last * (1 + b / 100), 0)),
          '<text x="%.1f" y="%.1f" class="lab">%s</text>' % (xr, Y(a) + 4, _fmt(last * (1 + a / 100), 0)),
          '<text x="%.1f" y="%.1f" class="pn">%s%%</text>' % (xr, (Y(a) + Y(b)) / 2 + 4, _fmt((out[hz[-1][0]].get("probs_normalized") or {}).get("base"), 0)),
          '<circle cx="%.1f" cy="%.1f" r="3.5" class="now"/>' % (x0, Yv(last)),
          '<text x="%.1f" y="%.1f" class="lab" text-anchor="middle">%s</text>' % (x0, Yv(last) + 18, _fmt(last, 0)),
          '<text x="%.1f" y="%.1f" class="lab" text-anchor="middle">%s close</text>' % (x0, Yv(last) + 31, datetime.fromisoformat(hist[-1][0]).strftime("%-d %b")),
          '<text x="%d" y="%d" class="lab">%s</text>' % (L, H - 8, datetime.fromisoformat(hist[0][0]).strftime("%-d %b")),
          "</svg>"]
    first = out[hz[0][0]]
    note = ("Grey: the engine's base case. Red and green: bear and bull, with their odds. Dashed edge: how far the Nasdaq-100 moved 8 times out of 10 "
            "over the same horizon when VIX was in the same range. Measured from the %s close of %s. Same percentages apply to QQQ and NQ. "
            "Next session: bear below %s, bull above %s." % (e(ref_date), _fmt(last, 0), _fmt(last * (1 + first["lower_pct"] / 100), 0), _fmt(last * (1 + first["upper_pct"] / 100), 0)))
    return '<section class="ch"><h2>Outlook fan · Nasdaq-100%s</h2><div class="chartbox">%s</div>%s<p class="note">%s</p></section>' % (" · " + e(run_day) + " run" if run_day else "", "".join(g), '<p class="why">%s</p>' % e(why) if why else "", note)


def outlook_html(b):
    out = []
    order = [("next_day", True), ("next_week", False), ("next_month", False)]
    for h, open_ in order:
        o = (b.get("outlook") or {}).get(h)
        if not o or not isinstance(o.get("lower_pct"), (int, float)):
            continue
        p = o.get("probs_normalized") or {s.get("name"): s.get("prob") for s in o.get("scenarios", [])}
        hp = o.get("history_probs") or {}
        sc = {s.get("name"): s for s in o.get("scenarios", [])}
        pb, pn, pu = (float(p.get(k) or 0) for k in ("bear", "base", "bull"))
        strip = "".join('<i class="%s" style="flex:%s">%s</i>' % (c, v, _fmt(v, 0) if v >= 8 else "") for c, v in (("b", pb), ("n", pn), ("u", pu)))
        hist = ""
        if hp:
            hist = '<span class="hist" aria-label="History %s%%, %s%%, %s%%">%s</span>' % (
                _fmt(hp.get("bear"), 0), _fmt(hp.get("base"), 0), _fmt(hp.get("bull"), 0),
                "".join('<i class="%s" style="flex:%s"></i>' % (c, hp.get(k) or 0) for c, k in (("b", "bear"), ("n", "base"), ("u", "bull"))))
        tot = pb + pn + pu or 1
        cuts = '<span class="cuts"><em style="left:%.0f%%">%+.1f%%</em><em style="left:%.0f%%">%+.1f%%</em></span>' % (
            pb / tot * 100, o["lower_pct"], (pb + pn) / tot * 100, o["upper_pct"])
        items = "".join('<li class="%s"><p>%s</p><small>Off if %s</small></li>' % (
            c, e((sc.get(k) or {}).get("text")), e(_inv((sc.get(k) or {}).get("invalidation"))))
            for c, k in (("b", "bear"), ("n", "base"), ("u", "bull")) if sc.get(k))
        out.append('<details class="hz"%s><summary><span class="hl">%s</span><span class="strip" aria-label="Bear %s%%, base %s%%, bull %s%%">%s</span>%s%s</summary><ol class="if">%s</ol></details>' % (
            " open" if open_ else "", H_NAME[h], _fmt(pb, 0), _fmt(pn, 0), _fmt(pu, 0), strip, hist, cuts, items))
    if not out:
        return ""
    return ('<section class="outlook"><h2>Outlook · Nasdaq-100 from the %s close</h2>%s<p class="note">Thick line: the engine\'s odds for bear, base and bull. '
            'Thin line: how often each happened historically with VIX in the same range. Tap a horizon for the conditions.</p></section>' % (e(b.get("ref_date")), "".join(out)))


def coming_up(b, st):
    rows = [(x.get("when_vienna", ""), x.get("event", "")) for x in (b.get("scheduled_events") or [])][:5]
    for x in (st or {}).get("earnings") or []:
        if len(rows) >= 7:
            break
        rows.append((x["day"], "%s earnings%s" % (x["ticker"], ", " + x["timing"] if x.get("timing") else "")))
    if not rows:
        return ""
    return '<section><h2>Coming up · CET</h2><div class="cal">%s</div></section>' % "".join(
        '<div><time>%s</time><span>%s</span></div>' % (e(w), e(ev)) for w, ev in rows)


def render(b, st=None, prefix=""):
    w = b.get("what_happened") or {}
    made = datetime.fromisoformat(b["made_utc"]).astimezone(CET)
    nav = "".join('<a href="%s%s">%s</a>' % (prefix, href, lab) for href, lab in (("record.html", "Record"), ("archive.html", "Archive"), ("sources.html", "Sources")))
    parts = ['<div><div class="top"><span>%s</span><nav>%s</nav></div><h1>%s</h1></div>' % (made.strftime("%A %d %B %Y"), nav, e(b.get("headline")))]
    summ = (w.get("summary") or "").strip()
    first, _, rest = summ.partition(". ")
    parts.append('<section><h2>What happened</h2><p class="lead">%s</p>%s</section>' % (
        e(first + ("." if rest else "")), '<p class="mid">%s</p>' % e(rest) if rest else ""))
    if st:
        nums = key_numbers(st.get("facts"))
        if nums:
            parts.append('<section class="nums" aria-label="Key numbers">%s</section>' % "".join(
                '<div><b>%s</b><span>%s%s</span></div>' % (e(v), e(lab), ' <i class="%s">%s</i>' % (cls, e(ch)) if ch else "") for v, lab, ch, cls in nums))
    parts.append('<section class="driver"><div><h2>Dominant driver</h2><strong>%s</strong><p class="mid">%s</p></div>'
                 '<div><h2>Leader</h2><strong>%s</strong><p class="mid">%s</p></div></section>' % (
                     e((b.get("dominant_driver") or "").capitalize()), e(b.get("driver_reason")), e(b.get("leader")), e(b.get("leader_reason"))))
    rows = [(lab, w.get(k)) for k, lab in (("market_action", "Market"), ("macro", "Rates and macro"), ("geopolitics", "Geopolitics"), ("company_news", "Companies")) if w.get(k)]
    unc = b.get("unconfirmed") or []
    if unc:
        rows.append(("Unconfirmed", "; ".join(unc)))
    parts.append('<section><h2>Detail</h2><dl>%s</dl></section>' % "".join('<dt>%s</dt><dd>%s</dd>' % (e(a), e(c)) for a, c in rows))
    if st and st.get("ndx_recent"):
        ref = b.get("ref_date")
        last_d = st["ndx_recent"][-1][0]
        note = "" if not ref or ref == last_d else " The data's latest close is %s; the scenarios are measured from the %s close." % (last_d, ref)
        parts.append(fan(st["ndx_recent"], b.get("outlook"), st.get("rates"), ref, made.strftime("%-d %b"), b.get("fan_reason") or ((b.get("outlook") or {}).get("next_week") or {}).get("confidence_reason", "")))
    parts.append(outlook_html(b))
    parts.append(coming_up(b, st))
    wl = b.get("watch_list") or []
    if wl:
        parts.append('<section><h2>Watch</h2><ul>%s</ul></section>' % "".join("<li>%s</li>" % e(x) for x in wl[:4]))
    srcs = "Cboe market commentary and index data, US Treasury and TreasuryDirect, FRED, BLS, EIA, CFTC, Atlanta Fed, SEC filings, Federal Reserve, Kalshi, Polymarket, Alpha Vantage"
    parts.append('<footer><span>%s · reference close %s.</span><span>Sources: %s. Headlines are unconfirmed. Conditional context, not advice.</span></footer>' % (
        e(b.get("slot_label")), e(b.get("ref_date")), srcs))
    return "".join(p for p in parts if p)
