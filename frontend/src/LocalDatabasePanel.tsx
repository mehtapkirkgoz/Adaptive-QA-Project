import {useEffect, useState} from 'react';
import type {LocalDatabaseBinding} from './LocalDatabaseEditor';
import {useLocalJobHistory} from './useLocalJobHistory';
type Job = {job_id: string; status: string; result: {status: string} | null};
type Review = {execution_authorized: false; contract_fingerprint: string};
type Props = {projectId: string; binding: LocalDatabaseBinding; unsaved: boolean; licensed: boolean; databaseReference?: string;
  request: <T>(path: string, method?: string, body?: unknown) => Promise<T>};
const active = (job: Job) => ['queued', 'running', 'cancel_requested'].includes(job.status);

export function LocalDatabasePanel({projectId, binding, unsaved, licensed, request, databaseReference}: Props) {
  const [review, setReview] = useState<Review | null>(null), [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const base = `/api/projects/${projectId}/local-database`;
  const {jobs, setJobs, historyReady, historyLoading, historyError, refreshHistory, polling} = useLocalJobHistory<Job>(base, request);
  useEffect(() => {if (unsaved) {setReview(null); setConfirmed(false);}}, [unsaved]);
  async function inspect() {
    setBusy(true); setError(''); setReview(null); setConfirmed(false);
    try {setReview(await request<Review>(base + '/review', 'POST', {}));}
    catch {setError('database review failed. Check saved settings and your local session.');}
    finally {setBusy(false);}
  }
  async function enqueue() {
    if (!review || !confirmed || unsaved || !databaseReference || !historyReady || polling) return;
    const digest = review.contract_fingerprint;
    setBusy(true); setError(''); setReview(null); setConfirmed(false);
    try {
      const job = await request<Job>(base + '/jobs', 'POST', {confirmed_contract_fingerprint: digest});
      setJobs(previous => [job, ...previous].slice(0, 20));
    } catch {
      setError('Queue confirmation was not received. Check history before confirming another job; this request may already be queued.');
      try {setJobs((await request<{jobs: Job[]}>(base + '/jobs')).jobs);} catch { /* Preserve uncertainty. */ }
    } finally {setBusy(false);}
  }
  return <section className="plan-review" aria-label="Explicit database execution">
    <h3>Explicit database execution</h3>
    <p>Saved table <code>{binding.table}</code> · Expected count: {binding.expected_count}</p>
    <p className="hint">Owned SQLite fixtures only. Review does not open the database. A separate worker performs one read-only count; no rows or resolved file paths are shown.</p>
    {!databaseReference && <p role="status">Select and save the database path reference before reviewing.</p>}
    {unsaved && <p role="status">Save configuration changes before reviewing database execution.</p>}
    <button disabled={busy || unsaved || !databaseReference} onClick={() => void inspect()}>Review saved database count</button>
    {review && <div aria-label="database review confirmation">
      <p>Review complete. No database was opened.</p>
      <label className="check"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/><span>I authorize one read-only count on my owned SQLite fixture.</span></label>
      <button disabled={busy || unsaved || !databaseReference || !confirmed || polling || !historyReady} onClick={() => void enqueue()}>Queue one database count</button>
    </div>}
    <details><summary>Run a database worker locally</summary>
      <p>Prepare only owned test fixtures under <code style={{overflowWrap:'anywhere'}}>database-fixtures/{projectId}</code> inside this workspace.</p>
      {databaseReference && <p>Set <code style={{overflowWrap:'anywhere'}}>{databaseReference}</code> in the worker terminal to the absolute fixture file path inside that directory. Do not paste its value into the dashboard or support reports.</p>}<p>Use your installed environment and the same workspace as this dashboard. Replace example paths.</p><pre style={{whiteSpace: 'pre-wrap', overflowWrap: 'anywhere'}}><code>{licensed
      ? 'python -m adaptive_qa local database-once --workspace C:/QA/workspace --trusted-keys C:/QA/publisher-public-keys.json'
      : 'python -m adaptive_qa dashboard free-database-once --database C:/QA/workspace/projects.sqlite'}</code></pre><p>The three-queue worker cycle does not process database jobs. Unknown completion is never retried automatically.</p></details>
    {error && <p className="message error" role="alert">{error}</p>}
    {historyError && <p className="message error" role="alert">Database history is unavailable. Refresh history before confirming another job.</p>}
    <button disabled={busy || historyLoading} onClick={refreshHistory}>Refresh database history</button>
    {historyLoading && <p role="status">Loading database history…</p>}
    {historyReady && !jobs.length && <p className="hint">No database jobs yet.</p>}
    {jobs.map(job => <div className="discovery-job" key={job.job_id}><span><code>{job.job_id.slice(0, 8)}</code><strong>{job.status.replaceAll('_', ' ')}</strong>{job.result && <small>database result: {job.result.status}</small>}</span>
      {active(job) && <button disabled={busy || job.status === 'cancel_requested'} onClick={() => {
        setBusy(true); setError('');
        void request<Job>(base + '/jobs/' + job.job_id + '/cancel', 'POST', {}).then(updated => setJobs(previous => previous.map(item => item.job_id === updated.job_id ? updated : item)))
          .catch(() => setError('Cancellation was not confirmed. Check history before retrying.')).finally(() => setBusy(false));
      }}>Cancel database job</button>}</div>)}
  </section>;
}
