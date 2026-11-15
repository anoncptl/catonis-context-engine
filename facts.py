"""
Facts table, cross-source checks and the unsourced-number check.

Every number the engine shows is a fact with a value, unit, as-of date and source.
The model may only use numbers that appear in its inputs. After the model answers,
check_numbers() lists any figure in the brief that matches nothing it was given.
"""
import json, re

# ---------- facts ----------

def _last(obs):
    return obs[-1] if obs else None


def build_facts(s):
    """Flat list of facts from the structured data. Code computes every value."""
    F = []

    def add(label, value, unit, as_of, source, change=None, group="Markets"):
        if value is None:
            return
        F.append({"id": "F%d" % (len(F) + 1), "group": group, "label": label, "value": value, "unit": unit,
                  "change": change, "as_of": as_of, "source": source})

    tr = (s.get("treasury") or [])
    if tr:
        t = tr[-1]
        for tenor, lab in (("2 Yr", "2-year Treasury yield"), ("10 Yr", "10-year Treasury yield"), ("30 Yr", "30-year Treasury yield")):
            if tenor in t:
                ch = t.get(tenor + " chg_bp")
                add(lab, t[tenor], "%", t["date"], "US Treasury", None if ch is None else "%+.1f bp" % ch, "Rates")
    fred = s.get("fred") or {}
    order = [("NASDAQ100", "Markets"), ("SP500", "Markets"), ("VIXCLS", "Volatility"), ("VXNCLS", "Volatility"),
             ("DFII10", "Rates"), ("T10YIE", "Rates"), ("T10Y2Y", "Rates"), ("BAMLH0A0HYM2", "Credit"),
             ("DCOILBRENTEU", "Commodities"), ("DCOILWTICO", "Commodities")]
    if not tr:
        order += [("DGS2", "Rates"), ("DGS10", "Rates")]
    cb_have = set((s.get("cboe_idx") or {}))
    for sid, grp in order:
        if sid not in fred or (sid == "VIXCLS" and "VIX" in cb_have) or (sid == "VXNCLS" and "VXN" in cb_have):
            continue  # same number from Cboe is shown; FRED's copy is used for the cross-check
        o = _last(fred[sid]["observations"])
        ch = "%+.2f%%" % o["chg_pct"] if "chg_pct" in o else ("%+.1f bp" % o["chg_bp"] if "chg_bp" in o else None)
        add(fred[sid]["description"], o["value"], fred[sid].get("unit", ""), o["date"], "FRED " + sid, ch, grp)
    for sym, d in (s.get("cboe_idx") or {}).items():
        if sym == "VIX" and "VIXCLS" in fred:
            pass  # keep both: they are cross-checked below
        o = _last(d["observations"])
        ch = "%+.2f%%" % o["chg_pct"] if "chg_pct" in o else None
        add(d["description"], o["value"], "index", o["date"], "Cboe " + sym, ch, "Volatility")
    for sid, b in (s.get("bls") or {}).items():
        if "mom_pct" in b:
            add(b["description"] + ", m/m", b["mom_pct"], "%", b["month"], "BLS " + sid,
                None if b.get("prev_mom_pct") is None else "prior %+.2f%%" % b["prev_mom_pct"], "Macro prints")
            if b.get("yoy_pct") is not None:
                add(b["description"] + ", y/y", b["yoy_pct"], "%", b["month"], "BLS " + sid, None, "Macro prints")
        elif "change" in b:
            add(b["description"] + ", monthly change", b["change"], "k", b["month"], "BLS " + sid, None, "Macro prints")
        else:
            add(b["description"], b["value"], "%", b["month"], "BLS " + sid,
                None if b.get("previous") is None else "prior %s" % b["previous"], "Macro prints")
    for sid, m in (s.get("fred_monthly") or {}).items():
        add(m["label"] + ", m/m", m["mom_pct"], "%", m["month"], "FRED " + sid, None, "Macro prints")
        add(m["label"] + ", y/y", m["yoy_pct"], "%", m["month"], "FRED " + sid, None, "Macro prints")
    for ev in (s.get("odds") or []):
        for mk in ev["markets"][:4]:
            add("%s: %s" % (ev["event"][:60], mk["outcome"][:40]), mk["prob_pct"], "% implied", ev.get("close") or "open",
                ev["venue"], None, "Fed odds")
    rel = relative_strength(fred)
    if rel:
        add("Nasdaq-100 minus S&P 500, last session", rel["d1"], "pct pts", rel["date"], "computed from FRED", None, "Leadership")
        if rel.get("d5") is not None:
            add("Nasdaq-100 minus S&P 500, last 5 sessions", rel["d5"], "pct pts", rel["date"], "computed from FRED", None, "Leadership")
    cb = s.get("cboe_idx") or {}
    vxn = _last(cb.get("VXN", {}).get("observations", []) or (fred.get("VXNCLS") or {}).get("observations", []))
    vix = _last(cb.get("VIX", {}).get("observations", []) or (fred.get("VIXCLS") or {}).get("observations", []))
    if vxn and vix and vxn["date"] == vix["date"]:
        add("VXN minus VIX", round(vxn["value"] - vix["value"], 2), "pts", vix["date"], "computed from Cboe/FRED", None, "Leadership")
    return F


def relative_strength(fred):
    a = {o["date"]: o["value"] for o in (fred.get("NASDAQ100") or {}).get("observations", [])}
    b = {o["date"]: o["value"] for o in (fred.get("SP500") or {}).get("observations", [])}
    common = sorted(set(a) & set(b))
    if len(common) < 2:
        return None
    d, p = common[-1], common[-2]
    out = {"date": d, "d1": round((a[d] / a[p] - b[d] / b[p]) * 100, 2) + 0.0, "d5": None}
    if len(common) >= 6:
        q = common[-6]
        out["d5"] = round((a[d] / a[q] - b[d] / b[q]) * 100, 2) + 0.0
    return out


def facts_prompt(facts):
    return "\n".join("%s | %s | %s %s%s | as of %s | %s" % (
        f["id"], f["label"], f["value"], f["unit"], " (" + f["change"] + ")" if f["change"] else "", f["as_of"], f["source"])
        for f in facts)


# ---------- cross-source checks ----------

def disagreements(s):
    """Compare the same number from two sources on the same date."""
    out = []
    fred = s.get("fred") or {}
    tr = {r["date"]: r for r in (s.get("treasury") or [])}
    for sid, tenor, lab in (("DGS10", "10 Yr", "10-year yield"), ("DGS2", "2 Yr", "2-year yield")):
        for o in (fred.get(sid) or {}).get("observations", [])[-3:]:
            t = tr.get(o["date"], {}).get(tenor)
            if t is not None:
                diff = abs(t - o["value"]) * 100
                out.append({"what": lab, "date": o["date"], "a": "%.2f%% (Treasury)" % t, "b": "%.2f%% (FRED)" % o["value"],
                            "agree": diff <= 3, "note": "%.1f bp apart" % diff})
    cb = {o["date"]: o["value"] for o in ((s.get("cboe_idx") or {}).get("VIX") or {}).get("observations", [])}
    for o in (fred.get("VIXCLS") or {}).get("observations", [])[-3:]:
        if o["date"] in cb:
            diff = abs(cb[o["date"]] - o["value"])
            out.append({"what": "VIX close", "date": o["date"], "a": "%.2f (Cboe)" % cb[o["date"]],
                        "b": "%.2f (FRED)" % o["value"], "agree": diff <= 0.1, "note": "%.2f apart" % diff})
    cbx = {o["date"]: o["value"] for o in ((s.get("cboe_idx") or {}).get("VXN") or {}).get("observations", [])}
    for o in (fred.get("VXNCLS") or {}).get("observations", [])[-3:]:
        if o["date"] in cbx:
            diff = abs(cbx[o["date"]] - o["value"])
            out.append({"what": "VXN close", "date": o["date"], "a": "%.2f (Cboe)" % cbx[o["date"]],
                        "b": "%.2f (FRED)" % o["value"], "agree": diff <= 0.1, "note": "%.2f apart" % diff})
    # BLS CPI vs FRED-distributed values are the same publication, so no check there.
    return out


# ---------- unsourced numbers ----------
NUM_RE = re.compile(r"(?<![\w.])[-+−]?\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])[-+−]?\$?\d+(?:\.\d+)?")
SKIP_KEYS = {"prob", "lower_pct", "upper_pct", "date", "when_vienna", "id", "name", "confidence"}


def _variants(x):
    """Ways a number may legitimately be written."""
    out = set()
    for d in (0, 1, 2, 3):
        r = round(abs(x), d)
        out.add(("%." + str(d) + "f") % r)
        out.add(("{:,.%df}" % d).format(r))
    out.add(str(abs(x)))
    return {v.rstrip("0").rstrip(".") if "." in v else v for v in out} | out


def allowed_numbers(texts, facts):
    allowed = set()
    for f in facts:
        if isinstance(f["value"], (int, float)):
            allowed |= _variants(float(f["value"]))
        for m in NUM_RE.findall(str(f.get("change") or "")):
            allowed.add(_clean(m))
    for t in texts:
        for m in NUM_RE.findall(t or ""):
            c = _clean(m)
            allowed.add(c)
            x = _to_float(c)
            if x is not None:
                allowed |= _variants(x)
    return allowed


def _clean(tok):
    return tok.replace("−", "").replace("+", "").replace("-", "").replace("$", "").strip()


def _to_float(tok):
    try:
        return float(tok.replace(",", ""))
    except ValueError:
        return None


def _strings(obj, key=None):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k not in SKIP_KEYS:
                yield from _strings(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v, key)
    elif isinstance(obj, str):
        yield key, obj


def check_numbers(brief, allowed, thresholds=()):
    """Return [{number, context}] for figures in the brief that match nothing in the inputs."""
    allowed = set(allowed) | {_clean("%g" % t) for t in thresholds}
    flags, seen = [], set()
    for key, text in _strings({k: v for k, v in brief.items() if k not in ("memory_update", "sources_used", "sources_unavailable", "number_flags")}):
        for m in NUM_RE.finditer(text):
            tok = _clean(m.group())
            x = _to_float(tok)
            if x is None:
                continue
            tail = text[m.end(): m.end() + 12].lower()
            head = text[max(0, m.start() - 12): m.start()].lower()
            # ignore small counts, years, dates, times, horizons and probabilities restated from the scenarios
            if x <= 10 and "." not in tok and not re.match(r"\s*(%|bp|basis)", tail):
                continue
            if 1990 <= x <= 2100 and "." not in tok:
                continue
            if re.match(r"\s*(:|h\b|am|pm|et\b|cet|vienna|nov|dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct)", tail):
                continue
            if re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*$", head) or head.endswith(":"):
                continue
            if re.match(r"\s*(day|days|session|sessions|week|weeks|month|months|year|years|-day|-week)", tail):
                continue
            if tok in allowed or (x is not None and any(v in allowed for v in _variants(x))):
                continue
            k = (tok, text[:40])
            if k in seen:
                continue
            seen.add(k)
            a, b = max(0, m.start() - 60), min(len(text), m.end() + 40)
            flags.append({"number": m.group(), "field": key, "context": ("…" if a else "") + text[a:b] + ("…" if b < len(text) else "")})
    return flags
