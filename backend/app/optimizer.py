"""CP-SAT lineup optimizer.

Model: one binary variable x[p] per player, with per-position count bounds
derived from the sport config (e.g. NFL Classic: QB==1, RB in [2,3],
WR in [3,4], TE in [1,2], DST==1, total==9). For single-flex roster shapes
these bounds are exactly equivalent to a full slot-assignment model but have
no slot symmetry, so a single CP-SAT worker solves them in milliseconds —
which matters on fractional-CPU hosts. Slots (including FLEX) are assigned
deterministically after the solve for the DraftKings bulk-import export.

Bulk generation re-solves the same model, appending constraints between
solves: a no-duplicate cut (and optional max-overlap cut) per found lineup,
and x[p] == 0 once a player hits its exposure cap.
"""

import math

from ortools.sat.python import cp_model

from .config import SportConfig
from .models import (
    ExposureEntry,
    Lineup,
    LineupPlayer,
    OptimizeSettings,
    Player,
    PlayerAdjustment,
)

_PROJ_SCALE = 100  # projections are floats; CP-SAT wants integer objectives
_SOLVE_TIME_LIMIT_S = 10.0
_SKILL_POSITIONS = ("RB", "WR", "TE")  # eligible "bring-back" pieces for game stacks


class OptimizerError(ValueError):
    pass


def _apply_adjustments(
    players: list[Player], adjustments: list[PlayerAdjustment]
) -> tuple[list[Player], set[str], dict[str, float]]:
    """Returns (pool with excluded removed & projections overridden,
    locked player ids, per-player max exposure overrides)."""
    adj_by_id = {a.id: a for a in adjustments}
    pool: list[Player] = []
    locked: set[str] = set()
    exposure_overrides: dict[str, float] = {}
    for p in players:
        adj = adj_by_id.get(p.id)
        if adj:
            if adj.excluded:
                continue
            if adj.projection is not None:
                p = p.model_copy(update={"projection": adj.projection})
            if adj.locked:
                locked.add(p.id)
            if adj.max_exposure is not None:
                exposure_overrides[p.id] = adj.max_exposure
        pool.append(p)
    return pool, locked, exposure_overrides


def _exposure_cap(fraction: float, num_lineups: int) -> int:
    if fraction >= 1.0:
        return num_lineups
    return math.floor(fraction * num_lineups + 1e-9)


def _assign_slots(chosen: list[Player], config: SportConfig) -> list[LineupPlayer]:
    """Deterministically map a chosen roster onto the config's slot order.

    Pure slots (single eligible position) are filled first, highest projection
    first; whatever remains goes to flex slots that accept its position.
    """
    remaining = sorted(chosen, key=lambda p: -p.projection)
    result: dict[str, Player] = {}
    for slot in config.slots:
        if len(slot.eligible_positions) == 1:
            pos = slot.eligible_positions[0]
            pick = next((p for p in remaining if p.position == pos), None)
            if pick is not None:
                result[slot.name] = pick
                remaining.remove(pick)
    for slot in config.slots:
        if slot.name in result:
            continue
        pick = next((p for p in remaining if p.position in slot.eligible_positions), None)
        if pick is None:
            raise OptimizerError(
                f"Internal error: solver roster does not fit slot {slot.name}"
            )
        result[slot.name] = pick
        remaining.remove(pick)
    return [LineupPlayer(slot=s.name, player=result[s.name]) for s in config.slots]


def generate_lineups(
    players: list[Player],
    settings: OptimizeSettings,
    config: SportConfig,
    adjustments: list[PlayerAdjustment] | None = None,
) -> tuple[list[Lineup], list[ExposureEntry], str]:
    pool, locked, exposure_overrides = _apply_adjustments(players, adjustments or [])
    if not pool:
        raise OptimizerError("Player pool is empty after exclusions")

    salary_max = settings.salary_max if settings.salary_max is not None else config.salary_cap
    salary_max = min(salary_max, config.salary_cap)
    if settings.salary_min > salary_max:
        raise OptimizerError(
            f"Minimum salary {settings.salary_min} exceeds maximum {salary_max}"
        )

    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x_{p.id}") for p in pool]

    valid_positions = set(config.positions)
    for i, p in enumerate(pool):
        if p.position not in valid_positions:
            model.add(x[i] == 0)  # position not used by this contest type

    by_position: dict[str, list[cp_model.IntVar]] = {pos: [] for pos in config.positions}
    for i, p in enumerate(pool):
        if p.position in by_position:
            by_position[p.position].append(x[i])

    for pos, (lo, hi) in config.position_bounds().items():
        vars_ = by_position[pos]
        if len(vars_) < lo:
            raise OptimizerError(f"Not enough {pos}s in the pool (need at least {lo})")
        model.add(sum(vars_) >= lo)
        model.add(sum(vars_) <= hi)
    model.add(sum(x) == config.roster_size)

    salary_expr = sum(p.salary * x[i] for i, p in enumerate(pool))
    model.add(salary_expr <= salary_max)
    if settings.salary_min > 0:
        model.add(salary_expr >= settings.salary_min)

    for i, p in enumerate(pool):
        if p.id in locked:
            model.add(x[i] == 1)

    if settings.stack_qb_wr:
        for i, p in enumerate(pool):
            if p.position != "QB":
                continue
            teammates = [
                x[j] for j, q in enumerate(pool) if q.position == "WR" and q.team == p.team
            ]
            model.add(sum(teammates) >= 1).only_enforce_if(x[i])

    if settings.game_stack:
        for i, p in enumerate(pool):
            if p.position != "QB" or not p.opponent:
                continue
            bring_backs = [
                x[j]
                for j, q in enumerate(pool)
                if q.position in _SKILL_POSITIONS and q.team == p.opponent
            ]
            model.add(sum(bring_backs) >= 1).only_enforce_if(x[i])

    model.maximize(
        sum(round(p.projection * _PROJ_SCALE) * x[i] for i, p in enumerate(pool))
    )

    n = settings.num_lineups
    global_cap = _exposure_cap(settings.global_max_exposure, n)
    caps: dict[int, int] = {}
    for i, p in enumerate(pool):
        cap = _exposure_cap(exposure_overrides.get(p.id, settings.global_max_exposure), n)
        if p.id in locked:
            cap = n  # a lock overrides exposure limits
        elif p.id not in exposure_overrides:
            cap = global_cap
        caps[i] = cap
        if cap == 0:
            model.add(x[i] == 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = _SOLVE_TIME_LIMIT_S
    # Keep the thread count fixed and low: free hosting tiers grant a fraction
    # of one CPU, and the count-based model is tiny enough that one worker
    # proves optimality in milliseconds anyway.
    solver.parameters.num_workers = 1

    lineups: list[Lineup] = []
    counts: dict[int, int] = {i: 0 for i in range(len(pool))}
    capped: set[int] = set()
    message = ""

    for k in range(n):
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if k == 0:
                raise OptimizerError(
                    "No feasible lineup exists with the current pool and settings "
                    "(check locks, exclusions, stacking rules, and salary bounds)"
                )
            message = (
                f"Only {k} of {n} requested lineups are feasible with the current "
                "uniqueness/overlap/exposure constraints."
            )
            break

        chosen = [i for i in range(len(pool)) if solver.value(x[i]) == 1]
        chosen_players = [pool[i] for i in chosen]
        lineups.append(
            Lineup(
                players=_assign_slots(chosen_players, config),
                total_salary=sum(p.salary for p in chosen_players),
                total_projection=round(sum(p.projection for p in chosen_players), 2),
            )
        )

        # Forbid this exact lineup (and near-copies if max_overlap is set).
        overlap_limit = (
            min(settings.max_overlap, config.roster_size - 1)
            if settings.max_overlap is not None
            else config.roster_size - 1
        )
        model.add(sum(x[i] for i in chosen) <= overlap_limit)

        # Retire players that just hit their exposure cap.
        for i in chosen:
            counts[i] += 1
            if counts[i] >= caps[i] and i not in capped:
                capped.add(i)
                if counts[i] < n:  # only matters if more lineups remain
                    model.add(x[i] == 0)

    exposures = [
        ExposureEntry(
            player_id=pool[i].id,
            name=pool[i].name,
            position=pool[i].position,
            team=pool[i].team,
            count=c,
            exposure=round(c / len(lineups), 4) if lineups else 0.0,
        )
        for i, c in counts.items()
        if c > 0
    ]
    exposures.sort(key=lambda e: (-e.count, e.name))
    return lineups, exposures, message
