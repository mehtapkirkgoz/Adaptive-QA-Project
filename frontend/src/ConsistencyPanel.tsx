import {useEffect, useState} from 'react';

type Signals = {reason: string; minimum_observations: number; excluded_runs: number;
  signals: {case_id: string; context_id: string; observations: number; passed: number; failed: number;
    assessment: string; potential_flakiness: boolean}[]};
type Props = {projectId: string; revision: string;
  request: <T>(path: string, method?: string, body?: unknown) => Promise<T>};
export function ConsistencyPanel({projectId, revision, request}: Props) {
  const [open, setOpen] = useState(false), [report, setReport] = useState<Signals>();
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!open) return;
    let alive = true;
    setReport(undefined); setError(false);
    void request<Signals>(`/api/projects/${projectId}/flaky-signals`)
      .then(data => {if (alive) setReport(data);})
      .catch(() => {if (alive) setError(true);});
    return () => {alive = false;};
  }, [projectId, revision, open]);
  return <section aria-label="Test consistency"><button onClick={() => setOpen(!open)}>{open ? 'Hide consistency' : 'Review consistency'}</button>
    {open && error && <p role="alert">Could not load consistency observations.</p>}
    {open && report && <><p className="hint">{report.reason}</p>
      <p className="hint">Latest 20 owned runs. Minimum observations per context: {report.minimum_observations}. Excluded runs: {report.excluded_runs}.</p>
      {!report.signals.length && <p>No comparable observations yet.</p>}
      {report.signals.map(row => <p key={`${row.case_id}:${row.context_id}`}><strong>{row.case_id}</strong> — {row.assessment.replaceAll('_', ' ')}. {row.observations} observations; {row.passed} passed, {row.failed} failed. Context {row.context_id.slice(0, 8)}.</p>)}
    </>}
  </section>;
}
