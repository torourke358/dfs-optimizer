export interface Player {
  id: string;
  name: string;
  position: string;
  salary: number;
  team: string;
  game_info: string;
  opponent: string;
  projection: number;
}

export interface PlayerAdjustment {
  id: string;
  projection?: number | null;
  locked?: boolean;
  excluded?: boolean;
  max_exposure?: number | null;
}

export interface OptimizeSettings {
  sport: string;
  num_lineups: number;
  salary_min: number;
  salary_max: number | null;
  global_max_exposure: number;
  max_overlap: number | null;
  stack_qb_wr: boolean;
  game_stack: boolean;
}

export interface LineupPlayer {
  slot: string;
  player: Player;
}

export interface Lineup {
  players: LineupPlayer[];
  total_salary: number;
  total_projection: number;
}

export interface ExposureEntry {
  player_id: string;
  name: string;
  position: string;
  team: string;
  count: number;
  exposure: number;
}

export interface OptimizeResponse {
  lineups: Lineup[];
  exposures: ExposureEntry[];
  requested: number;
  generated: number;
  message: string;
}

export interface RowState {
  locked: boolean;
  excluded: boolean;
  projection: number | null; // override; null = use uploaded value
}

export const SALARY_CAP = 50000;
export const POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DST'] as const;
