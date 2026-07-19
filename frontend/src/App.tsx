import { useCallback, useEffect, useMemo, useState } from 'react';
import { exportDkCsv, optimize, uploadCsv, warmBackend } from './api';
import samplePlayers from './data/sample_players.json';
import { PlayerTable } from './components/PlayerTable';
import { Results } from './components/Results';
import { SettingsPanel } from './components/SettingsPanel';
import { UploadZone } from './components/UploadZone';
import type { OptimizeResponse, OptimizeSettings, Player, PlayerAdjustment, RowState } from './types';
import { SALARY_CAP } from './types';

const DEFAULT_SETTINGS: OptimizeSettings = {
  sport: 'nfl_classic',
  num_lineups: 20,
  salary_min: 0,
  salary_max: SALARY_CAP,
  global_max_exposure: 0.6,
  max_overlap: null,
  stack_qb_wr: true,
  game_stack: false,
};

export default function App() {
  const [players, setPlayers] = useState<Player[]>([]);
  const [slateName, setSlateName] = useState('');
  const [rowState, setRowState] = useState<Record<string, RowState>>({});
  const [settings, setSettings] = useState<OptimizeSettings>(DEFAULT_SETTINGS);
  const [result, setResult] = useState<OptimizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [backendReady, setBackendReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    warmBackend().then((ok) => {
      if (!cancelled) setBackendReady(ok);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadPlayers = useCallback((list: Player[], name: string) => {
    setPlayers(list);
    setSlateName(name);
    setRowState({});
    setResult(null);
    setError('');
  }, []);

  const handleSample = useCallback(() => {
    // Bundled with the app so the demo works instantly, even while the
    // free-tier backend is still waking from a cold start.
    loadPlayers(samplePlayers as Player[], 'Sample NFL main slate · 12 teams');
  }, [loadPlayers]);

  const handleFile = useCallback(
    async (file: File) => {
      setLoading(true);
      setError('');
      try {
        loadPlayers(await uploadCsv(file), file.name);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Could not parse that CSV');
      } finally {
        setLoading(false);
      }
    },
    [loadPlayers],
  );

  const handleRowChange = useCallback((id: string, patch: Partial<RowState>) => {
    setRowState((prev) => {
      const base: RowState = prev[id] ?? { locked: false, excluded: false, projection: null };
      return { ...prev, [id]: { ...base, ...patch } };
    });
  }, []);

  const adjustments = useMemo<PlayerAdjustment[]>(
    () =>
      Object.entries(rowState)
        .filter(([, rs]) => rs.locked || rs.excluded || rs.projection !== null)
        .map(([id, rs]) => ({
          id,
          locked: rs.locked,
          excluded: rs.excluded,
          projection: rs.projection,
        })),
    [rowState],
  );

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    setError('');
    try {
      setResult(await optimize(players, adjustments, settings));
    } catch (e) {
      setError(
        backendReady
          ? e instanceof Error
            ? e.message
            : 'Optimization failed'
          : 'The solver server is still waking up (free hosting) — give it a few seconds and try again.',
      );
    } finally {
      setGenerating(false);
    }
  }, [players, adjustments, settings, backendReady]);

  const handleExport = useCallback(async () => {
    if (!result) return;
    setExporting(true);
    try {
      const csv = await exportDkCsv(result.lineups, settings.sport);
      const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'dk_lineups.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  }, [result, settings.sport]);

  return (
    <div className="shell">
      <header className="masthead">
        <h1 className="masthead__brand">
          CAPROOM<span className="masthead__tick">_</span>
        </h1>
        <p className="masthead__tag">DraftKings NFL lineup optimizer · CP-SAT under the hood</p>
        {slateName && <span className="masthead__slate mono">{slateName}</span>}
        <span
          className={`status-pill${backendReady ? ' status-pill--ready' : ''}`}
          title={
            backendReady
              ? 'Solver server is awake'
              : 'Free hosting sleeps when idle — waking the solver server now'
          }
        >
          <span className="status-pill__dot" />
          {backendReady ? 'solver ready' : 'waking solver…'}
        </span>
      </header>

      <UploadZone onFile={handleFile} onLoadSample={handleSample} loading={loading} />

      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}

      {players.length > 0 && (
        <main className="workbench">
          <PlayerTable players={players} rowState={rowState} onRowChange={handleRowChange} />
          <SettingsPanel
            settings={settings}
            onChange={(patch) => setSettings((s) => ({ ...s, ...patch }))}
            onGenerate={handleGenerate}
            canGenerate={players.length > 0}
            loading={generating}
          />
        </main>
      )}

      {players.length === 0 && !loading && (
        <div className="intro">
          <p>
            Upload a DraftKings NFL salaries export — or load the sample slate — to build the player
            pool. Lock studs, cross off fades, edit projections inline, then generate up to 150
            cap-legal lineups and export them straight back to DraftKings.
          </p>
        </div>
      )}

      {result && (
        <Results
          lineups={result.lineups}
          exposures={result.exposures}
          message={result.message}
          onExport={handleExport}
          exporting={exporting}
        />
      )}
    </div>
  );
}
