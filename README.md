# Context Engine

Your daily market context for NQ, built from free public sources, refreshed automatically once every weekday at 08:30 New York time (14:30 CET), published as a private-link web page you can open on your phone.

You do not need to code. You will click, copy and paste. It takes about 30 to 45 minutes once.

---

## What it does

Once every weekday, and whenever you run it by hand, it:

1. Reads Cboe Insights (daily market take, weekly volatility digest, all insights).
2. Pulls official data: US Treasury yields, FRED (real yields, credit spread, oil, VIX, VXN, PCE), BLS (CPI, PPI, jobs), the official BLS, FRED and FOMC calendars, SEC 8-K filings from the 10 largest Nasdaq-100 companies, Fed releases, Cboe volatility indexes (VIX, VXN, VVIX, SKEW, VIX9D, COR1M if published), Fed odds from Kalshi and Polymarket, and headlines from GDELT and Google News.
3. Asks Claude for a brief: what happened, dominant driver, QQQ or SPX leading, scheduled events in CET, and three testable scenarios.
4. Checks every number in the brief against its sources. Anything it cannot match is sent back to Claude once to fix, and anything still unmatched is flagged on the page.
5. Grades older scenarios automatically with Brier scores and compares them with history.
6. Publishes the page and saves its memory.

Run time: Monday to Friday at 08:30 New York time, which is 14:30 CET (13:30 CET for a few weeks in March and around late October, when the US and Europe change clocks on different dates). A scheduled task starts it at that time. GitHub's own timer fires a few backup times until about 16:50 CET in case that start is missed; it still runs only once a day. You can run it any time by hand: Actions, Context Engine, Run workflow.
