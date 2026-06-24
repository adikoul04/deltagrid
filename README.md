# DeltaGrid

**DeltaGrid** is a browser-based options market making simulator. Trade against live or replayed markets, quote strikes with configurable spreads, simulate fills, and track P&amp;L and portfolio Greeks in a dark trading-terminal UI.

Stack: **React 19 + TypeScript + Vite** (simulation, UI, charts) and a thin **FastAPI** backend (market data + BSM pricing). Pricing and IV solving run in **Python** (`scipy`); the browser owns quotes, fills, positions, and charts.

The project is **feature-complete** and supports local development plus optional split deployment (static frontend + API). See [Deployment](#deployment).

---

## Features

### Simulation modes

| Mode | Description |
|------|-------------|
| **Live** | Polls Yahoo Finance for spot and option chains every 5s while the clock is running. Bid/ask on the chain are repriced synthetically from BSM fair value + half-spread so the book moves with spot between refreshes. |
| **Replay** | Steps through historical time from a chosen date, start time, and timezone (New York, Chicago, or UTC). Spot is interpolated from minute bars; option markets are **synthetic** (BSM-repriced) because historical NBBO is not time-accurate. Replay speed 1×–100×. Start, pause, and resume without losing session state. |

### Market data &amp; pricing (backend)

- Live **spot** via Yahoo Finance (`yfinance`)
- Full **option chain** for ticker + expiry (`YYYY-MM-DD`)
- **Risk-free rate** from FRED (3-month T-bill, `DTB3`) when `FRED_API_KEY` is set; otherwise a 5% default
- **BSM fair value** and **Greeks** (delta, gamma, theta, vega) per contract
- **Implied vol** solved from market mid via Newton-style IV solver
- In-memory **cache** (5s TTL) to limit external API calls
- **Replay spot** interpolated from intraday minute history

### Chain tab

- **Spot price** header metric and **spot time-series chart** (Plotly) with pan/zoom
- Auto-scrolling x-axis: grows 0 → now until 1000s, then slides a 100s window; panning preserved until you return to the live edge
- Full option chain table: symbol, type, strike, bid, ask, mid, IV, fair, delta, gamma, theta, vega

### Quotes tab

- **Portfolio panel** — mark-to-market P&amp;L and net delta, gamma, theta, vega
- **Open positions** table (ticker, type, strike, expiry, quantity)
- **P&amp;L** and **position quantity** time-series charts side by side (500s growth → 50s sliding window)
- **Send quotes** — strike picker, spread scope (call / put / both), spread shape, width, quantity
- **Spread shapes:** balanced, left-skewed, right-skewed, or fully **custom** bid/ask per leg
- **Market status** panel per leg (mkt bid, mkt ask, fair, mid) or “No market data for this strike.”
- **Auto-refresh:** non-custom quotes reprice each tick from updated fair value
- **Active quotes** table with per-leg cancel
- **Trade log** — timestamp, type, strike, side, qty, price

### Fill simulation (client-side)

Two levels of fill logic:

1. **Level 0 — crossed market:** if your ask ≤ market bid or your bid ≥ market ask, you fill immediately at your quote price.
2. **Level 2 — probabilistic:** competitive quotes fill with per-tick probability that decays with edge vs. the NBBO (base rate, decay constant, max edge, price tolerance).

Fills remove the quote, update positions and cash, append to the trade log, and surface in the **status bar** (last 3 alerts, dismissible).

### Portfolio &amp; risk

- **P&amp;L:** mark-to-market — `cash + Σ(qty × fair_value × 100)` per open contract
- **Net Greeks:** `Σ(qty × 100 × greek)` over open positions
- Closed legs contribute realized cash only (no stale marks)
- Theta is the model’s raw annualized BSM value, aggregated in the UI

### UI &amp; UX

- Dark **trading-terminal** layout: sidebar controls, status bar, spot strip, tabbed main panel
- **Status bar:** live/replay mode, sim timestamp, running/paused, loading indicator, API errors, fill toasts
- **Chain** and **Quotes** tabs
- Sidebar settings persisted to `localStorage` (`deltagrid-settings`): ticker, expiry, mode, replay prefs, default spread/qty

---

## Architecture

```
deltagrid/
├── backend/                 # Thin FastAPI data API
│   └── app/
│       ├── main.py          # App entry, CORS
│       ├── routes.py        # Market data endpoints
│       └── schemas.py       # Response models
├── frontend/                # React + TypeScript + Vite
│   └── src/
│       ├── api/             # HTTP client (VITE_API_BASE)
│       ├── domain/          # Fills, positions, quotes, chart viewport
│       ├── store/           # Zustand simulation state
│       ├── hooks/           # Simulation tick loop
│       ├── components/      # Sidebar, charts, tables, status bar
│       └── tabs/            # Chain, Quotes
├── options_mm/              # Python pricing & data layer
│   ├── data/fetcher.py      # yfinance + FRED
│   ├── pricing/             # BSM + IV solver
│   ├── engine/              # Quote, fill, position engines (Python tests)
│   └── services/chain.py    # Chain pricing orchestration
├── render.yaml              # Render blueprint (backend deploy)
├── scripts/dev.sh           # Start backend + frontend
└── tests/                   # pytest suite (backend + domain)
```

### Responsibility split

| Layer | Owns | Does not own |
|-------|------|--------------|
| **Backend** | Spot, chain, RFR, replay spot; BSM/IV via scipy | UI state, quotes, positions, chart viewport |
| **Frontend domain** | Fill simulation, positions, P&amp;L/Greeks, chart viewport, quote refresh | External API keys, scipy pricing |
| **Frontend UI** | Tabs, sidebar, tables, Plotly charts | Market data fetching logic |

### API

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/spot?ticker=` | Live spot price |
| `GET /api/rfr` | Risk-free rate (FRED or default) |
| `GET /api/chain?ticker=&expiry=&spot=&as_of=&synthetic=` | Priced option chain |
| `GET /api/replay/spot?ticker=&timestamp=` | Interpolated replay spot |
| `POST /api/cache/clear` | Clear data cache (live mode) |

Interactive docs: `http://localhost:8000/docs` when running locally.

---

## Setup

**Requirements:** Python 3.11+, Node 20+

```bash
# Python (repo root)
python -m pip install -r requirements.txt
cp .env.example .env   # optional FRED_API_KEY for live Treasury rates

# Frontend
cd frontend && npm install
```

## Run locally

**Option A — one script:**

```bash
./scripts/dev.sh
```

**Option B — two terminals:**

```bash
# Terminal 1 — API on :8000
python -m uvicorn backend.app.main:app --reload --port 8000

# Terminal 2 — UI on :5173 (proxies /api → backend)
cd frontend && npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

## Test

```bash
# Backend + Python domain (23 tests)
python -m pytest

# Frontend domain logic
cd frontend && npm test
```

---

## Usage

1. Enter **ticker** (e.g. `SPY`) and **expiry** (`YYYY-MM-DD`) in the sidebar.
2. Choose **Live** or **Replay**, configure time settings, and start the clock.
3. **Chain** tab — spot chart and full option chain with Greeks.
4. **Quotes** tab — portfolio metrics, P&amp;L/quantity charts, strike quoting, active quotes, and trade history.
5. Send quotes; watch fills and risk update each tick.

**Tips**

- Use a **near-term listed expiry** (e.g. next Friday for SPY) so Yahoo returns chain data.
- In **Replay**, pick a date at least ~10 days in the past (minute bars lag a few trading days).
- Pause live mode when not actively testing to reduce API load.

---

## Configuration

| Variable | Where | Purpose |
|----------|-------|---------|
| `FRED_API_KEY` | `.env` (backend) | Live risk-free rate from FRED; falls back to 5% if unset |
| `ALLOWED_ORIGINS` | `.env` (backend) | Comma-separated CORS origins for your deployed frontend URL(s) |
| `VITE_API_BASE` | frontend build env | API base URL (default `/api` for local Vite proxy) |

---

## Deployment

DeltaGrid is designed as a **split deployment**: static React frontend + Python API. Both can be hosted on common free tiers.

### Recommended layout

| Piece | Service | Notes |
|-------|---------|-------|
| **Frontend** | [Vercel](https://vercel.com/), [Netlify](https://www.netlify.com/), or [Cloudflare Pages](https://pages.cloudflare.com/) | Static CDN hosting |
| **Backend** | [Render](https://render.com/) | `render.yaml` blueprint included |

### Frontend

1. Connect the repo to your static host.
2. **Root directory:** `frontend`
3. **Framework preset:** Vite (not “Services” / monorepo mode)
4. **Build command:** `npm ci && npm run build`
5. **Output directory:** `dist`
6. **Environment variable:** `VITE_API_BASE=https://YOUR-API-HOST/api` (path must end with `/api`)

### Backend (Render)

Use the included `render.yaml` blueprint or create a **Web Service**:

- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Env:** `ALLOWED_ORIGINS` = your frontend origin(s), optional `FRED_API_KEY`

After the API is live, set `VITE_API_BASE` on the frontend and redeploy.

### Hosting caveats

- **Render free** services spin down after ~15 min of inactivity; the first request after idle can take 30–60s.
- **Yahoo Finance** (`yfinance`) is unofficial and rate-limited, especially from cloud/datacenter IPs. Local development is more reliable than a public API host for heavy live polling.
- **Live mode** polls spot + chain every 5s and clears the backend cache each tick while running.
- **No auth** — single-user, in-memory cache; suitable for a demo, not multi-tenant production.
- **Replay** depends on Yahoo minute history availability (typically lags a few trading days).

---

## Tradeoffs &amp; assumptions

- Pricing stays in **Python** (scipy BSM + IV solver); the browser runs simulation state only.
- Replay option markets are **synthetic** — educational simulation, not historical tape accuracy.
- Live running mode reprices displayed bid/ask from fair value so the book reacts to spot between chain refreshes.
- Quotes sent during an in-flight market-data tick are preserved (race-safe merge in the simulation store).

## License

See [LICENSE](LICENSE).
