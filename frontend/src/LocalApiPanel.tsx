import {useEffect, useState} from 'react';
import type {LocalApiBinding} from './LocalApiEditor';
import {useLocalJobHistory} from './useLocalJobHistory';
type Job = {job_id: string; status: string; result: {status: string; reason?: string} | null};
const reasons: Record<string,string> = {
  contract_satisfied:'The saved response contract passed.', tls_verification_failed:'TLS certificate verification failed.',
  http_status_mismatch:'HTTP status did not match the saved expectation.', json_contract_failed:'The JSON response contract failed.',
  policy_blocked:'Execution was blocked by the API policy.', cancelled:'Execution was cancelled.',
  destination_blocked:'Destination authorization failed. Check the saved host and public-IP scope.',
  configuration_changed:'Saved settings changed before completion.', execution_error:'The bounded API operation could not complete.',
};
type Review = {execution_authorized: false; contract_fingerprint: string};
type Props = {projectId: string; target: string; binding: LocalApiBinding; unsaved: boolean; licensed: boolean;
  request: <T>(path: string, method?: string, body?: unknown) => Promise<T>};
const active = (job: Job) => ['queued', 'running', 'cancel_requested'].includes(job.status);

export function LocalApiPanel({projectId, target, binding, unsaved, licensed, request}: Props) {
  const publicHttps = binding.profile === 'public_https';
  const [review, setReview] = useState<Review | null>(null), [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const base = `/api/projects/${projectId}/local-api`;
  const {jobs, setJobs, historyReady, historyLoading, historyError, refreshHistory, polling} = useLocalJobHistory<Job>(base, request);
  useEffect(() => {if (unsaved) {setReview(null); setConfirmed(false);}}, [unsaved]);
  async function inspect() {
    setBusy(true); setError(''); setReview(null); setConfirmed(false);
    try {setReview(await request<Review>(base + '/review', 'POST', {}));}
    catch {setError('API review failed. Check saved settings and your local session.');}
    finally {setBusy(false);}
  }
  async function enqueue() {
    if (!review || !confirmed || unsaved || !historyReady || polling) return;
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
  return <section className="plan-review" aria-label="Explicit API execution">
    <h3>Explicit API execution</h3>
    <p>Saved GET <code style={{overflowWrap:'anywhere'}}>{publicHttps ? target.replace(/\/$/,'') + binding.path : binding.path}</code> · HTTP {binding.expected_status} · {binding.response_mode === 'status_only' ? 'Status-only contract' : <code>{binding.json_field} = {String(binding.expected_boolean)}</code>}</p>
    <p className="hint">{publicHttps ? 'Public HTTPS on port 443 with validated public IPs and verified TLS. Redirects are not followed.' : 'Owned loopback API only.'} Review does not contact the endpoint. A separate local worker executes one confirmed request; no authentication or request values are used.</p>
    {unsaved && <p role="status">Save configuration changes before reviewing API execution.</p>}
    <button disabled={busy || unsaved} onClick={() => void inspect()}>Review saved API binding</button>
    {review && <div aria-label="API review confirmation">
      <p>Review complete. No request was sent to the API.</p>
      <label className="check"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/><span>{publicHttps ? 'I authorize one GET request to my configured public HTTPS API.' : 'I authorize one GET request to my owned local API.'}</span></label>
      <button disabled={busy || unsaved || !confirmed || polling || !historyReady} onClick={() => void enqueue()}>Queue one API request</button>
    </div>}
    <details><summary>Run an API worker locally</summary><p>Use your installed environment and the same workspace as this dashboard. Replace example paths.</p><pre style={{whiteSpace: 'pre-wrap', overflowWrap: 'anywhere'}}><code>{licensed
      ? 'python -m adaptive_qa local api-once --workspace C:/QA/workspace --trusted-keys C:/QA/publisher-public-keys.json'
      : 'python -m adaptive_qa dashboard free-api-once --database C:/QA/workspace/projects.sqlite'}</code></pre><p>The three-queue worker cycle does not process API jobs. Unknown completion is never retried automatically.</p></details>
    {error && <p className="message error" role="alert">{error}</p>}
    {historyError && <p className="message error" role="alert">API history is unavailable. Refresh history before confirming another job.</p>}
    <button disabled={busy || historyLoading} onClick={refreshHistory}>Refresh API history</button>
    {historyLoading && <p role="status">Loading API history…</p>}
    {historyReady && !jobs.length && <p className="hint">No API jobs yet.</p>}
    {jobs.map(job => <div className="discovery-job" key={job.job_id}><span><code>{job.job_id.slice(0, 8)}</code><strong>{job.status.replaceAll('_', ' ')}</strong>{job.result && <small>API result: {job.result.status}</small>}{job.result?.reason && <small>{reasons[job.result.reason] ?? 'The API operation returned an unavailable outcome reason.'}</small>}</span>
      {active(job) && <button disabled={busy || job.status === 'cancel_requested'} onClick={() => {
        setBusy(true); setError('');
        void request<Job>(base + '/jobs/' + job.job_id + '/cancel', 'POST', {}).then(updated => setJobs(previous => previous.map(item => item.job_id === updated.job_id ? updated : item)))
          .catch(() => setError('Cancellation was not confirmed. Check history before retrying.')).finally(() => setBusy(false));
      }}>Cancel API job</button>}</div>)}
  </section>;
}
