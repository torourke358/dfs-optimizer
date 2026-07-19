import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from .config import SPORT_CONFIGS, get_sport_config
from .csv_io import lineups_to_dk_csv, parse_salaries_csv
from .models import Lineup, OptimizeRequest, OptimizeResponse, Player
from .optimizer import OptimizerError, generate_lineups

SAMPLE_CSV = Path(__file__).parent.parent / "sample_data" / "DKSalaries.csv"

app = FastAPI(title="DFS Lineup Optimizer", version="1.0.0")

# Demo app: allow the local dev frontend plus an optional deployed origin.
_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
]
if extra := os.environ.get("FRONTEND_ORIGIN"):
    _origins.append(extra.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "sports": list(SPORT_CONFIGS)}


@app.get("/api/sample", response_model=list[Player])
def sample_slate() -> list[Player]:
    return parse_salaries_csv(SAMPLE_CSV.read_text(encoding="utf-8-sig"))


@app.post("/api/upload", response_model=list[Player])
async def upload_csv(file: UploadFile) -> list[Player]:
    raw = await file.read()
    try:
        return parse_salaries_csv(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    try:
        config = get_sport_config(req.settings.sport)
        lineups, exposures, message = generate_lineups(
            req.players, req.settings, config, req.adjustments
        )
    except (OptimizerError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return OptimizeResponse(
        lineups=lineups,
        exposures=exposures,
        requested=req.settings.num_lineups,
        generated=len(lineups),
        message=message,
    )


class ExportRequest(BaseModel):
    sport: str = "nfl_classic"
    lineups: list[Lineup]


@app.post("/api/export", response_class=PlainTextResponse)
def export_dk_csv(req: ExportRequest) -> PlainTextResponse:
    config = get_sport_config(req.sport)
    return PlainTextResponse(
        lineups_to_dk_csv(req.lineups, config),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dk_lineups.csv"},
    )
