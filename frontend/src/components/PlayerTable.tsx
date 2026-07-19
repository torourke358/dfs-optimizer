import { useMemo, useState } from 'react';
import type { Player, RowState } from '../types';
import { POSITIONS } from '../types';

type SortKey = 'name' | 'position' | 'team' | 'salary' | 'projection' | 'value';

interface Props {
  players: Player[];
  rowState: Record<string, RowState>;
  onRowChange: (id: string, patch: Partial<RowState>) => void;
}

const fmtSalary = (n: number) => `$${n.toLocaleString()}`;

function effProjection(p: Player, rs: RowState | undefined): number {
  return rs?.projection ?? p.projection;
}

export function PlayerTable({ players, rowState, onRowChange }: Props) {
  const [posFilter, setPosFilter] = useState<string>('ALL');
  const [teamFilter, setTeamFilter] = useState<string>('ALL');
  const [search, setSearch] = useState('');
  const [maxSalary, setMaxSalary] = useState<number | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('salary');
  const [sortDesc, setSortDesc] = useState(true);

  const teams = useMemo(() => [...new Set(players.map((p) => p.team))].sort(), [players]);

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = players.filter(
      (p) =>
        (posFilter === 'ALL' || p.position === posFilter) &&
        (teamFilter === 'ALL' || p.team === teamFilter) &&
        (maxSalary === null || p.salary <= maxSalary) &&
        (!q || p.name.toLowerCase().includes(q)),
    );
    const dir = sortDesc ? -1 : 1;
    return filtered.sort((a, b) => {
      const va =
        sortKey === 'value'
          ? effProjection(a, rowState[a.id]) / (a.salary || 1)
          : sortKey === 'projection'
            ? effProjection(a, rowState[a.id])
            : a[sortKey];
      const vb =
        sortKey === 'value'
          ? effProjection(b, rowState[b.id]) / (b.salary || 1)
          : sortKey === 'projection'
            ? effProjection(b, rowState[b.id])
            : b[sortKey];
      if (typeof va === 'string' && typeof vb === 'string') return dir * va.localeCompare(vb);
      return dir * (Number(va) - Number(vb));
    });
  }, [players, posFilter, teamFilter, search, maxSalary, sortKey, sortDesc, rowState]);

  const sortBy = (key: SortKey) => {
    if (key === sortKey) setSortDesc(!sortDesc);
    else {
      setSortKey(key);
      setSortDesc(key !== 'name' && key !== 'position' && key !== 'team');
    }
  };

  const arrow = (key: SortKey) => (sortKey === key ? (sortDesc ? ' ↓' : ' ↑') : '');

  return (
    <section className="panel pool" aria-label="Player pool">
      <div className="pool__controls">
        <div className="pos-tabs" role="tablist" aria-label="Filter by position">
          {['ALL', ...POSITIONS].map((pos) => (
            <button
              key={pos}
              role="tab"
              aria-selected={posFilter === pos}
              className={`pos-tab${posFilter === pos ? ' pos-tab--on' : ''}`}
              onClick={() => setPosFilter(pos)}
            >
              {pos}
            </button>
          ))}
        </div>
        <input
          className="field field--search"
          placeholder="Search players"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search players"
        />
        <select
          className="field"
          value={teamFilter}
          onChange={(e) => setTeamFilter(e.target.value)}
          aria-label="Filter by team"
        >
          <option value="ALL">All teams</option>
          {teams.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <select
          className="field"
          value={maxSalary ?? ''}
          onChange={(e) => setMaxSalary(e.target.value ? Number(e.target.value) : null)}
          aria-label="Filter by max salary"
        >
          <option value="">Any salary</option>
          {[9000, 8000, 7000, 6000, 5000, 4000].map((s) => (
            <option key={s} value={s}>
              ≤ {fmtSalary(s)}
            </option>
          ))}
        </select>
      </div>

      <div className="pool__scroll">
        <table className="pool__table">
          <thead>
            <tr>
              <th className="th-btn" onClick={() => sortBy('name')}>Player{arrow('name')}</th>
              <th className="th-btn" onClick={() => sortBy('position')}>Pos{arrow('position')}</th>
              <th className="th-btn" onClick={() => sortBy('team')}>Team{arrow('team')}</th>
              <th>Opp</th>
              <th className="th-btn num" onClick={() => sortBy('salary')}>Salary{arrow('salary')}</th>
              <th className="th-btn num" onClick={() => sortBy('projection')}>Proj{arrow('projection')}</th>
              <th className="th-btn num" onClick={() => sortBy('value')}>Val{arrow('value')}</th>
              <th className="center">Lock</th>
              <th className="center">Excl</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => {
              const rs = rowState[p.id];
              const proj = effProjection(p, rs);
              const cls = rs?.excluded ? 'row--excluded' : rs?.locked ? 'row--locked' : '';
              return (
                <tr key={p.id} className={cls}>
                  <td className="cell-name">{p.name}</td>
                  <td>
                    <span className={`pos-chip pos-chip--${p.position.toLowerCase()}`}>{p.position}</span>
                  </td>
                  <td>{p.team}</td>
                  <td className="cell-dim">{p.opponent || '—'}</td>
                  <td className="num mono">{fmtSalary(p.salary)}</td>
                  <td className="num">
                    <input
                      className="proj-input mono"
                      type="number"
                      step="0.1"
                      min="0"
                      value={proj}
                      aria-label={`Projection for ${p.name}`}
                      onChange={(e) =>
                        onRowChange(p.id, {
                          projection: e.target.value === '' ? 0 : Number(e.target.value),
                        })
                      }
                    />
                  </td>
                  <td className="num mono cell-dim">{((proj / p.salary) * 1000).toFixed(2)}</td>
                  <td className="center">
                    <button
                      className={`toggle toggle--lock${rs?.locked ? ' toggle--on' : ''}`}
                      title={rs?.locked ? 'Unlock' : 'Lock into every lineup'}
                      aria-pressed={rs?.locked ?? false}
                      onClick={() => onRowChange(p.id, { locked: !rs?.locked, excluded: false })}
                    >
                      {rs?.locked ? '🔒' : '🔓'}
                    </button>
                  </td>
                  <td className="center">
                    <button
                      className={`toggle toggle--excl${rs?.excluded ? ' toggle--on' : ''}`}
                      title={rs?.excluded ? 'Re-include' : 'Exclude from all lineups'}
                      aria-pressed={rs?.excluded ?? false}
                      onClick={() => onRowChange(p.id, { excluded: !rs?.excluded, locked: false })}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows.length === 0 && <div className="pool__empty">No players match these filters.</div>}
      </div>
      <div className="pool__count">
        {rows.length} of {players.length} players shown
      </div>
    </section>
  );
}
