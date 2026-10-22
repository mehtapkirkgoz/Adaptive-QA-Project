import {useEffect, useState} from 'react';

type Report = {run_status: string; catalog_total: number; requested_total: number;
  recorded_total: number; unrecorded_total: number; status_counts: Record<string, number>;
  results: {case_id: string; status: string; duration_seconds: number; message: string; evidence_id?: string}[]};
type Props = {base: string; revision: string;
  request: <T>(path: string, method?: string, body?: unknown) => Promise<T>};

export function ReportPanel({base, revision, request}: Props) {
  const [open, setOpen] = useState(false), [filter, setFilter] = useState('');
  const [report, setReport] = useState<Report>(), [error, setError] = useState(false);
  useEffect(() => {
    if (!open) return;
    let alive = true;
    setReport(undefined); setError(false);
    void request<Report>(`${base}/report${filter ? `/status/${filter}` : ''}`)
      .then(data => {if (alive) setReport(data);})
      .catch(() => {if (alive) setError(true);});
    return () => {alive = false;};
  }, [base, revision, open, filter]);
  return <section aria-label="Run report">
    <button onClick={() => setOpen(!open)}>{open ? 'Hide report' : 'Review report'}</button>
    {open && <>
      <label>Result status <select value={filter} onChange={event => setFilter(event.target.value)}>
        <option value="">All outcomes</option>
        {['passed', 'failed', 'skipped', 'blocked', 'cancelled', 'error'].map(value => <option key={value} value={value}>{value}</option>)}
      </select></label>
      <a href={`${base}/report/download`} download>Download JSON report</a>
      {error && <p role="alert">Could not load report. Check your session and reopen it.</p>}
      {!report && !error && <p role="status">Loading report…</p>}
      {report && <>
        <p>Catalog: {report.catalog_total}. Requested: {report.requested_total}. Recorded: {report.recorded_total}. Unrecorded: {report.unrecorded_total}.</p>
        <p className="hint">Catalog size does not mean every case applies to this project. Totals include outcomes hidden by the filter.</p>
        <p>{Object.entries(report.status_counts).map(([status, count]) => `${status}: ${count}`).join(' · ')}</p>
        {!report.results.length && <p>No recorded outcomes match this filter.</p>}
        {report.results.map(result => <p key={result.case_id}><strong>{result.case_id}</strong> {result.status} ({result.duration_seconds.toFixed(2)}s). {result.message}
          {result.evidence_id && <> <a href={`${base}/evidence/${result.evidence_id}`} target="_blank" rel="noopener noreferrer">Report screenshot</a></>}</p>)}
      </>}
    </>}
  </section>;
}
