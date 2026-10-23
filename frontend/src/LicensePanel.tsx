import {useEffect, useState} from 'react';

type Status = {status: string; execution_allowed: boolean; max_projects?: number | null; max_concurrent_runs?: number; expires_at?: number};
type Request = <T>(path: string, method?: string, body?: unknown) => Promise<T>;

export function LicensePanel({request}: {request: Request}) {
  const [status, setStatus] = useState<Status | null>(null);
  const [document, setDocument] = useState('');
  const [busy, setBusy] = useState(false), [message, setMessage] = useState('');
  async function refresh() {
    try {setStatus(await request<Status>('/api/local/license'));}
    catch {setMessage('License status could not be loaded.');}
  }
  useEffect(() => {void refresh(); const timer = setInterval(() => void refresh(), 30000); return () => clearInterval(timer);}, []);
  return <section className="card" aria-label="Local license"><h2>Local license</h2>
    <p>Targets, credentials and test results stay on this computer. License verification works locally.</p>
    <p role="status">{status ? `License: ${status.status}. ${status.execution_allowed ? `Project limit: ${status.max_projects ?? 'Unlimited'}. Concurrent executions: ${status.max_concurrent_runs}.` : 'Execution is unavailable. Existing records remain accessible.'}` : 'Loading license status…'}</p>
    {status?.expires_at && <p>Expires: {new Date(status.expires_at * 1000).toLocaleString()}</p>}
    <form onSubmit={event => {event.preventDefault(); setBusy(true); setMessage('');
      void request<Status>('/api/local/license', 'POST', {document}).then(value => {setStatus(value); setDocument(''); setMessage('Verified license installed.');})
        .catch(() => setMessage('License rejected. The previous license was preserved.'))
        .finally(() => setBusy(false));}}>
      <label>Signed license document<textarea value={document} onChange={event => setDocument(event.target.value)} maxLength={8192} required rows={4}/></label>
      <button className="primary" disabled={busy}>Install license</button>
    </form>{message && <p role="status">{message}</p>}
  </section>;
}
