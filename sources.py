"""
Structured sources for the Context Engine. Python standard library only.

Every source fails soft: gather() never raises. Each source records a status
(working or failed, with a short reason) that the page shows in its health table.

Sources (all free):
  fred        FRED (St. Louis Fed): index closes, yields, real yield, breakeven, credit spread,
              oil, VIX, VXN, PCE inflation. FRED_API_KEY recommended (free).
  treasury    US Treasury daily par yield curve. Same-day official yields (FRED lags a day).
  bls         BLS API: CPI, core CPI, PPI, unemployment, payrolls. BLS_API_KEY optional (free).
  calendar    Official release dates: BLS schedule (with times), FRED release dates (BEA and others,
              needs FRED_API_KEY), and the Fed's FOMC meeting calendar.
  consensus   Unofficial weekly calendar with consensus forecasts (backup only, labelled unofficial).
  edgar       SEC EDGAR: recent 8-K filings from the ten largest Nasdaq-100 companies.
  odds        Fed decision odds from Kalshi and Polymarket public data.
  gdelt       GDELT: global and geopolitical news (titles only, unverified).
  headlines   Google News RSS searches since the last US close (titles only, unverified).
  fed         Federal Reserve press releases and speeches (official).
  cboe_idx    Cboe index history files: VIX, VXN, VVIX, SKEW, VIX9D, COR1M where published.
"""
import csv, io, json, math, os, re, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtime
from html.parser import HTMLParser
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

VIENNA = ZoneInfo("Europe/Vienna")
NEW_YORK = ZoneInfo("America/New_York")
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0 Safari/537.36 personal-research-script")


def contact_ua():
    """SEC and BLS ask automated clients to identify themselves with a contact email."""
    email = os.environ.get("CONTACT_EMAIL", "").strip() or "no-email-set@example.com"
    return "ContextEngine personal research %s" % email


def _get(url, timeout=30, ua=None, data=None, headers=None):
    h = {"User-Agent": ua or BROWSER_UA, "Accept": "*/*"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h, data=data, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _num(v):
    try:
        x = float(str(v).replace(",", ""))
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


# =====================================================================
# FRED
# =====================================================================
# series id -> (description, change kind, unit). pct = % change, bp = basis-point change
SERIES = {
    "NASDAQ100": ("Nasdaq-100 index close", "pct", "index"),
    "SP500": ("S&P 500 index close", "pct", "index"),
    "VIXCLS": ("VIX close", "pct", "index"),
    "VXNCLS": ("VXN (Nasdaq-100 volatility) close", "pct", "index"),
    "DGS10": ("10-year Treasury yield", "bp", "%"),
    "DGS2": ("2-year Treasury yield", "bp", "%"),
    "T10Y2Y": ("10y minus 2y spread", "bp", "pct pts"),
    "DFII10": ("10-year real yield (TIPS)", "bp", "%"),
    "T10YIE": ("10-year breakeven inflation", "bp", "%"),
    "BAMLH0A0HYM2": ("High-yield credit spread (OAS)", "bp", "pct pts"),
    "DCOILWTICO": ("WTI crude oil", "pct", "$/bbl"),
    "DCOILBRENTEU": ("Brent crude oil", "pct", "$/bbl"),
}
MONTHLY_SERIES = {  # BEA's PCE inflation, distributed by FRED
    "PCEPI": ("PCE price index", "PCE inflation"),
    "PCEPILFE": ("Core PCE price index (ex food and energy)", "Core PCE inflation"),
}


def fred_series(sid, start):
    """[(date, float)] from start. Missing values ('.') are skipped."""
    key = os.environ.get("FRED_API_KEY")
    if key:
        url = ("https://api.stlouisfed.org/fred/series/observations?series_id=%s&api_key=%s"
               "&file_type=json&observation_start=%s" % (sid, key, start))
        rows = [(o["date"], o["value"]) for o in json.loads(_get(url))["observations"]]
    else:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=%s" % (sid, start)
        rows = [(r[0], r[1]) for r in list(csv.reader(io.StringIO(_get(url))))[1:] if len(r) >= 2]
    out = []
    for d, v in rows:
        x = _num(v)
        if x is not None:
            out.append((d, x))
    return out


def with_changes(rows, kind):
    """Day-over-day changes computed in code so the model never does the arithmetic."""
    out = []
    for i, (d, v) in enumerate(rows):
        item = {"date": d, "value": round(v, 4)}
        if i > 0:
            prev = rows[i - 1][1]
            if kind == "pct" and prev:
                item["chg_pct"] = round((v / prev - 1) * 100, 2)
            elif kind == "bp":
                item["chg_bp"] = round((v - prev) * 100, 1)
        out.append(item)
    return out


def fred_block(today):
    data, errs = {}, []
    start = (today - timedelta(days=24)).isoformat()
    for sid, (desc, kind, unit) in SERIES.items():
        try:
            rows = fred_series(sid, start)[-10:]
            if rows:
                data[sid] = {"description": desc, "unit": unit, "observations": with_changes(rows, kind)}
        except Exception as e:
            errs.append("%s: %s" % (sid, e))
    monthly = {}
    mstart = (today - timedelta(days=500)).isoformat()
    for sid, (desc, label) in MONTHLY_SERIES.items():
        try:
            rows = fred_series(sid, mstart)
            if len(rows) >= 13:
                last, prev, yago = rows[-1], rows[-2], rows[-13]
                monthly[sid] = {"description": desc, "label": label, "month": last[0][:7],
                                "mom_pct": round((last[1] / prev[1] - 1) * 100, 2),
                                "yoy_pct": round((last[1] / yago[1] - 1) * 100, 2)}
        except Exception as e:
            errs.append("%s: %s" % (sid, e))
    return data, monthly, errs


def fred_history(sid, start="2000-01-01"):
    """Long daily history for base rates. Returns {date: value}."""
    return dict(fred_series(sid, start))


# =====================================================================
# US Treasury daily par yield curve (official, same day)
# =====================================================================
TREASURY_URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                "daily-treasury-rates.csv/%d/all?type=daily_treasury_yield_curve"
                "&field_tdr_date_value=%d&page&_format=csv")
TREASURY_TENORS = ["3 Mo", "2 Yr", "5 Yr", "10 Yr", "30 Yr"]


def treasury(today):
    rows = []
    for year in (today.year, today.year - 1):
        try:
            text = _get(TREASURY_URL % (year, year))
        except Exception:
            if year == today.year:
                raise
            continue
        for r in csv.DictReader(io.StringIO(text)):
            try:
                d = datetime.strptime(r["Date"], "%m/%d/%Y").date().isoformat()
            except Exception:
                continue
            vals = {t: _num(r.get(t)) for t in TREASURY_TENORS}
            if vals.get("10 Yr") is not None:
                rows.append((d, vals))
        if len(rows) >= 6:
            break
    rows.sort()
    rows = rows[-6:]
    if not rows:
        raise RuntimeError("no rows in Treasury file")
    out = []
    for i, (d, vals) in enumerate(rows):
        item = {"date": d}
        for t, v in vals.items():
            if v is None:
                continue
            item[t] = v
            if i > 0 and rows[i - 1][1].get(t) is not None:
                item[t + " chg_bp"] = round((v - rows[i - 1][1][t]) * 100, 1)
        out.append(item)
    return out


# =====================================================================
# BLS API: inflation and jobs prints
# =====================================================================
BLS_SERIES = {
    "CUSR0000SA0": ("CPI, all items (seasonally adjusted)", "index"),
    "CUSR0000SA0L1E": ("Core CPI, ex food and energy (SA)", "index"),
    "WPSFD4": ("PPI final demand (SA)", "index"),
    "WPSFD49116": ("PPI final demand ex food, energy, trade (SA)", "index"),
    "LNS14000000": ("Unemployment rate", "level"),
    "CES0000000001": ("Nonfarm payrolls, thousands", "diff"),
}


def bls(today):
    key = os.environ.get("BLS_API_KEY", "").strip()
    payload = {"seriesid": list(BLS_SERIES), "startyear": str(today.year - 2), "endyear": str(today.year)}
    if key:
        payload["registrationkey"] = key
        url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    else:
        url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    resp = json.loads(_get(url, ua=contact_ua(), data=json.dumps(payload).encode(),
                           headers={"Content-Type": "application/json"}))
    if resp.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError("; ".join(resp.get("message", [])) or resp.get("status", "BLS error"))
    out = {}
    for s in resp["Results"]["series"]:
        sid = s["seriesID"]
        desc, kind = BLS_SERIES.get(sid, (sid, "level"))
        obs = []
        for o in s.get("data", []):
            if not o.get("period", "").startswith("M") or o["period"] == "M13":
                continue
            obs.append(("%s-%s" % (o["year"], o["period"][1:]), _num(o.get("value"))))
        obs.sort()
        obs = [(m, v) for m, v in obs if v is not None]  # BLS uses '-' for missing months
        if len(obs) < 2:
            continue
        (m1, v1), (m0, v0) = obs[-1], obs[-2]
        item = {"description": desc, "month": m1, "value": v1}
        if kind == "index":
            item["mom_pct"] = round((v1 / v0 - 1) * 100, 2)
            yago = dict(obs).get("%d-%s" % (int(m1[:4]) - 1, m1[5:]))
            item["yoy_pct"] = round((v1 / yago - 1) * 100, 2) if yago else None
            item["prev_mom_pct"] = round((v0 / obs[-3][1] - 1) * 100, 2) if len(obs) >= 3 else None
        elif kind == "diff":
            item["change"] = round(v1 - v0, 0)
        else:
            item["previous"] = v0
        out[sid] = item
    if not out:
        raise RuntimeError("BLS returned no usable series")
    return out


# =====================================================================
# Official release calendars
# =====================================================================
BLS_ICS = "https://www.bls.gov/schedule/news_release/bls.ics"
FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
BLS_KEEP = re.compile(r"Consumer Price|Producer Price|Employment Situation|Job Openings|"
                      r"Employment Cost|Real Earnings|Import and Export|Productivity", re.I)
FRED_RELEASES_KEEP = {  # FRED release names (BEA, Census, Fed) worth listing
    "Gross Domestic Product": "08:30", "Personal Income and Outlays": "08:30",
    "Advance Monthly Sales for Retail and Food Services": "08:30",
    "Unemployment Insurance Weekly Claims Report": "08:30", "New Residential Construction": "08:30",
    "Advance Durable Goods Manufacturers' Shipments, Inventories and Orders": "08:30",
    "Industrial Production and Capacity Utilization": "09:15",
    "University of Michigan: Consumer Sentiment": "10:00",
}


def _ics_events(text):
    text = re.sub(r"\r?\n[ \t]", "", text)  # unfold lines
    for block in text.split("BEGIN:VEVENT")[1:]:
        f = {}
        for line in block.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                f[k.split(";")[0].upper()] = (k, v.strip())
        yield f


def _ics_dt(field):
    k, v = field
    tz = re.search(r"TZID=([^;:]+)", k)
    if v.endswith("Z"):
        return datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    if "T" in v:
        dt = datetime.strptime(v[:15], "%Y%m%dT%H%M%S")
        zone = NEW_YORK
        if tz:
            try:
                zone = ZoneInfo(tz.group(1))
            except Exception:  # legacy names such as "US-Eastern" used by BLS
                zone = NEW_YORK
        return dt.replace(tzinfo=zone)
    return datetime.strptime(v[:8], "%Y%m%d").replace(hour=8, minute=30, tzinfo=NEW_YORK)


def _cal_item(dt, event, source, time_note=""):
    return {"sort": dt.astimezone(timezone.utc).isoformat(),
            "when_vienna": dt.astimezone(VIENNA).strftime("%a %d %b %H:%M"),
            "when_new_york": dt.astimezone(NEW_YORK).strftime("%a %d %b %H:%M"),
            "event": event, "source": source, "time_note": time_note}


def bls_calendar(now, days):
    out = []
    for f in _ics_events(_get(BLS_ICS, ua=contact_ua())):
        if "DTSTART" not in f or "SUMMARY" not in f:
            continue
        name = f["SUMMARY"][1]
        if not BLS_KEEP.search(name):
            continue
        dt = _ics_dt(f["DTSTART"])
        if now - timedelta(hours=12) <= dt <= now + timedelta(days=days):
            out.append(_cal_item(dt, name, "BLS release schedule"))
    return out


def fred_release_calendar(now, days):
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("needs FRED_API_KEY")
    url = ("https://api.stlouisfed.org/fred/releases/dates?api_key=%s&file_type=json"
           "&realtime_start=%s&realtime_end=%s&include_release_dates_with_no_data=true&limit=1000"
           % (key, now.date().isoformat(), (now + timedelta(days=days)).date().isoformat()))
    out = []
    for r in json.loads(_get(url)).get("release_dates", []):
        name = r.get("release_name", "")
        if name not in FRED_RELEASES_KEEP:
            continue
        hh, mm = FRED_RELEASES_KEEP[name].split(":")
        dt = datetime.strptime(r["date"], "%Y-%m-%d").replace(hour=int(hh), minute=int(mm), tzinfo=NEW_YORK)
        out.append(_cal_item(dt, name, "FRED release calendar", "usual release time"))
    return out


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0
    def handle_starttag(self, tag, a):
        if tag in ("script", "style"): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip: self.skip -= 1
        if tag in ("div", "p", "li", "tr", "h1", "h2", "h3", "h4", "h5", "br", "td", "strong"):
            self.parts.append("\n")
    def handle_data(self, d):
        if not self.skip: self.parts.append(d)


def html_text(html):
    p = _Text(); p.feed(html)
    return re.sub(r"[ \t]+", " ", "".join(p.parts))


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def fomc_calendar(now, days):
    """Parse meeting dates from the Fed's FOMC calendar page. Decision day = last day of the meeting, 14:00 ET."""
    text = html_text(_get(FOMC_URL))
    out = []
    for ym in re.finditer(r"(20\d\d) FOMC Meetings", text):
        year = int(ym.group(1))
        nxt = re.search(r"20\d\d FOMC Meetings", text[ym.end():])
        chunk = text[ym.end(): ym.end() + (nxt.start() if nxt else 6000)]
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        for i, l in enumerate(lines):
            m = re.match(r"^(%s)(?:/(%s))?$" % ("|".join(MONTHS), "|".join(MONTHS)), l)
            if not m or i + 1 >= len(lines):
                continue
            d = re.match(r"^(\d{1,2})(?:-(\d{1,2}))?(\*)?", lines[i + 1])
            if not d:
                continue
            month = MONTHS.index(m.group(2) or m.group(1)) + 1
            last_day = int(d.group(2) or d.group(1))
            if m.group(2) and d.group(2) and int(d.group(2)) < int(d.group(1)):
                month = MONTHS.index(m.group(2)) + 1
            try:
                dt = datetime(year, month, last_day, 14, 0, tzinfo=NEW_YORK)
            except ValueError:
                continue
            if now - timedelta(hours=12) <= dt <= now + timedelta(days=days):
                note = "with projections" if d.group(3) else ""
                out.append(_cal_item(dt, "FOMC decision" + (" (" + note + ")" if note else ""),
                                     "Federal Reserve FOMC calendar", "statement time 14:00 ET"))
    return out


def official_calendar(now, days=14):
    """Returns (events, per-part status). Raises only if every part fails."""
    events, parts = [], {}
    for name, fn in (("BLS", bls_calendar), ("FRED releases", fred_release_calendar), ("FOMC", fomc_calendar)):
        try:
            got = fn(now, days)
            events += got
            parts[name] = "ok, %d events" % len(got)
        except Exception as e:
            parts[name] = "failed: %s" % str(e)[:80]
    if not any(v.startswith("ok") for v in parts.values()):
        raise RuntimeError("; ".join("%s %s" % kv for kv in parts.items()))
    seen, uniq = set(), []
    for e in sorted(events, key=lambda e: e["sort"]):
        k = (e["event"].lower()[:30], e["sort"][:10])
        if k not in seen:
            seen.add(k); uniq.append(e)
    for e in uniq:
        del e["sort"]
    return uniq, parts


# ---- unofficial weekly calendar: kept only for consensus forecasts
CONSENSUS_URLS = ["https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                  "https://nfs.faireconomy.media/ff_calendar_nextweek.json"]


def consensus_calendar():
    events, errors, seen = [], [], set()
    for url in CONSENSUS_URLS:
        try:
            data = json.loads(_get(url))
        except Exception as e:
            errors.append(str(e)); continue
        for ev in data:
            if ev.get("country") != "USD" or ev.get("impact") not in ("High", "Medium"):
                continue
            try:
                dt = datetime.fromisoformat(ev["date"])
            except Exception:
                continue
            k = (ev.get("title"), ev["date"])
            if k in seen:
                continue
            seen.add(k)
            events.append({"when_vienna": dt.astimezone(VIENNA).strftime("%a %d %b %H:%M"),
                           "event": ev.get("title", ""), "forecast": ev.get("forecast") or None,
                           "previous": ev.get("previous") or None})
    if not events and errors:
        raise RuntimeError(errors[0])
    return events


# =====================================================================
# SEC EDGAR: 8-K filings of the largest Nasdaq-100 companies
# =====================================================================
EDGAR_COMPANIES = {
    "NVDA": 1045810, "MSFT": 789019, "AAPL": 320193, "AMZN": 1018724, "META": 1326801,
    "GOOGL": 1652044, "AVGO": 1730168, "TSLA": 1318605, "COST": 909832, "NFLX": 1065280,
}
EDGAR_ITEMS = {
    "1.01": "material agreement", "1.02": "agreement ended", "2.01": "acquisition or sale",
    "2.02": "results of operations", "2.05": "restructuring costs", "2.06": "impairment",
    "3.01": "delisting notice", "4.02": "financials not reliable", "5.02": "officer or director change",
    "5.07": "shareholder vote", "7.01": "Reg FD disclosure", "8.01": "other events", "9.01": "exhibits",
}
EDGAR_DAYS = 4


def edgar(now):
    out, errs = [], []
    cutoff = (now - timedelta(days=EDGAR_DAYS)).date().isoformat()
    for tkr, cik in EDGAR_COMPANIES.items():
        try:
            sub = json.loads(_get("https://data.sec.gov/submissions/CIK%010d.json" % cik, ua=contact_ua()))
        except Exception as e:
            errs.append("%s: %s" % (tkr, e)); continue
        r = sub.get("filings", {}).get("recent", {})
        for i, form in enumerate(r.get("form", [])):
            if form not in ("8-K", "8-K/A") or r["filingDate"][i] < cutoff:
                continue
            acc = r["accessionNumber"][i]
            items = [x.strip() for x in (r.get("items", [""] * (i + 1))[i] or "").split(",") if x.strip()]
            link = "https://www.sec.gov/Archives/edgar/data/%d/%s/%s" % (cik, acc.replace("-", ""), r["primaryDocument"][i])
            out.append({"ticker": tkr, "form": form, "filed": r["filingDate"][i],
                        "accepted": r.get("acceptanceDateTime", [""] * (i + 1))[i],
                        "items": ["%s %s" % (x, EDGAR_ITEMS.get(x, "")) for x in items],
                        "accession": acc, "link": link, "excerpt": ""})
        time.sleep(0.15)  # SEC allows 10 requests per second
    if errs and not out and len(errs) == len(EDGAR_COMPANIES):
        raise RuntimeError(errs[0])
    out.sort(key=lambda x: x["accepted"] or x["filed"], reverse=True)
    for f in out[:6]:  # short excerpt of the filing itself; skip pure exhibits/results-only noise
        try:
            t = re.sub(r"\s+", " ", html_text(_get(f["link"], ua=contact_ua())))
            m = re.search(r"Item\s+(5\.02|8\.01|1\.01|2\.0[1-6]|7\.01|4\.02)", t)
            f["excerpt"] = t[m.start(): m.start() + 900].strip() if m else ""
        except Exception:
            pass
        time.sleep(0.15)
    return out, errs


# =====================================================================
# Fed decision odds: Kalshi and Polymarket public data
# =====================================================================
KALSHI_URL = ("https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=%s"
              "&status=open&with_nested_markets=true&limit=5")
KALSHI_SERIES = ["KXFEDDECISION", "KXFED"]
POLY_URL = "https://gamma-api.polymarket.com/events?closed=false&limit=20&tag_slug=%s"
POLY_TAGS = ["fed-rates", "fed"]


def kalshi():
    out = []
    for s in KALSHI_SERIES:
        try:
            data = json.loads(_get(KALSHI_URL % s, headers={"Accept": "application/json"}))
        except Exception:
            continue
        for ev in data.get("events", [])[:3]:
            mk = []
            for m in ev.get("markets", []):
                p = m.get("last_price")
                bid, ask = m.get("yes_bid"), m.get("yes_ask")
                if bid and ask:
                    p = (bid + ask) / 2
                if p is None:
                    continue
                mk.append({"outcome": m.get("yes_sub_title") or m.get("subtitle") or m.get("title", ""),
                           "prob_pct": round(float(p), 1)})
            if mk:
                mk.sort(key=lambda x: -x["prob_pct"])
                out.append({"venue": "Kalshi", "event": ev.get("title", s), "close": ev.get("strike_date") or "",
                            "markets": mk[:6]})
        if out:
            break
    return out


def polymarket():
    out = []
    for tag in POLY_TAGS:
        try:
            data = json.loads(_get(POLY_URL % tag))
        except Exception:
            continue
        for ev in data:
            title = ev.get("title", "")
            if not re.search(r"\bFed\b|FOMC|interest rate", title, re.I):
                continue
            mk = []
            for m in ev.get("markets", []):
                try:
                    outcomes = json.loads(m.get("outcomes") or "[]")
                    prices = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
                except Exception:
                    continue
                if outcomes[:1] == ["Yes"] and prices:
                    mk.append({"outcome": m.get("groupItemTitle") or m.get("question", ""),
                               "prob_pct": round(prices[0] * 100, 1)})
            if mk:
                mk.sort(key=lambda x: -x["prob_pct"])
                out.append({"venue": "Polymarket", "event": title, "close": (ev.get("endDate") or "")[:10],
                            "markets": mk[:6]})
        if out:
            break
    out.sort(key=lambda e: e["close"] or "9999")
    return out[:3]


# =====================================================================
# GDELT global news, Google News headlines, Fed releases
# =====================================================================
GDELT_URL = ("https://api.gdeltproject.org/api/v2/doc/doc?query=%s&mode=artlist&format=json"
             "&maxrecords=40&timespan=%dh&sort=datedesc")
GDELT_QUERY = ('(Iran OR OPEC OR "oil prices" OR tariffs OR sanctions OR Taiwan OR Ukraine OR '
               '"Strait of Hormuz" OR "trade war") sourcelang:english')
MAX_GDELT = 15


def _norm(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def last_us_close(now=None):
    """Most recent weekday 16:00 New York time that is not in the future."""
    now = (now or datetime.now(timezone.utc)).astimezone(NEW_YORK)
    d = now.date()
    if datetime.combine(d, dtime(16, 0), NEW_YORK) > now:
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return datetime.combine(d, dtime(16, 0), NEW_YORK)


def gdelt(now):
    hours = max(6, min(72, math.ceil((now - last_us_close(now)).total_seconds() / 3600)))
    url = GDELT_URL % (quote_plus(GDELT_QUERY), hours)
    try:
        text = _get(url)
    except urllib.error.HTTPError as e:
        if e.code != 429:
            raise
        time.sleep(8)  # GDELT allows one request every 5 seconds per address
        text = _get(url)
    data = json.loads(text or "{}")
    out, seen = [], set()
    for a in data.get("articles", []):
        k = _norm(a.get("title", ""))[:80]
        if not k or k in seen:
            continue
        seen.add(k)
        try:
            dt = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            when = dt.astimezone(VIENNA).strftime("%a %d %b %H:%M")
        except Exception:
            when = ""
        out.append({"time_vienna": when, "headline": a.get("title", ""), "publisher": a.get("domain", ""),
                    "link": a.get("url", "")})
        if len(out) >= MAX_GDELT:
            break
    return out


GNEWS_QUERIES = ["Nasdaq", "Nasdaq futures", "S&P 500 futures", "Treasury yields",
                 "Fed interest rates", "oil prices", "inflation CPI jobs report", "AI stocks Nvidia"]
GNEWS_URL = "https://news.google.com/rss/search?q=%s&hl=en-US&gl=US&ceid=US:en"
HEADLINES_PER_QUERY = 6
MAX_HEADLINES = 25
FED_URLS = ["https://www.federalreserve.gov/feeds/press_all.xml",
            "https://www.federalreserve.gov/feeds/speeches_and_testimony.xml"]
FED_DAYS = 7
MAX_FED_ITEMS = 10


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _child_text(el, *names):
    for c in el:
        if _local(c.tag) in names and (c.text or "").strip():
            return c.text.strip()
    return ""


def _link(el):
    for c in el:
        if _local(c.tag) == "link":
            return (c.text or "").strip() or c.attrib.get("href", "")
    return ""


def _parse_dt(text):
    if not text:
        return None
    try:
        dt = parsedate_to_datetime(text)
    except Exception:
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _entries(xml_text):
    root = ET.fromstring(xml_text)
    for el in root.iter():
        if _local(el.tag) not in ("item", "entry"):
            continue
        yield {"title": _child_text(el, "title"),
               "dt": _parse_dt(_child_text(el, "pubDate", "published", "updated")),
               "link": _link(el), "summary": _child_text(el, "description", "summary"),
               "category": _child_text(el, "category"), "source": _child_text(el, "source")}


def headlines(now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = last_us_close(now).astimezone(timezone.utc)
    hours = max(1, math.ceil((now - cutoff).total_seconds() / 3600))
    window = "%dh" % hours if hours < 24 else "%dd" % math.ceil(hours / 24)
    items, seen, errors, ok = [], set(), [], 0
    for q in GNEWS_QUERIES:
        try:
            entries = list(_entries(_get(GNEWS_URL % quote_plus("%s when:%s" % (q, window)))))
        except Exception as e:
            errors.append("%s: %s" % (q, e)); continue
        ok += 1
        taken = 0
        for en in entries:
            title, pub, dt = en["title"], en["source"], en["dt"]
            if pub and title.endswith(" - " + pub):
                title = title[: -len(pub) - 3].strip()
            elif " - " in title and not pub:
                title, _, pub = title.rpartition(" - ")
            key = _norm(title)
            if not title or dt is None or dt < cutoff or dt > now + timedelta(minutes=5) or key in seen:
                continue
            seen.add(key)
            items.append({"dt": dt, "query": q, "headline": title, "publisher": pub, "link": en["link"]})
            taken += 1
            if taken >= HEADLINES_PER_QUERY:
                break
    if ok == 0:
        raise RuntimeError("; ".join(errors) or "no searches ran")
    items.sort(key=lambda x: x["dt"], reverse=True)
    out = [{"time_vienna": x["dt"].astimezone(VIENNA).strftime("%a %d %b %H:%M"), "query": x["query"],
            "headline": x["headline"], "publisher": x["publisher"], "link": x["link"]} for x in items[:MAX_HEADLINES]]
    return out, "%d/%d searches, %d headlines since the %s close" % (ok, len(GNEWS_QUERIES), len(out),
                                                                     last_us_close(now).strftime("%a %d %b"))


def fed_press(now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=FED_DAYS)
    entries, errors = [], []
    for u in FED_URLS:  # each feed counts on its own; fail only if every feed fails
        try:
            entries += list(_entries(_get(u)))
        except Exception as e:
            errors.append("%s: %s" % (u.rsplit("/", 1)[-1], e))
    if errors and not entries:
        raise RuntimeError("; ".join(errors))
    out, seen = [], set()
    for en in entries:
        if en["link"] in seen or not en["title"] or en["dt"] is None or en["dt"] < cutoff:
            continue
        seen.add(en["link"])
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", en["summary"])).strip()
        out.append({"dt": en["dt"], "title": en["title"], "category": en["category"],
                    "summary": text[:280], "link": en["link"]})
    out.sort(key=lambda x: x["dt"], reverse=True)
    return [{"time_vienna": x["dt"].astimezone(VIENNA).strftime("%a %d %b %H:%M"),
             "title": x["title"], "category": x["category"], "summary": x["summary"], "link": x["link"]}
            for x in out[:MAX_FED_ITEMS]]


# =====================================================================
# Cboe index history files
# =====================================================================
CBOE_IDX_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/%s_History.csv"
CBOE_INDICES = {"VIX": "VIX", "VXN": "VXN (Nasdaq-100 vol)", "VVIX": "VVIX (vol of VIX)",
                "SKEW": "SKEW", "VIX9D": "VIX9D (9-day vol)", "COR1M": "COR1M (1-month implied correlation)"}


def cboe_index(sym):
    rows = list(csv.reader(io.StringIO(_get(CBOE_IDX_URL % sym))))
    head = [h.strip().upper() for h in rows[0]]
    col = head.index("CLOSE") if "CLOSE" in head else len(head) - 1
    out = []
    for r in rows[1:]:
        if len(r) <= col:
            continue
        v = _num(r[col])
        try:
            d = datetime.strptime(r[0].strip(), "%m/%d/%Y").date().isoformat()
        except ValueError:
            try:
                d = datetime.strptime(r[0].strip(), "%Y-%m-%d").date().isoformat()
            except ValueError:
                continue
        if v is not None:
            out.append((d, v))
    out.sort()
    return with_changes(out[-6:], "pct")


def cboe_indices():
    data, errs = {}, []
    for sym, desc in CBOE_INDICES.items():
        try:
            obs = cboe_index(sym)
            if obs:
                data[sym] = {"description": desc, "observations": obs}
        except Exception as e:
            errs.append("%s: %s" % (sym, str(e)[:60]))
    if not data:
        raise RuntimeError(errs[0] if errs else "no data")
    return data, errs


# =====================================================================
# orchestration
# =====================================================================
SOURCE_NAMES = {
    "fred": "FRED", "treasury": "US Treasury yield curve", "bls": "BLS inflation and jobs",
    "calendar": "Official release calendars", "consensus": "Consensus calendar (unofficial)",
    "edgar": "SEC EDGAR 8-K filings", "odds": "Fed odds (Kalshi, Polymarket)", "gdelt": "GDELT global news",
    "headlines": "Google News headlines", "fed": "Federal Reserve releases", "cboe_idx": "Cboe index history",
}


def gather(now=None):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(NEW_YORK).date()
    out = {"generated_utc": now.isoformat(), "warnings": [], "status": {}}

    def status(key, ok, detail):
        out["status"][key] = {"name": SOURCE_NAMES[key], "ok": bool(ok), "detail": detail}

    def run(key, fn, describe):
        try:
            val = fn()
            out[key] = val
            status(key, bool(val), describe(val))
        except Exception as e:
            out[key] = None
            out["warnings"].append("%s unavailable: %s" % (SOURCE_NAMES[key], str(e)[:160]))
            status(key, False, str(e)[:120])

    try:
        daily, monthly, errs = fred_block(today)
        out["fred"], out["fred_monthly"] = daily, monthly
        if errs:
            out["warnings"].append("FRED: %d series failed, first: %s" % (len(errs), errs[0][:120]))
        status("fred", daily, "%d/%d daily series, %d monthly" % (len(daily), len(SERIES), len(monthly)))
    except Exception as e:
        out["fred"], out["fred_monthly"] = {}, {}
        status("fred", False, str(e)[:120])

    run("treasury", lambda: treasury(today), lambda v: "latest %s" % v[-1]["date"])
    run("bls", lambda: bls(today), lambda v: "%d series, latest month %s" % (len(v), max(x["month"] for x in v.values())))

    try:
        out["calendar"], parts = official_calendar(now)
        status("calendar", True, "%d events next 14 days (%s)" % (
            len(out["calendar"]), ", ".join("%s %s" % (k, v.split(",")[0]) for k, v in parts.items())))
    except Exception as e:
        out["calendar"] = None
        status("calendar", False, str(e)[:120])

    run("consensus", consensus_calendar, lambda v: "%d USD events with forecasts" % len(v))

    try:
        out["edgar"], errs = edgar(now)
        status("edgar", True, "%d 8-Ks in %d days from %d companies%s" % (
            len(out["edgar"]), EDGAR_DAYS, len(EDGAR_COMPANIES), ", %d lookups failed" % len(errs) if errs else ""))
    except Exception as e:
        out["edgar"] = None
        status("edgar", False, str(e)[:120])

    def odds():
        k, p = kalshi(), polymarket()
        if not k and not p:
            raise RuntimeError("no open Fed markets found on Kalshi or Polymarket")
        return k + p
    run("odds", odds, lambda v: ", ".join(sorted({e["venue"] for e in v})) + ", %d events" % len(v))
    run("gdelt", lambda: gdelt(now), lambda v: "%d articles" % len(v))

    try:
        out["headlines"], info = headlines(now)
        status("headlines", out["headlines"], info)
    except Exception as e:
        out["headlines"] = None
        status("headlines", False, str(e)[:120])

    run("fed", lambda: fed_press(now), lambda v: "%d items in %d days" % (len(v), FED_DAYS))

    try:
        out["cboe_idx"], errs = cboe_indices()
        status("cboe_idx", True, "%s%s" % (", ".join(out["cboe_idx"]), "; missing " + ", ".join(e.split(":")[0] for e in errs) if errs else ""))
    except Exception as e:
        out["cboe_idx"] = None
        status("cboe_idx", False, str(e)[:120])
    return out


PROMPT_KEYS = ("fred", "fred_monthly", "treasury", "bls", "cboe_idx", "calendar", "consensus",
               "edgar", "odds", "fed", "headlines", "gdelt")


def to_prompt(structured):
    if not structured or not any(structured.get(k) for k in PROMPT_KEYS):
        return "none available this run. Do not invent any data.\nWarnings: " + json.dumps((structured or {}).get("warnings", []))
    slim = {k: structured.get(k) for k in PROMPT_KEYS}
    for k in ("headlines", "gdelt", "fed"):
        slim[k] = [{a: b for a, b in h.items() if a != "link"} for h in (slim[k] or [])]
    slim["edgar"] = [{a: b for a, b in f.items() if a not in ("link", "accession")} for f in (slim["edgar"] or [])]
    slim["warnings"] = structured.get("warnings", [])
    note = ("Notes: FRED daily series lag about one business day. treasury is the official same-day curve. "
            "bls and fred_monthly are official prints with month-over-month changes computed in code. "
            "calendar is official (BLS, FRED release dates, FOMC); consensus is an unofficial calendar, "
            "use it only for forecast/previous and say so. edgar items are SEC filings (primary sources). "
            "odds are prediction-market prices, not CME FedWatch. fed items are official. headlines and gdelt "
            "are unverified titles: label them as headlines, never state them as fact.")
    return note + "\n" + json.dumps(slim, indent=1, default=str)
