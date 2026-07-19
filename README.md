# CAPROOM — DraftKings NFL DFS Lineup Optimizer

A deployable web app that builds optimal DraftKings NFL Classic lineups with
Google OR-Tools CP-SAT integer programming. Upload a DraftKings salaries CSV
(or load the bundled sample slate), tune projections and rules, generate up to
150 unique lineups, and export them in DraftKings bulk-import format.

**Stack:** FastAPI + OR-Tools CP-SAT (backend) · React + Vite + TypeScript (frontend)

## How the optimizer works

Each (player, roster slot) pair is a binary decision variable. The solver
maximizes total projected points subject to:

- Exactly one player per slot: QB, RB×2, WR×3, TE, FLEX (RB/WR/TE), DST
- Salary total within the $50,000 cap (and an optional user-set floor)
- Each player used at most once per lineup
- **Bulk uniqueness** — after each solve, a cut forbids that exact lineup
  (optionally tightened to a max-overlap constraint so no two lineups share
  more than K players)
- **Exposure caps** — a player is retired from the model once it hits its max
  share of the batch (global slider, per-player overrides, locks and excludes)
- **Stacking** — optional QB + same-team WR, and optional game stack
  (a bring-back from the QB's opponent)

Roster rules and the salary cap live in `backend/app/config.py`; adding NBA or
MLB later means adding a `SportConfig`, not touching the solver.

## Run locally

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows — use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

Or with Docker, one command:

```bash
docker compose up --build     # frontend on :5173, backend on :8000
```

### CLI demo (no UI needed)

```bash
cd backend
.venv/Scripts/python cli.py -n 10 --stack --max-exposure 0.5 --export lineups.csv
```

### Tests

```bash
cd backend
.venv/Scripts/python tests/test_optimizer.py   # or: pytest tests/
```

Validates roster legality, salary cap, uniqueness, overlap, exposure caps,
stacking, locks/excludes, and the DK export format.

## CSV formats

- **Input:** a standard DraftKings salaries export (`Position, Name + ID, Name,
  ID, Roster Position, Salary, Game Info, TeamAbbrev, AvgPointsPerGame`).
  Extra columns are ignored; a `Projection`/`Proj`/`FPTS` column is used when
  present, otherwise `AvgPointsPerGame` seeds projections and every value is
  editable in the UI. A sample slate ships in `backend/sample_data/`.
- **Output:** DraftKings bulk-import format — header row
  `QB,RB,RB,WR,WR,WR,TE,FLEX,DST`, one row of player IDs per lineup — ready to
  upload at draftkings.com.

## Deploy

### Backend → Railway

1. `railway login`, then from the repo root: `railway init`
2. `railway up --service backend` (or point the service's root directory at
   `/backend` in the dashboard — the Dockerfile is picked up automatically,
   and the container binds to Railway's `$PORT`)
3. Add an environment variable `FRONTEND_ORIGIN=https://<your-app>.vercel.app`
4. Generate a public domain for the service; note the URL.

### Frontend → Vercel

1. `vercel login`, then from `/frontend`: `vercel`
2. Set the project's **Root Directory** to `frontend` (framework preset: Vite)
3. Add an environment variable `VITE_API_URL=https://<railway-backend-url>`
4. `vercel --prod`

The frontend reads `VITE_API_URL` at build time; the backend also accepts any
`*.vercel.app` origin via CORS, so preview deploys work out of the box.
