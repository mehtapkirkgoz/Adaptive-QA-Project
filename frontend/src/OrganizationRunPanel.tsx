import {useEffect, useState} from 'react';
import {CaseSelector} from './CaseSelector';

type Run = {run_id: string; status: string; results: {case_id: string; status: string; evidence_id?: string; evidence_expired?: boolean}[]};
type Props = {base: string; discoveryJobId?: string; candidates: string[]; candidateNames?: Record<string, string>; canExecute: boolean;
  request: <T>(path: string, method?: string, body?: unknown) => Promise<T>};
const active = (run: Run) => ['queued', 'running', 'cancel_requested'].includes(run.status);

export function OrganizationRunPanel({base, discoveryJobId, candidates, candidateNames, canExecute, request}: Props) {
  const [runs, setRuns] = useState<Run[]>([]), [selection, setSelection] = useState<string[]>([]);
  const [busy, setBusy] = useState(false), [loading, setLoading] = useState(true), [error, setError] = useState('');
  const polling = runs.some(active);
  useEffect(() => {let alive = true, timer: ReturnType<typeof setTimeout> | undefined;
    async function refresh() {
      try {
        const data = await request<{runs: Run[]}>(`${base}/runs`);
        if (!alive) return;
        setRuns(data.runs); setLoading(false);
        if (data.runs.some(active)) timer = setTimeout(refresh, 1500);
      } catch {if (alive) {setLoading(false); setError('Could not refresh shared runs. Reopen the project and check your membership.');}}
    }
    void refresh();
    return () => {alive = false; if (timer) clearTimeout(timer);};
  }, [base, polling, request]);
  const candidateKey = candidates.join(',');
  useEffect(() => {setSelection([]);}, [discoveryJobId, candidateKey]);
  async function action(task: () => Promise<void>) {
    setBusy(true); setError('');
    try {await task();} catch {setError('Shared run request failed. Check current discovery, membership and available quota.');}
    finally {setBusy(false);}
  }
  return <section className="plan-review" aria-label="Organization test runs"><h3>Shared test runs</h3>
    <p className="hint">Select up to ten read-only cases from current controlled discovery. A separate worker executes queued work.</p>
    {!discoveryJobId && <p className="hint">Review current discovery before selecting tests.</p>}
    {discoveryJobId && <CaseSelector key={discoveryJobId + candidateKey} candidates={candidates} names={candidateNames}
      selection={selection} disabled={!canExecute || busy} labelPrefix="Shared select" onChange={setSelection}/>}
    <button disabled={!canExecute || busy || loading || polling || !discoveryJobId || !selection.length}
      onClick={() => void action(async () => {
        const run = await request<Run>(`${base}/runs`, 'POST', {discovery_job_id: discoveryJobId, case_ids: selection});
        setRuns(previous => [run, ...previous].slice(0, 20)); setSelection([]);
      })}>Start shared tests</button>
    {error && <p role="alert" className="message error">{error}</p>}
    {!runs.length && <p className="hint">No shared test runs yet.</p>}
    {runs.map(run => <article key={run.run_id} data-shared-run-id={run.run_id}>
      <p>Shared run {run.status.replaceAll('_', ' ')} · {run.run_id.slice(0, 8)}</p>
      {active(run) && <button disabled={!canExecute || busy || run.status === 'cancel_requested'} onClick={() => void action(async () => {
        const updated = await request<Run>(`${base}/runs/${run.run_id}/cancel`, 'POST', {});
        setRuns(previous => previous.map(value => value.run_id === run.run_id ? updated : value));
      })}>Cancel shared run</button>}
      <ul>{run.results.map(result => <li key={result.case_id}>{result.case_id}: {result.status}
        {result.evidence_id && <a href={`${base}/runs/${run.run_id}/evidence/${result.evidence_id}`}
          target="_blank" rel="noopener noreferrer"> View shared screenshot</a>}
        {result.evidence_expired && <span> Screenshot expired</span>}
      </li>)}</ul>
    </article>)}
  </section>;
}
