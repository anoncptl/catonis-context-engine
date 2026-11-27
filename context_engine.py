#!/usr/bin/env python3
"""
Context Engine
--------------
Daily market context for an NQ/Nasdaq day trader.

Reads Cboe Insights (daily market take, weekly volatility digest, all insights) for the narrative,
plus free official data (see sources.py), asks Claude for a brief with testable scenarios,
grades older scenarios automatically (scoring.py), checks every number against its inputs
(facts.py) and builds a static website (site.py).

Python standard library only (3.9+). Environment variables:
  ANTHROPIC_API_KEY  required for a brief
  FRED_API_KEY       recommended (free)
  BLS_API_KEY        optional (free)
  CONTACT_EMAIL      recommended: SEC and BLS ask automated clients for a contact address

Usage:
  python context_engine.py              run now (manual run)
  python context_engine.py --scheduled  only run if the clock is inside a run slot (used by GitHub)
  python context_engine.py --check      test every source and print which work; no AI call
  python context_engine.py --site       rebuild the website from saved data only
"""
import hashlib, json, os, re, sys, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import discord, facts, scoring, sitegen, sources  # noqa: E402

MODEL = os.environ.get("CONTEXT_ENGINE_MODEL", "claude-sonnet-5-5")
VIENNA, NEW_YORK = ZoneInfo("Europe/Vienna"), ZoneInfo("America/New_York")
ROOT = Path(__file__).parent
DATA, SITE_DIR = ROOT / "data", ROOT / "site"
POSTS_DIR, BRIEFS_DIR, SNAP_DIR = DATA / "posts", DATA / "briefs", DATA / "structured"
MEMORY_FILE, RUNS_FILE, LEDGER_FILE = DATA / "memory.json", DATA / "runs.json", DATA / "forecasts.json"

RSS_URL = "https://www.cboe.com/insights/rss/"
CATEGORY_PAGES = {
    "todaysmarkettake": "https://www.cboe.com/insights/categories/todaysmarkettake/",
    "macro_volatility_digest": "https://www.cboe.com/insights/categories/macro_volatility_digest/",
    "all": "https://www.cboe.com/insights",
}
PRIORITY = {"todaysmarkettake": 0, "macro_volatility_digest": 0, "indices": 1,
            "DerivativesResearch": 2, "trading_investing": 2}
MAX_CHARS_PER_POST, MAX_PROMPT_POSTS, BRIEFS_IN_CONTEXT, KEEP_SNAPSHOT_DAYS = 4500, 12, 5, 30

# One automatic run per weekday at 08:30 New York (14:30 CET). A Claude scheduled task triggers it at that time;
# GitHub's own schedule fires a few backup times in case the trigger is missed. The first firing inside the
# window does the work and later ones exit in seconds. Manual runs always run.
SLOTS = {
    "daily": {"tz": NEW_YORK, "start": (8, 30), "end": (10, 59), "label": "Daily (08:30 New York)"},
}


# ---------- secret scrubbing ----------
SECRET_ENV = ("ANTHROPIC_API_KEY", "FRED_API_KEY", "BLS_API_KEY", "CONTACT_EMAIL", "DISCORD_WEBHOOK_URL", "ALPHAVANTAGE_API_KEY", "EIA_API_KEY")
SECRET_PATTERNS = [re.compile(r"https://(?:\w+\.)?discord(?:app)?\.com/api/webhooks/\S+"), re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"), re.compile(r"(api_key|apikey|registrationkey|x-api-key)=[^&\s\"']+", re.I)]


def scrub(text):
    """Remove every key (and the contact email) from text before it is saved or published."""
    for name in SECRET_ENV:
        v = os.environ.get(name, "").strip()
        if len(v) >= 6:
            text = text.replace(v, "[%s removed]" % name.lower())
    for pat in SECRET_PATTERNS:
        text = pat.sub("[key removed]", text)
    return text


def save_json(path, obj):
    Path(path).write_text(scrub(json.dumps(obj, indent=1, default=str)))


# ---------- Cboe Insights ----------
def http_get(url, retries=2):
    for i in range(retries + 1):
        try:
            return sources._get(url)
        except Exception:
            if i == retries:
                raise
            time.sleep(2 * (i + 1))


def parse_rss(xml_text):
    items = []
    for it in ET.fromstring(xml_text).iter("item"):
        def g(tag):
            for c in it:
                if c.tag.split("}")[-1] == tag:
                    return (c.text or "").strip()
            return ""
        link = g("link")
        try:
            dt = parsedate_to_datetime(g("pubDate")).isoformat()
        except Exception:
            dt = ""
        items.append({"slug": link.rstrip("/").split("/")[-1], "url": link, "title": g("title"),
                      "summary": g("description"), "author": g("creator"), "category": g("category"), "published": dt})
    return items


class _Extractor(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "form", "noscript", "svg", "aside"}
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "blockquote"}

    def __init__(self):
        super().__init__()
        self.skip = self.main = 0
        self.cur = None
        self.blocks_main, self.blocks_all = [], []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP: self.skip += 1
        if tag in ("article", "main"): self.main += 1
        if tag in self.BLOCK and not self.skip: self.cur = []
        if tag == "title": self._in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip: self.skip -= 1
        if tag in ("article", "main") and self.main: self.main -= 1
        if tag == "title": self._in_title = False
        if tag in self.BLOCK and self.cur is not None:
            t = re.sub(r"\s+", " ", " ".join(self.cur)).strip()
            if t:
                self.blocks_all.append((tag, t))
                if self.main: self.blocks_main.append((tag, t))
            self.cur = None

    def handle_data(self, data):
        if self._in_title: self.title += data
        if self.cur is not None and not self.skip: self.cur.append(data)


BOILERPLATE = ("New to Options?", "Build your education foundation", "Sign up for our free learning portal")
KEY_CATEGORIES = ("todaysmarkettake", "macro_volatility_digest")  # the newest post of each is read every run
LATEST_PER_CATEGORY = 2


def extract_article(html):
    """Returns (text, title, published_iso_or_empty)."""
    p = _Extractor(); p.feed(html)
    out = [t for tag, t in (p.blocks_main or p.blocks_all)
           if not (t.startswith(("©", "Copyright")) or "Cboe may contact me" in t) and (tag.startswith("h") or len(t) >= 40)]
    title = re.sub(r"\s*[|\-–]\s*Cboe.*$", "", p.title.strip())
    return "\n".join(out), title, find_date(html, title)


def find_date(html, title=""):
    """Publication date from the article page: structured data, meta tags, <time>, a 'Week of M/D/YYYY' title, or a written date."""
    for pat in (r'"datePublished"\s*:\s*"([^"]+)"', r'article:published_time"\s+content="([^"]+)"',
                r'content="([^"]+)"\s+property="article:published_time"', r'<time[^>]*datetime="([^"]+)"'):
        m = re.search(pat, html)
        if m:
            try:
                return datetime.fromisoformat(m.group(1).replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                pass
    m = re.search(r"Week of (\d{1,2})/(\d{1,2})/(\d{4})", title or "")
    if m:
        return "%s-%02d-%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (20\d\d)\b",
                  re.sub(r"<[^>]+>", " ", html))
    if m:
        try:
            return datetime.strptime(" ".join(m.groups()), "%B %d %Y").date().isoformat()
        except ValueError:
            pass
    return ""


def is_real_article(text):
    return len(text or "") >= 800 and not any(b in (text or "")[:300] for b in BOILERPLATE)


def load_posts():
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    return {f.stem: json.loads(f.read_text()) for f in POSTS_DIR.glob("*.json")}


def page_slugs(html):
    """Post links in page order (top = newest). Only real links; a cut-off link that is the start of a longer one is dropped."""
    order = []
    for slug in re.findall(r'href="(?:https?://www\.cboe\.com)?/insights/posts/([a-z0-9][a-z0-9\-]*[a-z0-9])/?["?#]', html):
        if slug not in order:
            order.append(slug)
    return [x for x in order if not any(o != x and o.startswith(x) for o in order)]


def category_pages():
    """{category: [slugs, newest first]} for every page that loaded."""
    ranks = {}
    for cat, url in CATEGORY_PAGES.items():
        try:
            ranks[cat] = page_slugs(http_get(url))
        except Exception as e:
            print("  ! Cboe page %s failed: %s" % (cat, e), file=sys.stderr)
    return ranks


def fetch_post(item, rss_dates):
    """Download one post. Returns the saved item, or None if the page was not a real article (retried next run)."""
    try:
        text, title, date = extract_article(http_get(item["url"]))
    except Exception as e:
        print("  ! could not fetch %s: %s" % (item["url"], e), file=sys.stderr)
        return None
    if not is_real_article(text):
        print("  ! %s is not a readable article (skipped, will retry)" % item["url"], file=sys.stderr)
        return None
    if title:
        item["title"] = title
    date = date or rss_dates.get(item["slug"], "")
    item.update({"text": text, "text_source": "full_article", "published": date or item.get("published", ""),
                 "date_source": "article page" if date and item["slug"] not in rss_dates else ("RSS" if date else "unknown"),
                 "fetched_utc": datetime.now(timezone.utc).isoformat()})
    item.pop("from_category_page", None)
    (POSTS_DIR / ("%s.json" % item["slug"])).write_text(json.dumps(item, indent=1))
    time.sleep(1.0)
    return item


def refresh_posts():
    """Fetch new Cboe posts in full and re-check the newest Daily Take and Digest. Returns (new_posts, status)."""
    known = load_posts()
    # one-off repair: drop saved pages that were boilerplate instead of an article, so they are fetched again
    for slug, p in list(known.items()):
        if not is_real_article(p.get("text")):
            (POSTS_DIR / ("%s.json" % slug)).unlink(missing_ok=True)
            del known[slug]
        elif p.get("from_category_page"):  # old runs stamped these with the download date; that date was wrong
            p.update(published=find_date("", p.get("title", "")), date_source="title" if find_date("", p.get("title", "")) else "unknown")
            p.pop("from_category_page", None)
            (POSTS_DIR / ("%s.json" % slug)).write_text(json.dumps(p, indent=1))
    rss, rss_err = [], ""
    try:
        rss = parse_rss(http_get(RSS_URL))
    except Exception as e:
        rss_err = str(e)[:80]
    rss_dates = {i["slug"]: (i.get("published") or "")[:10] for i in rss if i.get("published")}
    ranks = category_pages()
    (DATA / "cboe_latest.json").write_text(json.dumps({k: v[:10] for k, v in ranks.items()}, indent=1))

    queue = [dict(i, published=(i.get("published") or "")[:10]) for i in rss]
    for cat, slugs in ranks.items():
        for slug in slugs:
            queue.append({"slug": slug, "url": "https://www.cboe.com/insights/posts/%s" % slug, "title": slug.replace("-", " ").title(),
                          "summary": "", "author": "", "published": rss_dates.get(slug, ""),
                          "category": cat if cat != "all" else "other"})
    new, done = [], set()
    for item in queue:
        if item["slug"] in known or item["slug"] in done:
            continue
        done.add(item["slug"])
        got = fetch_post(item, rss_dates)
        if got:
            new.append(got)
            known[got["slug"]] = got
    # fix the category of posts first saved as "other" when a key page lists them
    for cat in KEY_CATEGORIES:
        for slug in ranks.get(cat, []):
            p = known.get(slug)
            if p and p.get("category") != cat:
                p["category"] = cat
                (POSTS_DIR / ("%s.json" % slug)).write_text(json.dumps(p, indent=1))
    latest = {cat: [s for s in ranks.get(cat, [])[:LATEST_PER_CATEGORY] if s in known] for cat in KEY_CATEGORIES}
    names = {"todaysmarkettake": "Daily Take", "macro_volatility_digest": "Digest"}
    tops = "; ".join("newest %s: %s" % (names[c], known[l[0]]["title"][:60]) if l else "newest %s: NOT READ" % names[c] for c, l in latest.items())
    ok = all(latest[c] for c in KEY_CATEGORIES)
    detail = "%s; %d/3 pages; %d new posts; %s" % ("RSS %d items" % len(rss) if rss else "RSS failed " + rss_err, len(ranks), len(new), tops)
    return new, {"name": "Cboe Insights", "ok": ok, "detail": detail, "latest": latest}


def posts_for_prompt(new_posts, latest=None):
    """Always the newest Daily Take and Digest first, then other new posts, then recent cached ones."""
    known = load_posts()
    pool, order = {}, []

    def add(p, tag):
        if p and p["slug"] not in pool:
            pool[p["slug"]] = dict(p, _tag=tag)
            order.append(p["slug"])
    for cat, tag in (("todaysmarkettake", "newest Daily Take"), ("macro_volatility_digest", "newest Macro Volatility Digest")):
        for i, slug in enumerate((latest or {}).get(cat, [])):
            add(known.get(slug), tag if i == 0 else tag.replace("newest", "previous"))
    for p in sorted(new_posts, key=lambda p: (PRIORITY.get(p.get("category"), 3), p.get("published", "")), reverse=False):
        add(p, "new")
    if len(pool) < 6:
        for p in sorted(known.values(), key=lambda p: p.get("published") or "", reverse=True):
            if len(pool) >= 6:
                break
            add(p, "older")
    return [pool[s] for s in order][:MAX_PROMPT_POSTS]


# ---------- memory ----------
def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def recent_briefs(n):
    out = []
    all_b = sorted((json.loads(f.read_text()) for f in BRIEFS_DIR.glob("*.json")), key=lambda b: b.get("made_utc", ""))
    for b in all_b[-n:]:
        out.append({"id": b.get("id"), "summary": (b.get("what_happened") or {}).get("summary"),
                    "dominant_driver": b.get("dominant_driver"), "leader": b.get("leader"),
                    "outlook": {h: {"cuts": [v.get("lower_pct"), v.get("upper_pct")],
                                    "scenarios": [(s.get("name"), s.get("prob")) for s in v.get("scenarios", [])]}
                                for h, v in (b.get("outlook") or {}).items()}})
    return out


# ---------- prompt ----------
SYSTEM = """Never mention the user's city or country. Refer to times as CET (CEST in summer) or New York time.
You are the analysis core of a personal market-context engine for a discretionary NQ (Nasdaq-100 futures) day trader in Central Europe who trades the New York session with a Context, Location, Confirmation process. Your job is Context only: what is driving the market, which index leads, which scheduled events matter, and conditional scenarios. Never give entries, stops or price targets for trades.

Your only sources are the inputs below: Cboe Insights posts, the FACTS table, the structured data block, base rates, the forecast record, your earlier briefs and memory.

Hard rules:
1. Every number you write must come from the inputs. Prefer numbers from the FACTS table. Do not round differently than the input, do not compute new numbers yourself (code already computed changes), and never invent a level, consensus forecast, time or probability. If a number is not in the inputs, describe the fact without it.
2. Separate what a source states from your own inference. Put your inference in fields named *_inference or say "Engine read:".
3. Headlines (headlines, gdelt) are unverified: call them headlines, never state them as fact, and never let one headline move a probability by itself. SEC filings, Fed releases, BLS, Treasury and FRED are primary sources and may be stated as fact with attribution.
4. Scenarios are testable. For each horizon pick two cut points on the Nasdaq-100 % change from the last completed session close to the close 1 (next_day), 5 (next_week) or 21 (next_month) sessions later: bear = change below lower_pct, base = between, bull = above upper_pct. Probabilities sum to 100. Use the BASE RATES block to choose sensible cut points and as the starting point for probabilities; move away from history only for a stated reason. Code grades these automatically with Brier scores and compares you with history.
5. Name the dominant driver (one of: macro data, Fed and rates, single-stock or sector news, geopolitics and oil, volatility and positioning, earnings, unclear) and the leader (QQQ, SPX or unclear) with a reason that cites the leadership facts (Nasdaq-100 minus S&P 500, VXN minus VIX, COR1M if present).
6. List the scheduled events for the next two US sessions in Central European time (CET, or CEST in summer; write it as the when_vienna value, e.g. 'Tue 18 Nov 14:30') from the official calendar. Use consensus figures only from the consensus block and label them unofficial.
7. Flag narrative echo: say if a theme repeats without new evidence.
8. You have no live prices. FRED lags a day. Do not claim where NQ trades now.

Writing rules (a trader reads this 30 minutes before the open):
- Short, plain sentences. One fact per sentence. Lead with the fact, not the source.
- Do not attribute facts in the text. Never write "Cboe says", "Cboe names", "Cboe warns", "per Cboe", "FRED shows", "according to". State the fact. Sources are credited once at the bottom of the page. Only exception: name a primary source (SEC filing, Fed, BLS) when the attribution itself is the news.
- Never use em dashes or en dashes. Use periods, commas or colons.
- No "not X but Y" contrasts, no one-line dramatic closers, no filler (notably, crucially, key, pivotal, landscape, underscores, highlights, robust, delve).
- No stacked hedges. Say "may" once if needed.
- Put every unverified headline item into the "unconfirmed" list as one short line each, instead of repeating "unconfirmed" across fields.
Output ONLY one JSON object matching the schema. No prose outside the JSON."""

SCHEMA = """{
 "headline": "one line, max 90 characters",
 "what_happened": {"summary": "2 to 4 short sentences", "market_action": "1 to 2 sentences", "macro": "1 to 2 sentences", "geopolitics": "1 to 2 sentences or 'not covered by the sources'", "company_news": "1 to 2 sentences"},
 "unconfirmed": ["max 3 short lines: headline-only items, not verified by a primary source"],
 "dominant_driver": "macro data | Fed and rates | single-stock or sector news | geopolitics and oil | volatility and positioning | earnings | unclear",
 "driver_reason": "2 sentences",
 "leader": "QQQ | SPX | unclear",
 "leader_reason": "1 to 2 sentences citing the leadership facts",
 "overlap_with_previous": {"continuing": ["..."], "new": ["..."], "fading": ["..."], "echo_check": "..."},
 "scheduled_events": [{"when_vienna": "Tue 18 Nov 14:30", "event": "...", "why_it_matters": "...", "source": "BLS | FRED release calendar | FOMC calendar | earnings calendar | consensus (unofficial) | Cboe post"}],
 "outlook": {
   "next_day":   {"lower_pct": -0.8, "upper_pct": 0.8, "confidence": "low|medium|high", "confidence_reason": "...",
                  "scenarios": [{"name": "bear", "prob": 30, "text": "...", "invalidation": "..."}, {"name": "base", "prob": 45, "text": "...", "invalidation": "..."}, {"name": "bull", "prob": 25, "text": "...", "invalidation": "..."}]},
   "next_week":  {"lower_pct": 0, "upper_pct": 0, "confidence": "...", "confidence_reason": "...", "scenarios": ["... same shape ..."]},
   "next_month": {"lower_pct": 0, "upper_pct": 0, "confidence": "...", "confidence_reason": "...", "scenarios": ["... same shape ..."]}
 },
 "record_comment": "one or two sentences on what the graded record says about your calibration, or 'no graded forecasts yet'",
 "watch_list": ["max 4 short items to watch in the next session"],
 "memory_update": {"running_thesis": "max 120 words", "open_questions": ["..."], "themes": {"theme": "one-line status"}}
}"""


def build_prompt(ctx):
    parts = ["NOW: %s Central European time / %s New York. Run slot: %s. Last completed US session: %s." % (
        ctx["now"].astimezone(VIENNA).strftime("%a %d %b %Y %H:%M"), ctx["now"].astimezone(NEW_YORK).strftime("%H:%M"),
        ctx["slot"], ctx["ref_date"]),
        "\n## MEMORY\n" + json.dumps(ctx["memory"], indent=1),
        "\n## PREVIOUS BRIEFS (oldest to newest)\n" + (json.dumps(ctx["briefs"], indent=1) if ctx["briefs"] else "none, first run"),
        "\n## FORECAST RECORD (graded by code)\n" + ctx["ledger_text"],
        "\n## FACTS (id | label | value | as of | source)\n" + (facts.facts_prompt(ctx["facts"]) or "none"),
        "\n## BASE RATES (Nasdaq-100 %% change over N sessions since %s; quantiles p10..p90)\n" % (ctx["rates"] or {}).get("since", "n/a")
        + (json.dumps(ctx["rates"], indent=1) if ctx["rates"] else "unavailable this run: choose cut points from the facts and say confidence is low"),
        "\n## STRUCTURED DATA\n" + sources.to_prompt(ctx["structured"]),
        "\n## CBOE POSTS (first: Cboe's newest Daily Take, written after the US close, and newest weekly Macro Volatility Digest; then other new posts; [older] = already used before). Base what_happened mainly on the newest Daily Take and Digest. Do not name Cboe or the post titles in the text: the page credits sources once at the bottom. Write the facts directly."]
    for p in ctx["posts"]:
        parts.append("\n### [%s] [%s] %s | published %s | %s\n%s" % (p.get("_tag", ""), p.get("category"), p.get("title"),
                                                     (p.get("published") or "date unknown")[:10], p.get("text_source"), (p.get("text") or "")[:MAX_CHARS_PER_POST]))
    parts.append("\n## OUTPUT SCHEMA\n" + SCHEMA)
    return "\n".join(parts)


# ---------- Claude ----------
def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text[text.find("{"): text.rfind("}") + 1])


def _api(messages, key):
    body = json.dumps({"model": MODEL, "max_tokens": 16000, "system": SYSTEM, "messages": messages}).encode()
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                         headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                                  "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = "HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:300])
            if e.code in (400, 401, 403, 404):
                break
        except Exception as e:
            last = str(e)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("Claude API call failed: %s" % last)


def call_claude(messages):
    """One answer as parsed JSON. If the answer is cut off or not valid JSON, ask once more for a corrected one."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY is not set. Add it as a secret (see README step 4).")
    usage, convo = {}, list(messages)
    for attempt in range(2):
        resp = _api(convo, key)
        for k, v in (resp.get("usage") or {}).items():
            if isinstance(v, int):
                usage[k] = usage.get(k, 0) + v
        text = "".join(c.get("text", "") for c in resp["content"])
        cut = resp.get("stop_reason") == "max_tokens"
        try:
            if cut:
                raise ValueError("the answer was cut off at the length limit")
            return parse_json(text), text, usage
        except ValueError as e:  # json.JSONDecodeError is a ValueError
            print("    ! answer was not usable JSON (%s); asking for a corrected one" % str(e)[:80], file=sys.stderr)
            fix = ("Your previous answer could not be used: %s. Reply again with ONE complete, valid JSON object matching the schema. "
                   "Keep every text field short (two sentences at most) so the whole answer fits. No prose outside the JSON."
                   % ("it was cut off before the end" if cut else "invalid JSON (%s)" % str(e)[:120]))
            convo = list(messages[:-1]) + [{"role": "user", "content": messages[-1]["content"] + "\n\n" + fix}] if cut else \
                list(messages) + [{"role": "assistant", "content": text}, {"role": "user", "content": fix}]
    raise RuntimeError("Claude returned unusable JSON twice")


def thresholds_and_probs(brief):
    out = []
    for o in (brief.get("outlook") or {}).values():
        for k in ("lower_pct", "upper_pct"):
            if isinstance(o.get(k), (int, float)):
                out.append(o[k])
        out += [s.get("prob") for s in o.get("scenarios", []) if isinstance(s.get("prob"), (int, float))]
    return out


# ---------- slots ----------
def current_slot(now):
    for name, s in SLOTS.items():
        t = now.astimezone(s["tz"])
        if t.weekday() >= 5:
            continue
        hm = (t.hour, t.minute)
        if s["start"] <= hm <= s["end"]:
            return name, t.date().isoformat()
    return None, None


def fingerprint(new_posts, s):
    parts = [sorted(p["slug"] for p in new_posts),
             [(s.get("treasury") or [{}])[-1].get("date")],
             sorted((k, v.get("month")) for k, v in (s.get("bls") or {}).items()),
             sorted(f["accession"] for f in (s.get("edgar") or [])),
             sorted(f["title"] for f in (s.get("fed") or [])),
             [((s.get("fred") or {}).get("NASDAQ100") or {}).get("observations", [{}])[-1].get("date")]]
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


# ---------- main run ----------
def run(now, slot, slot_date, force):
    for d in (POSTS_DIR, BRIEFS_DIR, SNAP_DIR, SITE_DIR):
        d.mkdir(parents=True, exist_ok=True)
    runs = load_json(RUNS_FILE, {"done": {}, "last_fingerprint": None, "log": []})

    print("1/6 Cboe Insights…")
    new_posts, cboe_status = refresh_posts()
    print("    " + cboe_status["detail"])
    print("2/6 Data sources…")
    s = sources.gather(now)
    s["status"] = {"cboe": cboe_status, **s["status"]}
    for k, st in s["status"].items():
        print(scrub("    %-8s %s  %s" % ("ok" if st["ok"] else "FAILED", st["name"], st["detail"])))

    print("3/6 Price history and forecast grading…")
    ndx_hist, vix_hist, hist_err = {}, {}, None
    try:
        ndx_hist = sources.fred_history("NASDAQ100")
        vix_hist = sources.fred_history("VIXCLS")
    except Exception as e:
        hist_err = str(e)[:120]
        print("    ! history unavailable: %s" % hist_err, file=sys.stderr)
    s["status"]["history"] = {"name": "Price history for grading and base rates", "ok": bool(ndx_hist and vix_hist),
                              "detail": "%d Nasdaq-100 closes since %s" % (len(ndx_hist), min(ndx_hist)) if ndx_hist else (hist_err or "empty")}
    ledger = scoring.Ledger(LEDGER_FILE)
    graded = ledger.resolve(ndx_hist) if ndx_hist else []
    print("    graded %d forecast(s); %d open" % (len(graded), sum(x["status"] == "open" for x in ledger.items)))
    vix_now = None
    for src in ((s.get("cboe_idx") or {}).get("VIX", {}).get("observations"), ((s.get("fred") or {}).get("VIXCLS") or {}).get("observations")):
        if src:
            vix_now = src[-1]["value"]; break
    if vix_now is None and vix_hist:
        vix_now = vix_hist[max(vix_hist)]
    rates = scoring.base_rates(ndx_hist, vix_hist, vix_now) if (ndx_hist and vix_hist and vix_now) else None

    fp = fingerprint(new_posts, s)
    should_call = force or slot == "daily" or fp != runs.get("last_fingerprint")
    key_present = bool(os.environ.get("ANTHROPIC_API_KEY"))
    today_v = now.astimezone(VIENNA).strftime("%Y-%m-%d")
    snap = SNAP_DIR / ("%s-%s.json" % (today_v, slot))
    save_json(snap, s)

    fact_list = facts.build_facts(s)
    checks = facts.disagreements(s)
    brief = None
    if not should_call:
        print("4/6 Nothing new since the last run: skipping the AI call (saves money).")
    elif not key_present:
        print("4/6 ANTHROPIC_API_KEY not set: skipping the AI call. The site still shows data, grading and source health.")
    else:
        try:
            brief = make_brief(now, slot, today_v, new_posts, s, ledger, fact_list, rates, vix_now, ndx_hist, vix_hist)
            runs["last_fingerprint"] = fp
            s["status"]["ai"] = {"name": "Claude brief", "ok": True, "detail": "brief %s written" % brief["id"]}
            if os.environ.get("DISCORD_WEBHOOK_URL", "").strip():
                try:
                    ok_n = sum(1 for v in s["status"].values() if v["ok"])
                    res = discord.post(brief, ok_n, len(s["status"]), scrub)
                    s["status"]["discord"] = {"name": "Discord post", "ok": True, "detail": res}
                except Exception as e:
                    s["status"]["discord"] = {"name": "Discord post", "ok": False, "detail": scrub(str(e))[:160]}
                print("    Discord: %s" % s["status"]["discord"]["detail"])
        except SystemExit:
            raise
        except Exception as e:
            brief = None
            print(scrub("    ! brief failed: %s" % e), file=sys.stderr)
            s["status"]["ai"] = {"name": "Claude brief", "ok": False, "detail": scrub(str(e))[:160]}

    ledger.save()
    runs["done"][slot] = slot_date
    runs["log"] = (runs.get("log", []) + [{"utc": now.isoformat(), "slot": slot, "ai_call": bool(brief),
                                           "sources_ok": sum(1 for v in s["status"].values() if v["ok"]),
                                           "sources_total": len(s["status"])}])[-200:]
    RUNS_FILE.write_text(json.dumps(runs, indent=1))
    save_json(DATA / "latest_status.json", {"utc": now.isoformat(), "slot": slot, "status": s["status"],
                                                          "facts": fact_list, "checks": checks, "rates": rates,
                                                          "ndx_recent": [[d, ndx_hist[d]] for d in sorted(ndx_hist)[-30:]] if ndx_hist else [],
                                                          "calendar": s.get("calendar"), "consensus": s.get("consensus"), "earnings": s.get("earnings"),
                                                          "edgar": s.get("edgar"), "fed": s.get("fed"), "odds": s.get("odds"),
                                                          "headlines": s.get("headlines"), "gdelt": s.get("gdelt"),
                                                          "warnings": s.get("warnings")})
    prune_snapshots(now)
    print("5/6 Building the website…")
    sitegen.build(DATA, SITE_DIR)
    print("6/6 Done. Open site/index.html")


def undash(x):
    """Replace em and en dashes in Claude's text with plain punctuation."""
    if isinstance(x, str):
        x = re.sub(r"\s*[\u2014\u2013]\s*", ", ", x).replace(" -- ", ", ")
        x = re.sub(r"(?i)^(per|according to) (cboe|fred)[^,]*,\s*", "", x)
        x = re.sub(r"(?i)[,;]? (per|according to) (cboe|fred)\b[^,.;]*", "", x)
        x = re.sub(r"(?i)\b(cboe|fred) (says|shows|notes|reports|writes) (that )?", "", x)
        return re.sub(r"(^|[.!?] )([a-z])", lambda m: m.group(1) + m.group(2).upper(), x)
    if isinstance(x, list):
        return [undash(v) for v in x]
    if isinstance(x, dict):
        return {k: undash(v) for k, v in x.items()}
    return x


def make_brief(now, slot, today_v, new_posts, s, ledger, fact_list, rates, vix_now, ndx_hist, vix_hist):
    """One AI call (plus at most one repair call). Saves the brief and its forecasts. Returns the brief."""
    if True:
        print("4/6 Asking Claude for the brief…")
        memory = load_json(MEMORY_FILE, {"running_thesis": "", "open_questions": [], "themes": {}})
        posts = posts_for_prompt(new_posts, (s["status"].get("cboe") or {}).get("latest"))
        ctx = {"now": now, "slot": slot, "ref_date": scoring.last_completed_session(now.astimezone(NEW_YORK)),
               "memory": memory, "briefs": recent_briefs(BRIEFS_IN_CONTEXT), "ledger_text": ledger.prompt_block(),
               "facts": fact_list, "rates": rates, "structured": s, "posts": posts}
        prompt = build_prompt(ctx)
        messages = [{"role": "user", "content": prompt}]
        brief, raw, usage = call_claude(messages)

        texts = [p.get("text", "") for p in posts] + [prompt]
        allowed = facts.allowed_numbers(texts, fact_list)
        flags = facts.check_numbers(brief, allowed, thresholds_and_probs(brief))
        if flags:
            print("    %d number(s) not found in the inputs; asking Claude to fix them once…" % len(flags))
            fix = ("These numbers in your JSON do not appear in the inputs: %s. Return the complete JSON again with "
                   "each one removed or replaced by the exact value from the inputs. Change nothing else."
                   % json.dumps([f["number"] + " in: " + f["context"] for f in flags])[:3000])
            try:
                b2, _, u2 = call_claude(messages + [{"role": "assistant", "content": raw}, {"role": "user", "content": fix}])
                brief = b2
                usage = {k: usage.get(k, 0) + u2.get(k, 0) for k in set(usage) | set(u2) if isinstance(usage.get(k, 0), int)}
                flags = facts.check_numbers(brief, allowed, thresholds_and_probs(brief))
            except Exception as e:
                print("    ! repair call failed: %s" % e, file=sys.stderr)

        brief = undash(brief)
        bid = "%s-%s" % (today_v, slot)
        brief.update({"id": bid, "slot": slot, "slot_label": SLOTS.get(slot, {}).get("label", "Manual run"),
                      "made_utc": now.isoformat(), "ref_date": ctx["ref_date"], "model": MODEL, "usage": usage,
                      "number_flags": flags, "posts_used": [{"title": p.get("title"), "url": p.get("url"),
                                                             "date": (p.get("published") or "")[:10], "text_source": p.get("text_source"),
                                                             "older": p.get("_tag") == "older", "tag": p.get("_tag", "")} for p in posts]})
        added = ledger.record(bid, now.isoformat(), ctx["ref_date"], brief.get("outlook"), vix_now, ndx_hist, vix_hist)
        hp = {x["horizon"]: x.get("history_probs") for x in added}
        for h, o in (brief.get("outlook") or {}).items():
            o["history_probs"] = hp.get(h)
            o["probs_normalized"] = scoring.normalize(o.get("scenarios", []))
        mu = brief.get("memory_update") or {}
        memory.update({"running_thesis": mu.get("running_thesis", memory["running_thesis"]),
                       "open_questions": mu.get("open_questions", memory["open_questions"])})
        memory["themes"].update(mu.get("themes") or {})
        MEMORY_FILE.write_text(json.dumps(memory, indent=1))
        save_json(BRIEFS_DIR / ("%s.json" % bid), brief)
        print("    brief %s: %d unsourced number flag(s), tokens in/out %s/%s" % (
            bid, len(flags), usage.get("input_tokens"), usage.get("output_tokens")))
        return brief


def prune_snapshots(now):
    cutoff = (now - timedelta(days=KEEP_SNAPSHOT_DAYS)).strftime("%Y-%m-%d")
    for f in SNAP_DIR.glob("*.json"):
        if f.name[:10] < cutoff:
            f.unlink()


def check():
    now = datetime.now(timezone.utc)
    rows = []
    try:
        items = parse_rss(http_get(RSS_URL))
        rows.append(("Cboe Insights RSS", bool(items), "%d posts in feed" % len(items)))
    except Exception as e:
        rows.append(("Cboe Insights RSS", False, str(e)[:100]))
    for cat, url in CATEGORY_PAGES.items():
        try:
            n = len(set(re.findall(r'/insights/posts/([a-z0-9][a-z0-9\-]+)', http_get(url))))
            rows.append(("Cboe page: " + cat, n > 0, "%d post links" % n))
        except Exception as e:
            rows.append(("Cboe page: " + cat, False, str(e)[:100]))
    for st in sources.gather(now)["status"].values():
        rows.append((st["name"], st["ok"], st["detail"]))
    try:
        h = sources.fred_history("NASDAQ100", "2024-01-01")
        rows.append(("FRED price history", bool(h), "%d closes" % len(h)))
    except Exception as e:
        rows.append(("FRED price history", False, str(e)[:100]))
    rows.append(("Anthropic API key", bool(os.environ.get("ANTHROPIC_API_KEY")), "set" if os.environ.get("ANTHROPIC_API_KEY") else "not set"))
    rows.append(("FRED API key", bool(os.environ.get("FRED_API_KEY")), "set" if os.environ.get("FRED_API_KEY") else "not set (CSV fallback, no release calendar)"))
    rows.append(("Contact email", bool(os.environ.get("CONTACT_EMAIL")), "set" if os.environ.get("CONTACT_EMAIL") else "not set (SEC and BLS may refuse)"))
    w = max(len(r[0]) for r in rows)
    for name, ok, detail in rows:
        print("%-8s%-*s  %s" % ("WORKING" if ok else "FAILED", w, name, detail))
    print("\n%d of %d working. Failed sources are skipped automatically and shown on the site." % (sum(r[1] for r in rows), len(rows)))


def report(ran):
    """Tell the GitHub workflow whether to save and publish (skipped when nothing ran)."""
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write("ran=%s\n" % ("true" if ran else "false"))


def main():
    now = datetime.now(timezone.utc)
    if "--check" in sys.argv:
        return check()
    if "--site" in sys.argv:
        SITE_DIR.mkdir(parents=True, exist_ok=True)
        sitegen.build(DATA, SITE_DIR)
        return print("Site rebuilt in site/")
    if "--scheduled" in sys.argv:
        slot, slot_date = current_slot(now)
        if not slot:
            print("Outside every run slot. Nothing to do.")
            return report(False)
        runs = load_json(RUNS_FILE, {"done": {}})
        if runs.get("done", {}).get(slot) == slot_date:
            print("The %s run already happened today. Nothing to do." % slot)
            return report(False)
        run(now, slot, slot_date, force=False)
        return report(True)
    run(now, "manual", now.astimezone(VIENNA).date().isoformat(), force=True)
    report(True)


if __name__ == "__main__":
    main()
