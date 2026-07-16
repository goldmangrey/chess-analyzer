# Chess AI Teacher

Chess AI Teacher is a local, single-user application intended to help review chess games and improve play. The repository is currently at the **foundation stage**: it contains a minimal FastAPI health endpoint and a minimal Next.js status page. Game import, analysis, persistence, and the full user interface are not implemented yet.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer
- npm

## Backend

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

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

Run frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

This README describes only the current foundation. Later-stage features are intentionally not presented as available.
