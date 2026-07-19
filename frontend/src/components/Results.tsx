import type { ExposureEntry, Lineup } from '../types';
import { SALARY_CAP } from '../types';

const fmtSalary = (n: number) => `$${n.toLocaleString()}`;

function CapBar({ lineup }: { lineup: Lineup }) {
  return (
    <div
      className="capbar"
      title={`${fmtSalary(lineup.total_salary)} of ${fmtSalary(SALARY_CAP)} cap used`}
    >
      {lineup.players.map((lp) => (
        <div
          key={lp.player.id}
          className={`capbar__seg capbar__seg--${lp.player.position.toLowerCase()}`}
          style={{ width: `${(lp.player.salary / SALARY_CAP) * 100}%` }}
          title={`${lp.player.name} ${fmtSalary(lp.player.salary)}`}
        />
      ))}
    </div>
  );
}

function LineupCard({ lineup, index }: { lineup: Lineup; index: number }) {
  const capLeft = SALARY_CAP - lineup.total_salary;
  return (
    <article className="lineup">
      <header className="lineup__head">
        <span className="lineup__num">#{index + 1}</span>
        <span className="lineup__proj mono">{lineup.total_projection.toFixed(1)} pts</span>
        <span className="lineup__salary mono">
          {fmtSalary(lineup.total_salary)}
          <span className="lineup__left"> · {fmtSalary(capLeft)} left</span>
        </span>
      </header>
      <CapBar lineup={lineup} />
      <table className="lineup__table">
        <tbody>
          {lineup.players.map((lp) => (
            <tr key={lp.player.id}>
              <td className="lineup__slot">{lp.slot.replace(/\d+$/, '')}</td>
              <td className="lineup__name">{lp.player.name}</td>
              <td className="cell-dim">{lp.player.team}</td>
              <td className="num mono">{fmtSalary(lp.player.salary)}</td>
              <td className="num mono">{lp.player.projection.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </article>
  );
}

interface Props {
  lineups: Lineup[];
  exposures: ExposureEntry[];
  message: string;
  onExport: () => void;
  exporting: boolean;
}

export function Results({ lineups, exposures, message, onExport, exporting }: Props) {
  if (lineups.length === 0) return null;
  const avgProj = lineups.reduce((s, l) => s + l.total_projection, 0) / lineups.length;
  return (
    <section className="results" aria-label="Generated lineups">
      <header className="results__head">
        <h2 className="results__title">
          {lineups.length} lineup{lineups.length > 1 ? 's' : ''}
          <span className="results__avg mono"> · avg {avgProj.toFixed(1)} pts</span>
        </h2>
        <button className="btn btn--primary" onClick={onExport} disabled={exporting}>
          {exporting ? 'Exporting…' : 'Export DK CSV'}
        </button>
      </header>
      {message && <p className="results__note">{message}</p>}
      <div className="results__grid">
        {lineups.map((lu, i) => (
          <LineupCard key={i} lineup={lu} index={i} />
        ))}
      </div>

      {lineups.length > 1 && (
        <div className="exposure">
          <h3 className="exposure__title">Player exposure</h3>
          <div className="exposure__grid">
            {exposures.map((e) => (
              <div className="exposure__row" key={e.player_id}>
                <span className={`pos-chip pos-chip--${e.position.toLowerCase()}`}>{e.position}</span>
                <span className="exposure__name">{e.name}</span>
                <div className="exposure__meter">
                  <div className="exposure__fill" style={{ width: `${e.exposure * 100}%` }} />
                </div>
                <span className="exposure__pct mono">
                  {e.count}/{lineups.length}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
