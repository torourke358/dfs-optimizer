"""Constraint validation for the optimizer. Runs with pytest or plain python."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_sport_config
from app.csv_io import lineups_to_dk_csv, parse_salaries_csv
from app.models import OptimizeSettings, PlayerAdjustment
from app.optimizer import generate_lineups

CONFIG = get_sport_config("nfl_classic")
SAMPLE = Path(__file__).parent.parent / "sample_data" / "DKSalaries.csv"
PLAYERS = parse_salaries_csv(SAMPLE.read_text(encoding="utf-8-sig"))


def _positions(lineup):
    return Counter(lp.player.position for lp in lineup.players)


def _assert_valid_roster(lineup):
    assert len(lineup.players) == 9
    assert len({lp.player.id for lp in lineup.players}) == 9, "duplicate player in lineup"
    assert lineup.total_salary <= CONFIG.salary_cap
    pos = _positions(lineup)
    assert pos["QB"] == 1 and pos["DST"] == 1
    assert 2 <= pos["RB"] <= 3 and 3 <= pos["WR"] <= 4 and 1 <= pos["TE"] <= 2
    assert pos["RB"] + pos["WR"] + pos["TE"] == 7
    slots = [lp.slot for lp in lineup.players]
    assert slots == [s.name for s in CONFIG.slots], "slot order mismatch"


def test_single_lineup_optimal():
    lineups, _, _ = generate_lineups(PLAYERS, OptimizeSettings(num_lineups=1), CONFIG)
    assert len(lineups) == 1
    _assert_valid_roster(lineups[0])


def test_bulk_unique_and_overlap():
    settings = OptimizeSettings(num_lineups=20, max_overlap=6)
    lineups, _, msg = generate_lineups(PLAYERS, settings, CONFIG)
    assert len(lineups) == 20, msg
    sets = [frozenset(lp.player.id for lp in lu.players) for lu in lineups]
    assert len(set(sets)) == 20, "duplicate lineups"
    for i in range(len(sets)):
        _assert_valid_roster(lineups[i])
        for j in range(i + 1, len(sets)):
            assert len(sets[i] & sets[j]) <= 6, f"lineups {i},{j} overlap too much"


def test_exposure_cap():
    settings = OptimizeSettings(num_lineups=10, global_max_exposure=0.3)
    lineups, exposures, _ = generate_lineups(PLAYERS, settings, CONFIG)
    assert len(lineups) == 10
    for e in exposures:
        assert e.count <= 3, f"{e.name} exceeds 30% exposure ({e.count}/10)"


def test_qb_wr_and_game_stack():
    settings = OptimizeSettings(num_lineups=5, stack_qb_wr=True, game_stack=True)
    lineups, _, _ = generate_lineups(PLAYERS, settings, CONFIG)
    for lu in lineups:
        qb = next(lp.player for lp in lu.players if lp.player.position == "QB")
        wr_teams = {lp.player.team for lp in lu.players if lp.player.position == "WR"}
        assert qb.team in wr_teams, f"no WR stacked with {qb.name}"
        bring_back_teams = {
            lp.player.team for lp in lu.players
            if lp.player.position in ("RB", "WR", "TE")
        }
        assert qb.opponent in bring_back_teams, f"no bring-back vs {qb.name}"


def test_lock_and_exclude():
    lock_id = next(p.id for p in PLAYERS if p.name == "Patrick Mahomes")
    excl_id = next(p.id for p in PLAYERS if p.name == "Ja'Marr Chase")
    adjustments = [
        PlayerAdjustment(id=lock_id, locked=True),
        PlayerAdjustment(id=excl_id, excluded=True),
    ]
    lineups, _, _ = generate_lineups(
        PLAYERS, OptimizeSettings(num_lineups=3), CONFIG, adjustments
    )
    for lu in lineups:
        ids = {lp.player.id for lp in lu.players}
        assert lock_id in ids and excl_id not in ids


def test_per_player_exposure_and_projection_override():
    target = next(p for p in PLAYERS if p.name == "Josh Allen")
    adjustments = [PlayerAdjustment(id=target.id, max_exposure=0.2, projection=40.0)]
    lineups, exposures, _ = generate_lineups(
        PLAYERS, OptimizeSettings(num_lineups=10), CONFIG, adjustments
    )
    entry = next((e for e in exposures if e.player_id == target.id), None)
    assert entry is not None and entry.count <= 2  # 40-pt projection wants in, cap holds


def test_dk_export_format():
    lineups, _, _ = generate_lineups(PLAYERS, OptimizeSettings(num_lineups=2), CONFIG)
    csv_out = lineups_to_dk_csv(lineups, CONFIG)
    lines = csv_out.strip().split("\n")
    assert lines[0] == "QB,RB,RB,WR,WR,WR,TE,FLEX,DST"
    assert len(lines) == 3
    id_set = {p.id for p in PLAYERS}
    for line in lines[1:]:
        cells = line.split(",")
        assert len(cells) == 9 and all(c in id_set for c in cells)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
