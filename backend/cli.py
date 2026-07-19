"""Terminal demo: optimize lineups straight from a DraftKings salaries CSV.

Usage:
    python cli.py [path/to/DKSalaries.csv] [-n NUM_LINEUPS] [--stack] [--game-stack]
                  [--max-exposure 0.5] [--max-overlap 6] [--export out.csv]
"""

import argparse
from pathlib import Path

from app.config import get_sport_config
from app.csv_io import lineups_to_dk_csv, parse_salaries_csv
from app.models import OptimizeSettings
from app.optimizer import generate_lineups

DEFAULT_CSV = Path(__file__).parent / "sample_data" / "DKSalaries.csv"


def main() -> None:
    ap = argparse.ArgumentParser(description="DraftKings NFL lineup optimizer (CLI demo)")
    ap.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))
    ap.add_argument("-n", "--num-lineups", type=int, default=1)
    ap.add_argument("--stack", action="store_true", help="require QB + WR from same team")
    ap.add_argument("--game-stack", action="store_true", help="require opposing-team bring-back with QB")
    ap.add_argument("--max-exposure", type=float, default=1.0)
    ap.add_argument("--max-overlap", type=int, default=None)
    ap.add_argument("--export", help="write DK bulk-import CSV to this path")
    args = ap.parse_args()

    config = get_sport_config("nfl_classic")
    players = parse_salaries_csv(Path(args.csv).read_text(encoding="utf-8-sig"))
    print(f"Parsed {len(players)} players from {args.csv}\n")

    settings = OptimizeSettings(
        num_lineups=args.num_lineups,
        stack_qb_wr=args.stack,
        game_stack=args.game_stack,
        global_max_exposure=args.max_exposure,
        max_overlap=args.max_overlap,
    )
    lineups, exposures, message = generate_lineups(players, settings, config)

    for idx, lineup in enumerate(lineups, 1):
        print(f"=== Lineup {idx}  |  salary ${lineup.total_salary:,} / ${config.salary_cap:,}"
              f"  |  {lineup.total_projection:.2f} pts ===")
        for lp in lineup.players:
            p = lp.player
            print(f"  {lp.slot:<5} {p.name:<28} {p.team:<4} ${p.salary:<6,} {p.projection:>6.2f}")
        print()

    if len(lineups) > 1:
        print("Top exposures:")
        for e in exposures[:10]:
            print(f"  {e.name:<28} {e.position:<4} {e.count}/{len(lineups)}  ({e.exposure:.0%})")
        print()

    if message:
        print(f"NOTE: {message}\n")

    if args.export:
        Path(args.export).write_text(lineups_to_dk_csv(lineups, config), encoding="utf-8")
        print(f"Wrote DK bulk-import CSV to {args.export}")


if __name__ == "__main__":
    main()
