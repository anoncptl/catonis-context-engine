"""
Testable scenarios, automatic grading (Brier scores) and historical base rates.

Every horizon in a brief is one forecast on a number code can check:
    Nasdaq-100 % change from the reference close to the close N sessions later
      next_day = 1 session, next_week = 5 sessions, next_month = 21 sessions.
The model picks two cut points (lower_pct, upper_pct) and gives probabilities to
    bear: change < lower_pct     base: between     bull: change > upper_pct
Code resolves it from FRED's NASDAQ100 closes and computes the Brier score.

Brier score (3 outcomes): sum of (probability - outcome)^2. 0 is perfect, 2 is worst.
Two baselines are scored on the same forecasts:
    equal odds  : 1/3 each, always 0.667
    history     : how often each bucket happened historically when VIX was in the same range
If the engine does not beat "history", its probabilities add nothing over base rates.
"""
import json, math
from datetime import date, datetime, timedelta
from pathlib import Path

HORIZONS = {"next_day": 1, "next_week": 5, "next_month": 21}
VIX_BUCKETS = [(0, 15, "VIX under 15"), (15, 20, "VIX 15 to 20"), (20, 25, "VIX 20 to 25"), (25, 35, "VIX 25 to 35"), (35, 999, "VIX above 35")]
BUCKET_NAMES = ("bear", "base", "bull")


# ---------- reference session ----------

def last_completed_session(now_ny):
    """Date of the most recent US cash session that has closed (weekends skipped, holidays not)."""
    d = now_ny.date()
    if now_ny.hour < 16 or (now_ny.hour == 16 and now_ny.minute < 15):
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


# ---------- base rates ----------

def vix_bucket(v):
    for lo, hi, name in VIX_BUCKETS:
        if lo <= v < hi:
            return lo, hi, name
    return VIX_BUCKETS[-1]


def forward_changes(ndx, vix, n):
    """[(date, vix_that_day, % change over the next n sessions)] from aligned histories."""
    dates = sorted(ndx)
    out = []
    for i in range(len(dates) - n):
        d = dates[i]
        v = vix.get(d)
        if v is None:
            continue
        out.append((d, v, (ndx[dates[i + n]] / ndx[d] - 1) * 100))
    return out


def _q(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    return round(xs[f] + (xs[c] - xs[f]) * (k - f), 2)


def base_rates(ndx, vix, current_vix):
    """Quantiles of forward Nasdaq-100 changes, overall and for the current VIX range."""
    lo, hi, name = vix_bucket(current_vix)
    out = {"vix_now": current_vix, "regime": name, "since": min(ndx) if ndx else None, "horizons": {}}
    for h, n in HORIZONS.items():
        rows = forward_changes(ndx, vix, n)
        same = [c for _, v, c in rows if lo <= v < hi]
        allc = [c for _, _, c in rows]
        out["horizons"][h] = {
            "sessions": n,
            "same_regime": {"count": len(same), **{"p%d" % int(p * 100): _q(same, p) for p in (0.1, 0.25, 0.5, 0.75, 0.9)}},
            "all": {"count": len(allc), **{"p%d" % int(p * 100): _q(allc, p) for p in (0.1, 0.25, 0.5, 0.75, 0.9)}},
        }
    return out


def history_probs(ndx, vix, current_vix, n, lower, upper):
    """Historical frequency of bear/base/bull for these cut points, same VIX range."""
    lo, hi, _ = vix_bucket(current_vix)
    same = [c for _, v, c in forward_changes(ndx, vix, n) if lo <= v < hi]
    if len(same) < 30:
        return None
    bear = sum(c < lower for c in same) / len(same)
    bull = sum(c > upper for c in same) / len(same)
    return {"bear": round(bear * 100, 1), "base": round((1 - bear - bull) * 100, 1), "bull": round(bull * 100, 1), "n": len(same)}


# ---------- forecasts ----------

def brier(probs, outcome):
    return round(sum(((probs[k] / 100.0) - (1.0 if k == outcome else 0.0)) ** 2 for k in BUCKET_NAMES), 4)


def normalize(scen):
    """Map the model's scenarios to bear/base/bull probabilities summing to 100."""
    p = {k: 0.0 for k in BUCKET_NAMES}
    for s in scen:
        n = str(s.get("name", "")).lower()
        if n in p:
            try:
                p[n] = max(0.0, float(s.get("prob", 0)))
            except (TypeError, ValueError):
                pass
    tot = sum(p.values())
    if tot <= 0:
        return {k: round(100 / 3, 1) for k in BUCKET_NAMES}
    return {k: round(v * 100 / tot, 1) for k, v in p.items()}


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.items = json.loads(self.path.read_text()) if self.path.exists() else []

    def save(self):
        self.path.write_text(json.dumps(self.items, indent=1))

    def record(self, brief_id, made_utc, ref_date, outlook, vix_now, ndx_hist, vix_hist):
        """Store one forecast per (reference session, horizon). A later run for the same session replaces
        the earlier one, so the scored forecast is the last one made before that session's result."""
        added = []
        for h, n in HORIZONS.items():
            o = (outlook or {}).get(h) or {}
            try:
                lo, up = float(o["lower_pct"]), float(o["upper_pct"])
            except (KeyError, TypeError, ValueError):
                continue
            if lo >= up:
                lo, up = up, lo
            probs = normalize(o.get("scenarios", []))
            hist = history_probs(ndx_hist, vix_hist, vix_now, n, lo, up) if (ndx_hist and vix_hist and vix_now) else None
            item = {"id": "%s|%s" % (ref_date, h), "brief": brief_id, "made_utc": made_utc, "horizon": h, "sessions": n,
                    "metric": "Nasdaq-100 % change", "ref_date": ref_date, "lower_pct": lo, "upper_pct": up,
                    "probs": probs, "history_probs": hist, "status": "open"}
            self.items = [x for x in self.items if not (x["id"] == item["id"] and x["status"] == "open")]
            if any(x["id"] == item["id"] for x in self.items):
                continue  # already resolved: never rewrite history
            self.items.append(item)
            added.append(item)
        return added

    def resolve(self, ndx_hist):
        """Grade every open forecast whose outcome is now in the data."""
        dates = sorted(ndx_hist)
        done = []
        for x in self.items:
            if x["status"] != "open":
                continue
            base = [d for d in dates if d <= x["ref_date"]]
            if not base:
                continue
            ref = base[-1]
            after = [d for d in dates if d > x["ref_date"]]
            if len(after) < x["sessions"]:
                continue
            end = after[x["sessions"] - 1]
            chg = (ndx_hist[end] / ndx_hist[ref] - 1) * 100
            outcome = "bear" if chg < x["lower_pct"] else ("bull" if chg > x["upper_pct"] else "base")
            x.update({"status": "resolved", "ref_close": ndx_hist[ref], "end_date": end, "end_close": ndx_hist[end],
                      "change_pct": round(chg, 2), "outcome": outcome, "brier": brier(x["probs"], outcome),
                      "brier_equal": brier({k: 100 / 3 for k in BUCKET_NAMES}, outcome),
                      "brier_history": brier(x["history_probs"], outcome) if x.get("history_probs") else None})
            done.append(x)
        return done

    def summary(self):
        res = [x for x in self.items if x["status"] == "resolved"]
        out = {"open": sum(x["status"] == "open" for x in self.items), "resolved": len(res), "by_horizon": {}}
        for h in HORIZONS:
            r = [x for x in res if x["horizon"] == h]
            if not r:
                continue
            hb = [x["brier_history"] for x in r if x.get("brier_history") is not None]
            hit = sum(max(x["probs"], key=x["probs"].get) == x["outcome"] for x in r)
            out["by_horizon"][h] = {
                "n": len(r), "brier": round(sum(x["brier"] for x in r) / len(r), 3),
                "brier_equal": round(sum(x["brier_equal"] for x in r) / len(r), 3),
                "brier_history": round(sum(hb) / len(hb), 3) if hb else None,
                "top_pick_right": hit}
        out["recent"] = sorted(res, key=lambda x: x["end_date"], reverse=True)[:12]
        return out

    def prompt_block(self):
        s = self.summary()
        lines = ["Forecasts are graded by code, not by you. Resolved so far: %d, open: %d." % (s["resolved"], s["open"])]
        for h, v in s["by_horizon"].items():
            lines.append("%s: n=%d, your Brier %.3f vs equal-odds %.3f vs history %s (lower is better); top pick right %d/%d" % (
                h, v["n"], v["brier"], v["brier_equal"], "%.3f" % v["brier_history"] if v["brier_history"] is not None else "n/a",
                v["top_pick_right"], v["n"]))
        for x in s["recent"][:6]:
            lines.append("- %s %s: cut points %.2f/%.2f, probs %s, actual %+.2f%% -> %s, Brier %.3f" % (
                x["ref_date"], x["horizon"], x["lower_pct"], x["upper_pct"], x["probs"], x["change_pct"], x["outcome"], x["brier"]))
        return "\n".join(lines)
