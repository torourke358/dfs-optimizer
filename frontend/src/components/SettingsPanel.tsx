import type { OptimizeSettings } from '../types';
import { SALARY_CAP } from '../types';

interface Props {
  settings: OptimizeSettings;
  onChange: (patch: Partial<OptimizeSettings>) => void;
  onGenerate: () => void;
  canGenerate: boolean;
  loading: boolean;
}

export function SettingsPanel({ settings, onChange, onGenerate, canGenerate, loading }: Props) {
  return (
    <aside className="panel settings" aria-label="Optimizer settings">
      <h2 className="panel__title">Build settings</h2>

      <label className="setting">
        <span className="setting__label">Lineups</span>
        <input
          className="field field--num mono"
          type="number"
          min={1}
          max={150}
          value={settings.num_lineups}
          onChange={(e) =>
            onChange({ num_lineups: Math.max(1, Math.min(150, Number(e.target.value) || 1)) })
          }
        />
      </label>

      <div className="setting">
        <span className="setting__label">Salary range</span>
        <div className="setting__pair">
          <input
            className="field field--num mono"
            type="number"
            step={500}
            min={0}
            max={SALARY_CAP}
            value={settings.salary_min}
            aria-label="Minimum salary"
            onChange={(e) => onChange({ salary_min: Number(e.target.value) || 0 })}
          />
          <span className="setting__dash">–</span>
          <input
            className="field field--num mono"
            type="number"
            step={500}
            min={0}
            max={SALARY_CAP}
            value={settings.salary_max ?? SALARY_CAP}
            aria-label="Maximum salary"
            onChange={(e) => onChange({ salary_max: Number(e.target.value) || SALARY_CAP })}
          />
        </div>
      </div>

      <label className="setting">
        <span className="setting__label">
          Max exposure
          <span className="setting__value mono">{Math.round(settings.global_max_exposure * 100)}%</span>
        </span>
        <input
          type="range"
          min={10}
          max={100}
          step={5}
          value={Math.round(settings.global_max_exposure * 100)}
          onChange={(e) => onChange({ global_max_exposure: Number(e.target.value) / 100 })}
        />
        <span className="setting__hint">Max share of lineups any one player can appear in</span>
      </label>

      <label className="setting">
        <span className="setting__label">
          Max overlap
          <span className="setting__value mono">
            {settings.max_overlap === null ? 'off' : `${settings.max_overlap} players`}
          </span>
        </span>
        <input
          type="range"
          min={3}
          max={9}
          step={1}
          value={settings.max_overlap ?? 9}
          onChange={(e) => {
            const v = Number(e.target.value);
            onChange({ max_overlap: v >= 9 ? null : v });
          }}
        />
        <span className="setting__hint">Most players any two lineups may share (9 = no limit)</span>
      </label>

      <div className="setting setting--toggles">
        <label className="check">
          <input
            type="checkbox"
            checked={settings.stack_qb_wr}
            onChange={(e) => onChange({ stack_qb_wr: e.target.checked })}
          />
          <span>QB + WR stack</span>
          <span className="setting__hint">Every lineup pairs its QB with a same-team WR</span>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={settings.game_stack}
            onChange={(e) => onChange({ game_stack: e.target.checked })}
          />
          <span>Game stack</span>
          <span className="setting__hint">Adds a bring-back from the QB's opponent</span>
        </label>
      </div>

      <button className="btn btn--primary btn--generate" onClick={onGenerate} disabled={!canGenerate || loading}>
        {loading ? 'Solving…' : `Generate ${settings.num_lineups} lineup${settings.num_lineups > 1 ? 's' : ''}`}
      </button>
    </aside>
  );
}
