import {useEffect, useState} from 'react';
import type {LocalFormSettings} from './LocalFormBindingEditor';

type Job = {job_id: string; status: string; result: {status: string; attempted_submissions: number | null} | null};
type Review = {execution_authorized: false; contract_fingerprint: string};
type Props = {projectId: string; target: string; dataChanges: boolean; references: string[]; binding?: LocalFormSettings; hasUnsavedChanges?: boolean;
  request: <T>(path: string, method?: string, body?: unknown) => Promise<T>};
const active = (job: Job) => ['queued', 'running', 'cancel_requested'].includes(job.status);

export function InteractivePanel({projectId, target, dataChanges, references, request, binding, hasUnsavedChanges = false}: Props) {
  const fixture = /^http:\/\/127\.0\.0\.1:8000\/interactive\/(login-transition|login-rejected|search-transition|search-empty)$/.exec(target)?.[1];
  const login = binding ? binding.operation === 'login' : fixture?.startsWith('login'), negative = fixture === 'login-rejected' || fixture === 'search-empty';
  const [outcome, setOutcome] = useState<'accepted' | 'rejected'>(negative ? 'rejected' : 'accepted');
  const expectedNegative = binding ? outcome === 'rejected' : negative;
  const logical = login ? (expectedNegative ? 'login.rejected' : 'login.accepted') : (expectedNegative ? 'search.empty' : 'search.results');
  const required = login ? ['login_username', 'login_password'] : ['search_query'];
  const supported = !!fixture || !!binding;
  const ready = supported && !hasUnsavedChanges && dataChanges && required.every(slot => references.includes(slot));
  const [marker, setMarker] = useState(negative ? 'negative' : 'result'), [seconds, setSeconds] = useState(15);
  const [review, setReview] = useState<Review | null>(null), [confirmed, setConfirmed] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const base = `/api/projects/${projectId}/interactive`, polling = jobs.some(active);
  useEffect(() => {
    if (!supported) return;
    let alive = true, timer: ReturnType<typeof setTimeout> | undefined;
    async function refresh() {
      try {
        const data = await request<{jobs: Job[]}>(`${base}/jobs`);
        if (!alive) return;
        setJobs(data.jobs);
        if (data.jobs.some(active)) timer = setTimeout(refresh, 1500);
      } catch {if (alive) setError('Could not refresh interactive history. Check your local session.');}
    }
    void refresh();
    return () => {alive = false; if (timer) clearTimeout(timer);};
  }, [base, supported, polling]);
  useEffect(() => {if (hasUnsavedChanges) {setReview(null); setConfirmed(false);}}, [hasUnsavedChanges]);
  if (!supported) return null;
  const body = {...(binding ? {} : {fixture_id: fixture}), timeout_seconds: seconds,
    completion: {logical_name: logical, scope_test_id: null, locators: [{strategy: 'test_id', value: marker, role: null}]}};
  function invalidate() {setReview(null); setConfirmed(false); setError('');}
  async function inspect() {
    setBusy(true); invalidate();
    try {setReview(await request<Review>(`${base}/${binding ? 'local/review' : 'review'}`, 'POST', body));}
    catch {setError('Review failed. Check saved settings, input references and the explicit completion marker.');}
    finally {setBusy(false);}
  }
  async function enqueue() {
    if (!review || !confirmed) return;
    setBusy(true); setError('');
    const digest = review.contract_fingerprint;
    setReview(null); setConfirmed(false);
    try {
      const job = await request<Job>(`${base}/${binding ? 'local/jobs' : 'jobs'}`, 'POST', {...body, confirmed_contract_fingerprint: digest});
      setJobs(previous => [job, ...previous].slice(0, 20));
    } catch {
      setError('Queue confirmation failed or was interrupted. Check history before reviewing another submission; the request may already be queued.');
      try {setJobs((await request<{jobs: Job[]}>(`${base}/jobs`)).jobs);} catch { /* Keep the uncertainty visible. */ }
    } finally {setBusy(false);}
  }
  return <section className="plan-review interactive-panel" aria-label="Controlled interactive forms">
    <h3>Controlled interactive forms</h3>
    <p className="hint">This workflow supports the saved owned local fixture only. It permits one form submission and keeps inputs and results on this computer.</p>
    {binding && <label>Expected form outcome<select aria-label="Expected form outcome" value={outcome} onChange={event => {setOutcome(event.target.value as 'accepted' | 'rejected'); invalidate();}}><option value="accepted">Positive response</option><option value="rejected">Negative response</option></select></label>}
    {hasUnsavedChanges && <p role="status">Save configuration changes before reviewing an interactive submission.</p>}
    <p>Expected outcome: <strong>{logical.replaceAll('.', ' ')}</strong></p>
    {!ready && <p role="status">Save data-change permission and the required references: {required.join(', ')}. Values belong in your local worker environment.</p>}
    <label>Completion test ID<input value={marker} maxLength={160} onChange={event => {setMarker(event.target.value); invalidate();}}/></label>
    <label>Operation timeout (seconds)<input type="number" min={5} max={30} value={seconds} onChange={event => {setSeconds(Number(event.target.value)); invalidate();}}/></label>
    <button disabled={!ready || busy || !marker.trim() || seconds < 5 || seconds > 30} onClick={() => void inspect()}>Review interactive submission</button>
    {review && <div aria-label="Interactive review confirmation">
      <p className="hint">Review complete. No form was submitted. The completion marker must be absent before the click and visible after the expected server outcome.</p>
      <label className="check"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}/><span>I authorize this one submission on my owned local fixture.</span></label>
      <button disabled={!ready || !confirmed || busy || polling} onClick={() => void enqueue()}>Queue one interactive submission</button>
    </div>}
    <p className="hint">A separate local worker processes queued jobs. Unknown completion is never retried automatically. Screenshots are disabled for this workflow.</p>
    {error && <p className="message error" role="alert">{error}</p>}
    {!jobs.length && <p className="hint">No interactive jobs yet.</p>}
    {jobs.map(job => <div className="discovery-job" key={job.job_id}>
      <span><code>{job.job_id.slice(0, 8)}</code><strong>{job.status.replaceAll('_', ' ')}</strong>
        {job.result && <small>Result: {job.result.status}; submissions: {job.result.attempted_submissions === null ? 'unknown' : job.result.attempted_submissions}</small>}</span>
      {active(job) && <button disabled={busy || job.status === 'cancel_requested'} onClick={() => {
        setBusy(true); setError('');
        void request<Job>(`${base}/jobs/${job.job_id}/cancel`, 'POST', {}).then(updated => setJobs(previous => previous.map(item => item.job_id === updated.job_id ? updated : item)))
          .catch(() => setError('Could not confirm cancellation. Refresh history to check the current status.')).finally(() => setBusy(false));
      }}>Cancel interactive job</button>}
    </div>)}
  </section>;
}
