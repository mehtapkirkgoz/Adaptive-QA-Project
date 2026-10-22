import {useEffect, useState} from 'react';

type Outcome = {case_id: string; status: string; duration_seconds: number; message: string};
type Run = {run_id: string; status: string; case_ids: string[]; results: Outcome[]};
type Props = {projectId: string; discoveryJobId?: string; candidates: string[];
  request: <T>(path: string, method?: string, body?: unknown) => Promise<T>};
const active = (run: Run) => ['queued', 'running', 'cancel_requested'].includes(run.status);

export function RunPanel({projectId, discoveryJobId, candidates, request}: Props) {
  const [runs, setRuns] = useState<Run[]>([]), [selection, setSelection] = useState<string[]>([]);
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const polling = runs.some(active), base = `/api/projects/${projectId}/runs`;
  const candidateKey = candidates.join(',');
  useEffect(() => {setSelection([]);}, [discoveryJobId, candidateKey]);
  useEffect(() => {
    let alive = true, timer: ReturnType<typeof setTimeout> | undefined;
    async function refresh() {
      try {
        const data = await request<{runs: Run[]}>(base);
        if (!alive) return;
        setRuns(data.runs); setLoading(false);
        if (data.runs.some(active)) timer = setTimeout(refresh, 1500);
      } catch {if (alive) {setLoading(false); setError('Could not refresh runs. Check your session and reopen the project.');}}
    }
    void refresh();
    return () => {alive = false; if (timer) clearTimeout(timer);};
  }, [projectId, polling]);
  async function action(task: () => Promise<void>) {
    setBusy(true); setError('');
    try {await task();} catch {setError('Run request failed. Review current discovery, check your selection and session, then try again.');}
    finally {setBusy(false);}
  }
  return <section className="plan-review" aria-label="Test runs"><h3>Run selected UI tests</h3>
    <p className="hint">Only selected read-only tests bound to this local root are eligible. Choose up to ten. Starting creates a queued run for the separate test worker.</p>
    {!discoveryJobId && <p className="hint">Review a completed current discovery plan to choose tests.</p>}
    {!!discoveryJobId && <div className="run-selection">{candidates.map(id => <label className="check" key={id}><input type="checkbox" aria-label={`Select ${id}`}
      disabled={busy || (!selection.includes(id) && selection.length >= 10)} checked={selection.includes(id)}
      onChange={event => setSelection(event.target.checked ? [...selection, id] : selection.filter(item => item !== id))}/>{id}</label>)}</div>}
    <button className="primary" disabled={loading || busy || polling || !discoveryJobId || !selection.length}
      onClick={() => void action(async () => {
        const run = await request<Run>(base, 'POST', {discovery_job_id: discoveryJobId, case_ids: selection});
        setRuns(previous => [run, ...previous].slice(0, 20)); setSelection([]);
      })}>Start selected tests</button>
    {error && <p role="alert" className="message error">{error}</p>}
    {!runs.length && <p className="hint">No test runs yet.</p>}
    {runs.map(run => <article className="run-card" key={run.run_id}><div className="discovery-job"><span><code>{run.run_id.slice(0, 8)}</code><strong>Run {run.status.replaceAll('_', ' ')}</strong></span>
      {active(run) && <button disabled={busy || run.status === 'cancel_requested'} onClick={() => void action(async () => {
        const updated = await request<Run>(`${base}/${run.run_id}/cancel`, 'POST', {});
        setRuns(previous => previous.map(item => item.run_id === run.run_id ? updated : item));
      })}>Cancel test run</button>}</div>
      <p className="hint">{run.results.length} of {run.case_ids.length} test results recorded. Unattempted cases have no result.</p>
      {run.results.map(result => <p className="run-outcome" key={result.case_id}><strong>{result.case_id}</strong> <span>{result.status}</span> <small>{result.duration_seconds.toFixed(2)}s</small></p>)}
      {run.status === 'completed' && <p className="hint">The run finished. Check each test outcome; completion does not mean every test passed.</p>}
    </article>)}
  </section>;
}
