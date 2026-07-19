"""Sport-specific roster rules and salary caps.

Adding a new sport/contest type means adding a SportConfig here — the solver
and CSV exporter read everything (slots, cap, flex eligibility, export header)
from this config and contain no sport-specific logic.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RosterSlot:
    name: str                      # slot label, e.g. "RB2", "FLEX"
    eligible_positions: tuple[str, ...]
    export_name: str               # DK bulk-import column header, e.g. "RB"


@dataclass(frozen=True)
class SportConfig:
    key: str
    display_name: str
    salary_cap: int
    slots: tuple[RosterSlot, ...] = field(default_factory=tuple)

    @property
    def roster_size(self) -> int:
        return len(self.slots)

    @property
    def positions(self) -> tuple[str, ...]:
        seen: list[str] = []
        for slot in self.slots:
            for pos in slot.eligible_positions:
                if pos not in seen:
                    seen.append(pos)
        return tuple(seen)

    def position_bounds(self) -> dict[str, tuple[int, int]]:
        """Min/max lineup count per position, derived from the slot list.

        min = slots where the position is the only eligible one;
        max = all slots where the position is eligible.
        """
        bounds: dict[str, tuple[int, int]] = {}
        for pos in self.positions:
            lo = sum(1 for s in self.slots if s.eligible_positions == (pos,))
            hi = sum(1 for s in self.slots if pos in s.eligible_positions)
            bounds[pos] = (lo, hi)
        return bounds

    @property
    def export_header(self) -> tuple[str, ...]:
        return tuple(s.export_name for s in self.slots)


NFL_CLASSIC = SportConfig(
    key="nfl_classic",
    display_name="NFL Classic",
    salary_cap=50_000,
    slots=(
        RosterSlot("QB", ("QB",), "QB"),
        RosterSlot("RB1", ("RB",), "RB"),
        RosterSlot("RB2", ("RB",), "RB"),
        RosterSlot("WR1", ("WR",), "WR"),
        RosterSlot("WR2", ("WR",), "WR"),
        RosterSlot("WR3", ("WR",), "WR"),
        RosterSlot("TE", ("TE",), "TE"),
        RosterSlot("FLEX", ("RB", "WR", "TE"), "FLEX"),
        RosterSlot("DST", ("DST",), "DST"),
    ),
)

SPORT_CONFIGS: dict[str, SportConfig] = {
    NFL_CLASSIC.key: NFL_CLASSIC,
}


def get_sport_config(key: str) -> SportConfig:
    try:
        return SPORT_CONFIGS[key]
    except KeyError:
        raise ValueError(f"Unknown sport config '{key}'. Available: {list(SPORT_CONFIGS)}")
