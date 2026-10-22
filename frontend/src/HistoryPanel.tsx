import {useEffect, useState} from 'react';

type Comparison = {comparable: boolean; reason: string;
  results: {case_id: string; baseline_status: string | null; current_status: string | null; change: string}[]};
type Props = {base: string; runId: string; others: {run_id: string; status: string}[];
  request: <T>(path: string, method?: string, body?: unknown) => Promise<T>};

export function HistoryPanel({base, runId, others, request}: Props) {
  const [baseline, setBaseline] = useState(''), [report, setReport] = useState<Comparison>();
  const [error, setError] = useState(false);
  const candidates = others.filter(run => run.run_id !== runId && ['completed', 'cancelled', 'error'].includes(run.status));
  const valid = candidates.some(run => run.run_id === baseline);
  useEffect(() => {
    let alive = true;
    setReport(undefined); setError(false);
    if (baseline && valid) void request<Comparison>(`${base}/${runId}/compare/${baseline}`)
      .then(data => {if (alive) setReport(data);})
      .catch(() => {if (alive) setError(true);});
    return () => {alive = false;};
  }, [base, runId, baseline, valid]);
  return <section aria-label="Run comparison"><label>Compare with run <select aria-label="Compare with run" value={valid ? baseline : ''}
    onChange={event => setBaseline(event.target.value)}>
    <option value="">Choose a finalized run</option>
    {candidates.map(run => <option value={run.run_id} key={run.run_id}>{run.run_id.slice(0, 8)} — {run.status}</option>)}
  </select></label>
    {error && <p role="alert">Could not compare runs. Check ownership, completion and session.</p>}
    {report && <><p className="hint">{report.reason}</p>
      {report.results.map(row => <p data-testid="comparison-row" key={row.case_id}><strong>{row.case_id}</strong> {row.change}: {row.baseline_status ?? 'unrecorded'} → {row.current_status ?? 'unrecorded'}</p>)}
    </>}
  </section>;
}
