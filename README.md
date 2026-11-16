# Context Engine

Your daily market context for NQ, built from free public sources, refreshed automatically three times every weekday, published as a private-link web page you can open on your phone.

You do not need to code. You will click, copy and paste. It takes about 30 to 45 minutes once.

---

## What it does

Three times every weekday it:

1. Reads Cboe Insights (daily market take, weekly volatility digest, all insights).
2. Pulls official data: US Treasury yields, FRED (real yields, credit spread, oil, VIX, VXN, PCE), BLS (CPI, PPI, jobs), the official BLS, FRED and FOMC calendars, SEC 8-K filings from the 10 largest Nasdaq-100 companies, Fed releases, Cboe volatility indexes (VIX, VXN, VVIX, SKEW, VIX9D, COR1M if published), Fed odds from Kalshi and Polymarket, and headlines from GDELT and Google News.
3. Asks Claude for a brief: what happened, dominant driver, QQQ or SPX leading, scheduled events in CET, and three testable scenarios.
4. Checks every number in the brief against its sources. Anything it cannot match is sent back to Claude once to fix, and anything still unmatched is flagged on the page.
5. Grades older scenarios automatically with Brier scores and compares them with history.
6. Publishes the page and saves its memory.

Run times (Monday to Friday, GitHub may start them 5 to 30 minutes late):

| Run | CET | Why |
|---|---|---|
| Morning | about 06:30 to 07:30 | overnight news, weekly digest on Mondays |
| Pre-open | about 14:40 | after the 08:30 New York data releases, before the 15:30 open. Only calls Claude if something new arrived. |
| Evening | about 23:30 | after the US close, when Cboe's daily take is out |

---

## What you need

| Thing | Cost | Needed? |
|---|---|---|
| GitHub account | free | yes |
| Anthropic API key | pay per use, see Costs below | yes |
| FRED API key | free | strongly recommended |
| BLS API key | free | optional |
| Your email address | free | recommended (the SEC and BLS ask scripts for a contact address) |

---

## Step 1: Create a GitHub account

1. Go to **github.com/signup**.
2. Enter your email, a password and a username. Remember the username, it becomes part of your page address.
3. Verify your email.

## Step 2: Create the repository

A repository is a folder on GitHub that holds the engine.

1. When logged in, click the **+** in the top right, then **New repository**.
2. **Repository name:** `context-engine`
3. Choose **Public**. (Free GitHub only publishes pages from public repositories. Your API keys stay secret either way. See "Privacy" below.)
4. Leave every other option unticked.
5. Click **Create repository**.

## Step 3: Upload the files

1. Unzip `context-engine.zip` on your Mac (double-click it).
2. Open the unzipped `context-engine` folder in Finder.
3. Press **Cmd + Shift + .** (Command, Shift, full stop). This shows hidden files. You should now see a faded folder called **.github**. It holds the schedule, so it must be uploaded.
4. On the new repository page on GitHub, click the link **uploading an existing file**.
5. Select **everything inside** the `context-engine` folder (Cmd + A), including `.github`, and drag it onto the GitHub page. Use **Chrome**: Safari does not always upload folders.
6. Wait until all files are listed, then click **Commit changes** at the bottom.
7. Check: the repository page should now list `.github`, `context_engine.py`, `sources.py`, `facts.py`, `scoring.py`, `sitegen.py` and `README.md`.

If `.github` is missing after uploading, do this instead:

1. In the repository, click **Add file**, then **Create new file**.
2. In the name box type exactly: `.github/workflows/daily.yml` (the slashes create the folders).
3. Open `.github/workflows/daily.yml` from the zip in TextEdit, copy everything, paste it into GitHub.
4. Click **Commit changes**.

## Step 4: Get your keys

### Anthropic API key (required)

1. Go to **console.anthropic.com** and sign up.
2. Click **Billing** and add a payment method and some credit (5 dollars lasts a while).
3. Click **Limits** and set a **monthly spend limit**, for example 15 dollars. This is your safety net.
4. Click **API Keys**, then **Create Key**, name it `context-engine`, and copy the key. It starts with `sk-ant-`. You only see it once, so paste it somewhere temporary.

### FRED API key (free, strongly recommended)

1. Go to **fredaccount.stlouisfed.org**, create an account and log in.
2. Click **API Keys**, then **Request API Key**, write one sentence like "personal market research", and submit.
3. Copy the key (32 letters and numbers).

Without it the engine still works but has no BEA release calendar and uses a slower download.

### BLS API key (free, optional)

1. Go to **data.bls.gov/registrationEngine/** and register with your email.
2. Click the link in the email you receive. The key is in that email.

Without it the engine uses BLS's keyless access, which allows fewer requests per day. Three runs a day fit, so this is optional.

## Step 5: Store the keys as secrets

Secrets are stored encrypted. Nobody, including visitors to your public repository, can see them.

1. In your repository click **Settings** (top menu, gear icon).
2. In the left menu click **Secrets and variables**, then **Actions**.
3. Click **New repository secret** and add each of these. The name must match exactly, in capitals:

| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your `sk-ant-...` key |
| `FRED_API_KEY` | your FRED key |
| `BLS_API_KEY` | your BLS key (skip if you have none) |
| `CONTACT_EMAIL` | your email address |

After each one click **Add secret**.

## Step 6: Allow it to publish and save

1. Still in **Settings**, click **Pages** in the left menu.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.
3. Click **Actions** in the left menu, then **General**.
4. Scroll to **Workflow permissions**, choose **Read and write permissions**, click **Save**.

## Step 7: Run it for the first time

1. Click the **Actions** tab at the top of the repository.
2. If GitHub asks, click **I understand my workflows, go ahead and enable them**.
3. Click **Context Engine** in the left list.
4. Click **Run workflow** on the right, then the green **Run workflow** button.
5. Wait 3 to 6 minutes. A yellow dot means running, a green tick means done, a red cross means something failed (see Troubleshooting).
6. When it is green, go to **Settings**, then **Pages**. Your address is shown at the top, like `https://YOURNAME.github.io/context-engine/`.
7. Open it on your phone and add it to your home screen (Safari: Share, then Add to Home Screen).

A manual run always calls Claude, so each one costs a few cents.

## Step 8: Check the source health table

Scroll to the bottom of the page. **Source health** lists every source as working or failed with a short reason.

Some sources could not be tested before you ran it: Kalshi and Polymarket market names, the Fed's FOMC calendar page, the Treasury download and the BLS calendar. If any show **failed**, send me a screenshot of that table and I will fix it. A failed source is skipped; the rest still work.

## Step 9: Done

From now on it runs by itself. You only open the page.

---

## Reading the page

- **What happened, Dominant driver, Leader** at the top. Leader is QQQ, SPX or unclear, with the numbers it used (Nasdaq-100 minus S&P 500, VXN minus VIX, COR1M when available).
- **Scenarios**: each horizon is a forecast on one number, the Nasdaq-100 change from the reference close to 1, 5 or 21 sessions later. Bear is below the lower cut point, bull is above the upper one, base is between. The grey tick shows how often that outcome happened historically when VIX was in the same range.
- **Numbers check**: says "clean", or lists figures it could not match to a source.
- **Key numbers**: every number with its source and date.
- **Cross-source checks**: the same yield or VIX value from two sources. "DISAGREE" means one of them is off.
- **Official calendar**: next 14 days in CET and New York time.
- **SEC 8-K filings**: leadership changes, results, agreements at the 10 biggest Nasdaq-100 companies.
- **Record** (top menu): every graded scenario. The engine is only adding value if its Brier score is below "History". Give it at least 20 graded forecasts per horizon before judging.
- **Archive**: every past brief.

---

## Costs

- GitHub: free for a public repository.
- Data sources: free.
- Claude: each brief is one or two API calls with a long prompt. Expect a few cents to around 20 cents per brief depending on the model's price, so roughly 3 to 10 dollars a month. Check **Usage** in the Anthropic console after the first week. The spend limit from Step 4 caps it.
- To cut cost: the model is set by `MODEL` near the top of `context_engine.py`. A smaller model is cheaper and weaker.

## Privacy

The repository is public, so anyone who finds it can read the code, the briefs and the page. The page tells search engines not to list it. Your keys are secrets and are never visible. If you want everything private, GitHub Pro (about 4 dollars a month) allows pages from private repositories: switch the repository to private in Settings, General, Danger Zone.

## Changing things without coding

- **Pause it:** Actions tab, Context Engine, the "..." button, **Disable workflow**.
- **Run it now:** Actions tab, Context Engine, **Run workflow**.
- **Change search terms or companies:** open `sources.py` on GitHub, click the pencil icon, edit `GNEWS_QUERIES`, `GDELT_QUERY` or `EDGAR_COMPANIES`, then **Commit changes**. Or ask me and I will send you the exact edit.

GitHub pauses scheduled runs after 60 days without any change to the repository. Each run saves its memory to the repository, which counts as a change, so this should not happen. If it does, GitHub shows a button on the Actions tab to turn it back on.

## Troubleshooting

GitHub emails you when a run fails.

1. Open the **Actions** tab and click the run with the red cross.
2. Click the step with the red cross to open its log.
3. Send me a screenshot of the last 20 lines.

Common causes:

| Message | Fix |
|---|---|
| `ANTHROPIC_API_KEY is not set` | Step 5: check the secret name is exactly `ANTHROPIC_API_KEY` |
| `HTTP 401` from Claude | the key was copied wrongly or deleted, create a new one |
| `HTTP 400 ... credit balance` | add credit in the Anthropic console |
| `Permission denied` or `403` when pushing | Step 6, part 4: Read and write permissions |
| Page shows 404 | Step 6, part 2: Pages source must be GitHub Actions, then run again |

## Running it on your Mac (optional)

1. Open Terminal and go to the folder: `cd ~/Downloads/context-engine` (adjust the path).
2. `python3 context_engine.py --check` tests every source and prints which work. No AI call.
3. To run a full brief locally, set your key first: `export ANTHROPIC_API_KEY="sk-ant-..."`, then `python3 context_engine.py`. Open `site/index.html`.

---

## Files

| File | What it does |
|---|---|
| `context_engine.py` | main program: Cboe, prompt, Claude, run slots |
| `sources.py` | every data source |
| `facts.py` | number table, source checks, unsourced-number check |
| `scoring.py` | testable scenarios, Brier grading, base rates |
| `sitegen.py` | builds the web page |
| `.github/workflows/daily.yml` | the schedule |
| `data/` | memory, briefs, forecasts (created by the first run) |
| `site/` | the published page (created by the first run) |

Not advice. Conditional scenarios from public information, graded honestly.
