"""DraftKings CSV parsing (salaries export) and export (bulk-import format)."""

import csv
import io
import re

from .config import SportConfig
from .models import Lineup, Player

# Column aliases, lowercased, in priority order.
_NAME_COLS = ("name",)
_ID_COLS = ("id",)
_POSITION_COLS = ("position",)
_SALARY_COLS = ("salary",)
_TEAM_COLS = ("teamabbrev", "team")
_GAME_COLS = ("game info", "gameinfo", "game")
_PROJECTION_COLS = ("projection", "proj", "fpts", "projected points", "projectedpoints")
_FALLBACK_PROJECTION_COLS = ("avgpointspergame", "fppg")

_NAME_ID_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<id>\d+)\)\s*$")


def _find_col(header: list[str], aliases: tuple[str, ...]) -> int | None:
    lowered = [h.strip().lower() for h in header]
    for alias in aliases:
        if alias in lowered:
            return lowered.index(alias)
    return None


def _parse_opponent(game_info: str, team: str) -> str:
    """'BUF@MIA 11/03/2024 01:00PM ET' + 'MIA' -> 'BUF'."""
    matchup = game_info.split(" ")[0] if game_info else ""
    if "@" in matchup:
        away, _, home = matchup.partition("@")
        if team == away:
            return home
        if team == home:
            return away
    return ""


def parse_salaries_csv(content: str) -> list[Player]:
    """Parse a DraftKings salaries CSV export.

    Handles the standard DK header (Position, Name + ID, Name, ID, Roster
    Position, Salary, Game Info, TeamAbbrev, AvgPointsPerGame) and tolerates
    extra/missing columns. A 'Name (ID)' combined column is used when separate
    Name/ID columns are absent. Projections come from a projection column if
    present, else AvgPointsPerGame, else 0.
    """
    reader = csv.reader(io.StringIO(content))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise ValueError("CSV is empty")

    header = rows[0]
    i_name = _find_col(header, _NAME_COLS)
    i_id = _find_col(header, _ID_COLS)
    i_name_id = _find_col(header, ("name + id", "name+id"))
    i_pos = _find_col(header, _POSITION_COLS)
    i_salary = _find_col(header, _SALARY_COLS)
    i_team = _find_col(header, _TEAM_COLS)
    i_game = _find_col(header, _GAME_COLS)
    i_proj = _find_col(header, _PROJECTION_COLS)
    i_proj_fallback = _find_col(header, _FALLBACK_PROJECTION_COLS)

    if i_pos is None or i_salary is None:
        raise ValueError(
            "CSV does not look like a DraftKings salaries export "
            "(missing Position and/or Salary columns)"
        )
    if i_name is None and i_name_id is None:
        raise ValueError("CSV is missing a Name (or 'Name + ID') column")

    players: list[Player] = []
    seen_ids: set[str] = set()
    for row in rows[1:]:
        def cell(idx: int | None) -> str:
            if idx is None or idx >= len(row):
                return ""
            return row[idx].strip()

        name, pid = cell(i_name), cell(i_id)
        if not name or not pid:
            m = _NAME_ID_RE.match(cell(i_name_id))
            if m:
                name = name or m.group("name")
                pid = pid or m.group("id")
        if not name:
            continue
        if not pid:
            pid = name  # last resort: name as ID so the row is still usable
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        try:
            salary = int(float(cell(i_salary).replace(",", "").replace("$", "") or 0))
        except ValueError:
            continue

        proj_raw = cell(i_proj) or cell(i_proj_fallback)
        try:
            projection = float(proj_raw) if proj_raw else 0.0
        except ValueError:
            projection = 0.0

        team = cell(i_team)
        game_info = cell(i_game)
        position = cell(i_pos).upper()
        if position == "DEF":  # some sources use DEF for defenses
            position = "DST"

        players.append(
            Player(
                id=pid,
                name=name,
                position=position,
                salary=salary,
                team=team,
                game_info=game_info,
                opponent=_parse_opponent(game_info, team),
                projection=round(projection, 2),
            )
        )

    if not players:
        raise ValueError("No player rows could be parsed from the CSV")
    return players


def lineups_to_dk_csv(lineups: list[Lineup], config: SportConfig) -> str:
    """Render lineups in DraftKings bulk-import format: a header row of slot
    names (QB,RB,RB,WR,WR,WR,TE,FLEX,DST) and one row of player IDs per lineup.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(config.export_header)
    for lineup in lineups:
        by_slot = {lp.slot: lp.player.id for lp in lineup.players}
        writer.writerow([by_slot.get(slot.name, "") for slot in config.slots])
    return buf.getvalue()
