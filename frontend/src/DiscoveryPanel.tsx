import {useEffect, useState} from 'react';

type Job = {job_id: string; status: string};
type Report = {execution_authorized: false; inspected_pages: number; discovery_status: string;
  counts: {catalog: number; selected: number; skipped: number; blocked: number};
  cases: {case_id: string; name: string; test_type: string; decision: string; reason: string}[]};
type Props = {projectId: string; configured: boolean;
  request: <T>(path: string, method?: string, body?: unknown) => Promise<T>;
  onReport: (report: Report) => void};
const active = (job: Job) => ['queued', 'running', 'cancel_requested'].includes(job.status);

export function DiscoveryPanel({projectId, configured, request, onReport}: Props) {
  const [jobs, setJobs] = useState<Job[]>([]), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const [historical, setHistorical] = useState(false);
  const [loading, setLoading] = useState(true);
  const base = `/api/projects/${projectId}/discovery`;
  const polling = jobs.some(active);
  useEffect(() => {
    let alive = true, timer: ReturnType<typeof setTimeout> | undefined;
    async function refresh() {
      try {
        const data = await request<{jobs: Job[]}>(base);
        if (!alive) return;
        setJobs(data.jobs);
        setLoading(false);
        if (data.jobs.some(active)) timer = setTimeout(refresh, 1500);
      } catch {if (alive) {setLoading(false); setError('Could not refresh discovery. Check your session and reopen the project.');}}
    }
    void refresh();
    return () => {alive = false; if (timer) clearTimeout(timer);};
  }, [projectId, polling]);
  async function action(task: () => Promise<void>) {
    setBusy(true); setError(''); setHistorical(false);
    try {await task();} catch {setError('Discovery request failed. Save the controlled local target, check your session, or try again.');}
    finally {setBusy(false);}
  }
  return <section className="plan-review" aria-label="Discovery jobs"><h3>Discover your local fixture</h3>
    <p className="hint">Queue read-only discovery of the controlled local fixture. A separately running worker processes it. This does not run tests.</p>
    <button disabled={!configured || loading || busy || polling} onClick={() => void action(async () => {
      const job = await request<Job>(base, 'POST', {}); setJobs(previous => [job, ...previous].slice(0, 20));
    })}>Queue local discovery</button>
    {error && <p role="alert" className="message error">{error}</p>}
    {historical && <p role="status">This report uses older target or policy settings. Queue new discovery before reviewing it as the current plan.</p>}
    {!jobs.length && <p className="hint">No discovery jobs yet.</p>}
    {jobs.map(job => <div className="discovery-job" key={job.job_id}><span><code>{job.job_id.slice(0, 8)}</code><strong>{job.status.replaceAll('_', ' ')}</strong></span>
      {active(job) && <button disabled={busy || job.status === 'cancel_requested'} onClick={() => void action(async () => {
        const updated = await request<Job>(`${base}/${job.job_id}/cancel`, 'POST', {});
        setJobs(previous => previous.map(item => item.job_id === job.job_id ? updated : item));
      })}>Cancel discovery</button>}
      {job.status === 'completed' && <button disabled={busy} onClick={() => void action(async () => {
        const result = await request<{report: Report; configuration_current: boolean}>(`${base}/${job.job_id}`);
        if (!result.configuration_current) {setHistorical(true); return;}
        onReport(result.report);
      })}>Review discovery plan</button>}
    </div>)}
  </section>;
}
