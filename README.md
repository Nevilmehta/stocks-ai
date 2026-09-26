# StockAI (private MVP)

A private AI-assisted research platform for Indian stocks. **All 6 planned
MVP phases are complete**: project scaffolding, authentication, roles, a
dashboard, stock search, per-stock detail pages with interactive charts,
financials, technical indicators, a deterministic AI Research Score,
AI-generated research (analysis, chat, comparison, history), a watchlist, a
2-3 way stock comparison tool, a fundamentals screener, and admin analytics.
All data is DEMO DATA - no real market feed is connected, and AI runs on a
deterministic mock provider by default (Gemini is wired up but optional -
see section 8). See section 13 for exactly what to change to connect real
data and a real AI provider.

- Frontend: Next.js (App Router) + TypeScript + Tailwind + shadcn/ui
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Auth: email/password, httpOnly JWT cookie, `user` / `admin` roles
- No public signup - an admin creates accounts (or you seed dev accounts below)

---

## 1. Requirements

- Node.js 20+ and npm
- Python 3.11+
- PostgreSQL 16 (either via the included Docker Compose file, or a native
  local install)
- Docker Desktop is optional, but recommended for the easiest Postgres setup

---

## 2. Get PostgreSQL running

### Option A - Docker (recommended)

From the repository root:

```powershell
docker compose up -d
```

This starts Postgres on `localhost:5433` (mapped from the container's 5432 -
5433 avoids clashing with a native Postgres install on the default port)
with database `stockai`, user `stockai`, password `stockai` (matches the
default `DATABASE_URL` below).

Check it's healthy:

```powershell
docker compose ps
```

You should see `stockai-postgres` with state `Up (healthy)`.

> If `docker compose up -d` fails with a pipe/engine connection error, Docker
> Desktop isn't running yet. Start the Docker Desktop app from the Start
> menu, wait for its whale icon in the system tray to stop animating (first
> boot can take a minute or two), then retry the command.

### Option B - Native PostgreSQL install

If you already have PostgreSQL installed locally, just create a database and
user, then point `DATABASE_URL` (see below) at it:

```powershell
psql -U postgres -c "CREATE USER stockai WITH PASSWORD 'stockai';"
psql -U postgres -c "CREATE DATABASE stockai OWNER stockai;"
```

---

## 3. Backend setup (FastAPI)

Open a terminal in `backend/`:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Successful install ends with a line like:
`Successfully installed fastapi-0.115.6 ... uvicorn-0.34.0 ...`

Create your local environment file:

```powershell
Copy-Item ..\.env.example .env
```

The defaults in `.env.example` already match the Docker Compose Postgres
instance, so no edits are required for local development. Leave
`SEED_ADMIN_PASSWORD` / `SEED_DEMO_PASSWORD` blank to get random generated
passwords (recommended), or set them to fixed values if you prefer.

Create the database tables and seed demo data:

```powershell
python scripts/init_db.py
python scripts/seed_data.py
python scripts/seed_market_data.py
```

`seed_data.py` prints the admin/demo login credentials **once** - copy them
somewhere safe. Example output:

```
[created] admin@example.com / role=admin / password=Xy93k... (generated - save this now)
[created] demo@example.com / role=user / password=Ab12c... (generated - save this now)
[created] RELIANCE - Reliance Industries Ltd
...
```

`seed_market_data.py` generates 5 years of daily OHLCV price history plus 5
years of annual and 8 quarters of quarterly financials/ratios for each
company (deterministic per-symbol, so it's the same data every run). Expect
output like:

```
[created] RELIANCE: 1305 price rows, 13 financial periods, 13 ratio periods (latest close Rs.1171.6)
...
```

Both seed scripts are idempotent - re-running them skips anything already
seeded rather than duplicating it.

Run the test suite (uses an in-memory SQLite database, so it does not
require Postgres to be running):

```powershell
python -m pytest -v
```

Expected: `74 passed` (or however many tests exist as the project grows).

Start the API server:

```powershell
uvicorn app.main:app --reload --port 8000
```

Successful output ends with:
`Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)`

Verify it's alive by opening http://localhost:8000/api/health in a browser -
you should see `{"status":"ok","app_env":"development","market_data_provider":"mock","ai_provider":"mock"}`.
Interactive API docs are at http://localhost:8000/docs.

---

## 4. Frontend setup (Next.js)

Open a **second** terminal in `frontend/`:

```powershell
cd frontend
npm install
```

The environment file `.env.local` is already set to
`NEXT_PUBLIC_API_URL=http://localhost:8000`. If your backend runs elsewhere,
copy `.env.local.example` to `.env.local` and adjust it.

Start the dev server:

```powershell
npm run dev
```

Successful output ends with something like:
`Local: http://localhost:3000`

Open http://localhost:3000 in a browser.

---

## 5. What to test

**Phase 1 - accounts and access**

1. Open http://localhost:3000 - the landing page should render with a hero,
   feature grid, and disclaimer footer.
2. Click **Login**, sign in with the `admin@example.com` credentials printed
   by `seed_data.py`.
3. You should land on `/dashboard` showing a "DEMO DATA" badge, company/
   sector/market-mover counts, AI provider mode, and a searchable table of
   the 15 seeded companies.
4. Open the avatar menu (top right) - as an admin you'll see an **Admin**
   link. Visit `/admin` to see the user list and create a new invited user.
5. Log out, then log back in as `demo@example.com` - you should **not** see
   the Admin link, and visiting `/admin` directly should show "Admin access
   required".
6. Try visiting `/dashboard` in a private/incognito window without logging
   in - you should be redirected to `/login`.

**Phase 2 - stock research**

7. On the dashboard, click any company row (or use the search icon in the
   navbar and type part of a symbol/name/sector) to open `/stocks/<SYMBOL>`.
8. The price chart should render immediately with real (demo) data. Try the
   1M/3M/6M/1Y/3Y/5Y/MAX range buttons and the Line/Candlestick toggle.
9. **Overview** tab: description, market cap, P/E, P/B, ROE, ROCE, EPS,
   Debt/Equity, revenue/profit growth, 52-week high/low.
10. **Financials** tab: toggle Annual/Quarterly, check the revenue/net
    profit/EPS trend charts and the full period table (values in Rs. Cr).
11. **Technicals** tab: Trend/Momentum badges, RSI, MACD, moving averages,
    Bollinger bands, returns, volatility - all neutral research language,
    never "Buy"/"Sell".
12. **Peers** tab: links to other companies in the same sector.

**Phase 3 - AI Research Score**

13. Still on the **Overview** tab, scroll down to the **AI Research Score**
    card: a ring gauge (0-100), a label like "Balanced Research Profile",
    six subscore bars (Financial Strength, Growth, Profitability, Valuation,
    Technical Momentum, and a Risk badge), and a methodology note.
14. Compare a couple of different stocks - the score should genuinely differ
    (e.g. a company with strong growth/low debt scores higher than one with
    weak growth/high debt). Nothing here ever says "Buy" or "Sell".
15. The score is deterministic, not AI-generated - see
    `backend/app/analytics/scoring.py` for the exact formula and weights.

**Phase 4 - AI research**

16. On a stock page, click **AI Analyse** (top right). It switches to the
    **AI Analysis** tab and generates a Summary, Financial Health, Growth,
    Profitability, Valuation, Technical Picture, Strengths, Risks, Things to
    Monitor, Conclusion, and Disclaimer - every number in it should match
    what you see elsewhere on the page (Overview tab, AI Research Score).
    Nothing here ever says "Buy"/"Sell"/"Strong Buy" or gives a target price.
17. Go to **Research** in the navbar (or click a suggested prompt on the
    dashboard). Try: "Analyse Reliance Industries", "Compare TCS and
    Infosys", "Explain Tata Motors financial performance". Compare-style
    prompts (mentioning 2-3 companies) get a side-by-side comparison instead
    of a single analysis.
18. Ask something that doesn't mention a company (e.g. "hello") - you should
    get a clarifying message, not an error or a hallucinated answer.
19. Click **History** - every AI Analyse and chat exchange is saved. Click
    one to reopen the full conversation at `/research?session=<id>`.
20. Log in as a second user (e.g. `demo@example.com`) and confirm you do
    **not** see the admin's research history - it's private per account.

**Phase 5 - watchlist, compare, screener**

21. On any stock page, click **Watchlist** (top right, next to AI Analyse) -
    it should toggle to "In Watchlist" immediately. Go to **Watchlist** in
    the navbar to see it listed with live price, change, P/E, ROE and AI
    Score, and confirm you can add another stock via the search box there
    and remove one with the trash icon.
22. Go to **Compare** (avatar menu). Add 2-3 companies via the search box -
    you should see a normalized price-performance chart (indexed to 0% at
    the start of the window), a full metrics table, and an **AI Compare**
    button that generates a grounded comparison paragraph (never says one
    stock is simply "better").
23. Go to **Screener** (avatar menu). Click the **Example: ROE > 15%, D/E <
    0.5, Rev growth > 10%** preset button - the results should immediately
    narrow to only companies meeting all three thresholds (2 of the 15 seed
    companies match this exact preset). Try the Sector dropdown and other
    numeric filters, then **Reset**.
24. On the dashboard, the **Watchlist** card should now show your actual
    watchlist items (or an empty-state prompt if you haven't added any yet)
    instead of a placeholder.

**Phase 6 - admin analytics and polish**

25. As an admin, open **Admin** - above the user table you should see
    Users/Active users/Research sessions/Research messages stat cards and a
    **Most researched stocks** list (companies mentioned most often across
    everyone's AI Analyse and chat prompts, most-mentioned first).
26. Resize your browser to a phone width (~390px) or use your browser's
    device toolbar - the navbar, dashboard, stock page, watchlist, compare,
    screener, research and admin pages should all stack cleanly with no
    horizontal overflow (wide tables scroll horizontally within their own
    card instead of breaking the page layout).

---

## 6. Demo / admin accounts

Development-only accounts, created by `scripts/seed_data.py`:

| Email               | Role  | Password                                      |
| ------------------- | ----- | ---------------------------------------------- |
| admin@example.com   | admin | printed once by `seed_data.py` (or `SEED_ADMIN_PASSWORD`) |
| demo@example.com    | user  | printed once by `seed_data.py` (or `SEED_DEMO_PASSWORD`)  |

These are **local development credentials only** - never reuse them in a
real deployment. Public self-registration is disabled by default
(`ALLOW_REGISTRATION=false`); an admin creates every account via `/admin` or
`POST /api/admin/users`.

---

## 7. How mock data works today

- **Companies**: 15 well-known NSE large-caps are seeded from
  `backend/app/seed/companies.py` (symbol, name, sector, industry,
  description).
- **Price history, financials & ratios**: `backend/app/seed/market_data.py`
  generates a deterministic (seeded by symbol) random walk for 5 years of
  daily OHLCV, plus 5 annual + 8 quarterly financial statements and derived
  ratios, loaded by `scripts/seed_market_data.py`. Deterministic means the
  same symbol always produces the same numbers - it's not randomized on
  every run.
- **Technical indicators** (SMA/EMA/RSI/MACD/Bollinger/returns/volatility)
  are computed on the fly from that price history in
  `backend/app/analytics/technicals.py` - nothing pre-stored, no external
  API needed.
- **Market data provider**: controlled by `MARKET_DATA_PROVIDER=mock` in
  `.env`. All stock endpoints go through the `MarketDataProvider` interface
  in `backend/app/providers/market_data.py`; `MockMarketDataProvider` reads
  the seeded Postgres data. A future `RealMarketDataProvider` implementing
  the same interface swaps in via that one env var - no router or frontend
  changes.
- **AI provider**: controlled by `AI_PROVIDER=mock` in `.env`. All AI text
  (AI Analyse, research chat, comparisons) goes through the `AIProvider`
  interface in `backend/app/providers/ai_provider.py`. `MockAIProvider` is
  fully deterministic - the same underlying metrics always produce the same
  text, template-built with no randomness and no external calls, so it never
  invents a number that isn't already shown elsewhere on the page. The AI
  Research Score itself is separately deterministic (not AI-generated at
  all) - see section 7 above and `backend/app/analytics/scoring.py`.
- The frontend never hardcodes "mock" - it reads `market_data_provider` /
  `ai_provider` from `GET /api/health` and shows the DEMO DATA badge
  accordingly.

## 8. How to connect Gemini later

`GeminiAIProvider` (`backend/app/providers/ai_provider.py`) is already
implemented against the `google-generativeai` SDK, but **it has not been
tested against a real API key** in this environment - verify the model name
and behavior yourself before relying on it.

1. Get a Gemini API key from Google AI Studio.
2. In `backend/.env`, set:
   ```
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your-key-here
   GEMINI_MODEL=gemini-2.0-flash   # or whichever model you choose
   ```
3. Restart the backend (`uvicorn app.main:app --reload --port 8000`) and try
   **AI Analyse** on a stock page. It sends the same grounded numbers Mock
   uses, with instructions not to invent figures or give buy/sell advice; if
   the Gemini call fails for any reason, it silently falls back to the Mock
   draft rather than breaking the page. No frontend changes are required
   either way.

## 9. How to connect a real market data API later

1. Obtain the market data API's base URL and key/documentation.
2. In `backend/.env`, set:
   ```
   MARKET_DATA_PROVIDER=real
   MARKET_DATA_API_URL=...
   MARKET_DATA_API_KEY=...
   ```
3. A `RealMarketDataProvider` implementing the same `MarketDataProvider`
   interface as `MockMarketDataProvider` will be added in Phase 2 - the
   frontend and API routes will not need to change.

## 10. How to replace Gemini with your own AI later

Set `AI_PROVIDER=custom` and provide `CUSTOM_AI_URL` /
`CUSTOM_AI_API_KEY` in `backend/.env`. A `CustomAIProvider` will be added
implementing the same interface - again, no frontend restructuring.

---

## 11. Project structure

```
stocks-ai/
  frontend/              Next.js app (TypeScript, Tailwind, shadcn/ui)
    src/
      app/                Routes: /, /login, /dashboard, /admin, /stocks/[symbol],
                          /research, /research/history, /watchlist, /compare, /screener
      components/         UI primitives (shadcn) + layout (navbar w/ search, footer)
                          + stock-chart.tsx (Lightweight Charts), financial-bar-chart.tsx,
                          ai-indicator.tsx (AI Research Score gauge), ai-score-badge.tsx,
                          stock-picker.tsx (multi-select search for Compare),
                          compare-chart.tsx (normalized multi-line price chart)
      config/brand.ts      Centralized product name/tagline/disclaimer
      context/            Auth context (React)
      lib/api.ts            Typed fetch wrapper against the backend
      lib/format.ts          Rs./Lakh/Crore/percent formatting helpers
      middleware -> proxy.ts  Route protection (Next.js 16 "proxy" convention)
      types/                Shared TypeScript types
  backend/                FastAPI app
    app/
      main.py              App + CORS + router wiring
      config.py            Settings (env-driven, see .env.example)
      database.py           SQLAlchemy engine/session
      security.py           Password hashing + JWT
      deps.py               get_current_user / require_admin / get_market_data_provider
                              / get_ai_provider
      models/                users, companies, price_history, company_financials,
                              financial_ratios, watchlists, watchlist_items,
                              research_sessions, research_messages
      schemas/               Pydantic request/response models (incl. research.py, watchlist.py,
                              compare.py, screener.py, admin.py)
      providers/market_data.py  MarketDataProvider interface + MockMarketDataProvider
      providers/ai_provider.py  AIProvider interface + MockAIProvider (deterministic,
                              hallucination-safe) + GeminiAIProvider (untested)
      services/stock_context.py  Shared "gather everything about a stock" helper used
                              by research.py and compare.py
      services/company_matching.py  Shared "which companies does this text mention"
                              helper used by research.py (chat routing) and admin.py
                              (most-researched analytics)
      analytics/              technicals.py (pure SMA/EMA/RSI/MACD/Bollinger/etc.)
                              + indicators_service.py (builds the API response)
                              + scoring.py (deterministic AI Research Score - NOT AI-generated)
      routers/                health, auth, admin (incl. /analytics), stocks (incl.
                              /ai-score), research, watchlist, compare, screener
      seed/companies.py       The 15 seeded demo companies
      seed/market_data.py     Deterministic OHLCV + financials + ratios generator
    scripts/
      init_db.py            Create tables
      seed_data.py           Seed dev users + demo companies
      seed_market_data.py    Seed price history + financials + ratios
    tests/                  pytest suite (SQLite in-memory, no Postgres needed)
  docs/
  docker-compose.yml        Optional local Postgres
  .env.example               Backend environment template
  README.md
```

---

## 12. Troubleshooting

**`docker compose up -d` fails with a pipe/engine error**
Docker Desktop isn't running. Start it from the Start menu and wait for the
tray icon to finish animating, then retry.

**`psycopg2` fails to connect / "connection refused"**
Postgres isn't running or `DATABASE_URL` in `backend/.env` doesn't match
your setup. Confirm with `docker compose ps` (Docker) or your local
Postgres service status.

**`ImportError: email-validator is not installed`**
Run `pip install -r requirements.txt` again inside the activated venv -
`email-validator` is already listed there.

**Frontend shows a blank dashboard / network errors in the browser console**
Confirm the backend is running on port 8000 and `frontend/.env.local` has
`NEXT_PUBLIC_API_URL=http://localhost:8000`. Also confirm you're logged in -
`/api/stocks` requires authentication.

**Login succeeds but `/dashboard` immediately redirects to `/login`**
The `access_token` cookie is httpOnly and scoped to `localhost`. Make sure
you're accessing the frontend via `http://localhost:3000` (not `127.0.0.1`)
so the cookie's SameSite=Lax policy applies as expected between the two
localhost ports.

**`python scripts/seed_data.py` says users/companies already exist**
That's expected on a second run - it skips anything already seeded and
won't print new passwords for existing accounts.

---

## 13. What's next - going live checklist

All 6 planned MVP phases are built. What's left is entirely optional and
driven by you supplying real credentials:

1. **Real market data** - once you have an API URL/key: set
   `MARKET_DATA_PROVIDER=real`, `MARKET_DATA_API_URL`, `MARKET_DATA_API_KEY`
   in `backend/.env`. A `RealMarketDataProvider` implementing the same
   `MarketDataProvider` interface as `MockMarketDataProvider` needs to be
   added (see section 9) - no router or frontend changes required either way.
2. **Real Gemini AI** - `GeminiAIProvider` is already implemented (see
   section 8) but untested against a live key. Set `AI_PROVIDER=gemini`,
   `GEMINI_API_KEY`, `GEMINI_MODEL` and try **AI Analyse** on a stock page
   first (smallest surface to sanity-check) before relying on chat/compare.
3. **Your own AI model later** - set `AI_PROVIDER=custom`,
   `CUSTOM_AI_URL`, `CUSTOM_AI_API_KEY` once `CustomAIProvider` exists (see
   section 10) - not built yet, same interface as the other two providers.
4. **Stronger secrets for anything beyond your own machine** - regenerate
   `JWT_SECRET` (see the comment in `.env.example`), set fixed
   `SEED_ADMIN_PASSWORD`/`SEED_DEMO_PASSWORD` or just create real accounts
   via `/admin`, and reconsider `ALLOW_REGISTRATION` (default stays `false`).

Deliberately **not** next steps, per the original brief: payments/Razorpay,
subscriptions, public signup, broker integration, live trading, or any
infra beyond a single Postgres instance. Those are out of scope for this
private MVP until there's a reason to revisit them.
