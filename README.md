# Chess AI Teacher

Chess AI Teacher is a local, single-user application intended to help review chess games and improve play. The repository is currently at the **foundation stage**: it contains a minimal FastAPI health endpoint and a minimal Next.js status page. Game import, analysis, persistence, and the full user interface are not implemented yet.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer
- npm

## Backend

Create an optional local configuration file from the provided example:

```bash
cp backend/.env.example backend/.env
```

The backend runs without `.env` by using safe defaults. The configuration covers
the future database URL, Chess.com username and User-Agent, import limit, future
Stockfish path and analysis limits, and the frontend origin. These integrations
are not implemented yet.

The SQLite schema and SQLAlchemy ORM models for games and per-move analysis are
implemented. When explicitly initialized with the default configuration, the
local database will be stored at `backend/data/chess.db`. Game import and
Stockfish analysis are not implemented yet.

The repository layer encapsulates game and move-analysis SQL queries, including
filters, pagination, personal analytics sorting, and aggregate calculations.
Repositories flush changes when needed but never commit automatically; callers
own transaction boundaries. Import, analysis services, and REST APIs are not
implemented yet.

Chess.com import and PGN parsing are available through the manual CLI. Set a
valid, identifying `CHESSCOM_USER_AGENT`, then run:

```bash
cd backend
source .venv/bin/activate
python -m scripts.import_games --username Yeskendir --limit 10
```

The first real CLI run initializes `backend/data/chess.db`. Newly imported games
are stored with `pending` analysis status, ready for a separate local analysis run.

## Local Stockfish analysis

Install the native engine on macOS and find its path:

```bash
brew install stockfish
which stockfish
```

Set the discovered path in `backend/.env`, for example:

```env
STOCKFISH_PATH=/opt/homebrew/bin/stockfish
```

Analyze pending games sequentially:

```bash
cd backend
source .venv/bin/activate
python -m scripts.analyze_games --pending
```

Every ply is analyzed locally for both players and stored with evaluations, CP
loss, and classification. Later personal statistics will use only rows where
`is_user_move=true`. No AI API is used. REST and frontend integration are not
implemented yet.

Backend statistics now provides real summaries, period comparisons, weakest
openings, trends, and recent-game metrics. Every personal move metric explicitly
excludes opponent moves through `is_user_move=true`. Accuracy, Elo estimates,
AI explanations, and the Dashboard UI are not implemented.

## REST API

The FastAPI application exposes:

- `GET /health`
- `POST /api/import/chess-com`
- `GET /api/games`
- `GET /api/games/{game_id}`
- `GET /api/games/{game_id}/moves`
- `POST /api/games/{game_id}/analyze`
- `GET /api/stats/summary`
- `GET /api/stats/trends`
- `GET /api/stats/openings`
- `GET /api/stats/performance`
- `GET /api/stats/dashboard`

Swagger UI is available at <http://127.0.0.1:8000/docs>. Import and analysis can
be requested through REST; Stockfish work runs through FastAPI BackgroundTasks.
These in-process tasks are interrupted if the backend stops, which is acceptable
for the local MVP. The Dashboard consumes the statistics and import endpoints;
the Games and detailed analysis interfaces are still pending.

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

The health endpoint is available at <http://127.0.0.1:8000/health> and returns `{"status":"ok"}`.

Run backend tests:

```bash
cd backend
source .venv/bin/activate
pytest
```

## Frontend

The Soft Bento frontend now includes a real Dashboard backed by
`GET /api/stats/dashboard`. Chess.com import is available from the Dashboard;
new games can be queued for local Stockfish analysis through FastAPI's
background task flow. The interface also includes the reusable `AppShell`, top
navigation, responsive layout primitives, and shared feedback states. Review
the design-system workbench at <http://localhost:3000/components-preview>.

Configure the direct FastAPI base URL in `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

The backend must be running for live Dashboard data and import. The `/games`
route remains a placeholder; the Games list and detailed Game Analysis
interfaces are not implemented yet.

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

For local development, run the backend and frontend in separate terminals:

```bash
cd backend
source .venv/bin/activate
python run.py
```

```bash
cd frontend
npm run dev
```

Run frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

Later-stage frontend features are intentionally not presented as available.
