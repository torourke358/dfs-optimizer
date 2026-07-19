"""Pydantic models shared by the API and the solver."""

from pydantic import BaseModel, Field


class Player(BaseModel):
    id: str                  # DraftKings player ID (used for bulk-import export)
    name: str
    position: str            # QB / RB / WR / TE / DST
    salary: int
    team: str
    game_info: str = ""      # e.g. "BUF@MIA 11/03/2024 01:00PM ET"
    opponent: str = ""       # parsed from game_info
    projection: float = 0.0


class PlayerAdjustment(BaseModel):
    """Per-player overrides sent by the UI on top of the uploaded pool."""
    id: str
    projection: float | None = None
    locked: bool = False
    excluded: bool = False
    max_exposure: float | None = Field(default=None, ge=0.0, le=1.0)


class OptimizeSettings(BaseModel):
    sport: str = "nfl_classic"
    num_lineups: int = Field(default=1, ge=1, le=150)
    salary_min: int = Field(default=0, ge=0)
    salary_max: int | None = None            # defaults to the sport's cap
    global_max_exposure: float = Field(default=1.0, ge=0.0, le=1.0)
    max_overlap: int | None = Field(default=None, ge=0)  # max shared players between any two lineups
    stack_qb_wr: bool = False                # QB + >=1 WR from same team
    game_stack: bool = False                 # QB game must include >=1 opposing-team skill player


class OptimizeRequest(BaseModel):
    players: list[Player]
    adjustments: list[PlayerAdjustment] = []
    settings: OptimizeSettings = OptimizeSettings()


class LineupPlayer(BaseModel):
    slot: str                # QB / RB1 / ... / FLEX / DST
    player: Player


class Lineup(BaseModel):
    players: list[LineupPlayer]
    total_salary: int
    total_projection: float


class ExposureEntry(BaseModel):
    player_id: str
    name: str
    position: str
    team: str
    count: int
    exposure: float          # fraction of generated lineups


class OptimizeResponse(BaseModel):
    lineups: list[Lineup]
    exposures: list[ExposureEntry]
    requested: int
    generated: int
    message: str = ""
