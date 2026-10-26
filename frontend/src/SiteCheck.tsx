import {useEffect, useRef, useState} from 'react';
import type {ReactNode} from 'react';
import {DemoLoginPanel} from './DemoLoginPanel';

type Result = {case_id: string; status: string; message: string; reason_code?: string; duration_seconds: number; evidence_id?: string};
type Check = {check_id: string; project_id: string; url: string; status: string; inspected_pages?: number;
  requested?: number; not_run?: number; names?: Record<string, string>; results?: Result[]; run_id?: string; diagnostic_code?: string};
type Props = {demoProjectId?: string; request: <T>(path: string, method?: string, body?: unknown) => Promise<T>; tools: ReactNode; feedback: ReactNode; onOptionsOpen: (projectId?: string) => void; onCheckCreated: (projectId: string) => void; hasUnsavedOptions: boolean; edition: string; onSignOut?: () => void};
const reasons: Record<string, string> = {
  native_number_passed: 'The browser enforced the declared number bound on an isolated field copy. The live field was unchanged and no form was submitted.',
  native_number_failed: 'The isolated number field did not enforce its declared bound as expected.',
  native_number_unavailable: 'No unique editable number field with the required declared bound was available; no verdict is possible.',
  native_email_passed: 'Browser email validation matched the expected outcome on an isolated field copy. No page input or submission occurred.',
  native_email_failed: 'Browser email validation did not match the expected outcome. Existing field constraints were preserved.',
  native_email_unavailable: 'No unique editable email field was available for this probe; no pass or fail verdict is possible.',
  source_html_passed: 'The initial HTML structure satisfied this check. Scripts, images and styles were excluded.',
  source_html_assertion_failed: 'The initial HTML structure did not satisfy this check.',
  html_document_not_loaded: 'The target HTML could not be loaded reliably. Check access, TLS and the exact saved address.',
  destination_or_coverage_blocked: 'A destination or required rendered resource was blocked by the saved safety scope.',
  document_execution_incomplete: 'The document check could not finish reliably.',
  document_deadline_exceeded: 'The check exceeded its time limit.', document_process_error: 'The isolated test process could not return a valid result.'};
const active = (check: Check | null) => !!check && ['discovering', 'testing', 'cancelling'].includes(check.status);
function outcomeStatus(check: Check) {
  if (check.status !== 'completed' || !check.results?.length) return check.status;
  const verdicts=check.results.filter(result=>['passed','failed'].includes(result.status));
  if (!verdicts.length) return 'execution_error';
  return verdicts.length < check.results.length ? 'partial' : check.status;
}
const stages: Record<string, string> = {discovering: 'Inspecting the site…', testing: 'Running applicable checks…',
  cancelling: 'Stopping the check…', partial: 'Check finished with incomplete tests', completed: 'Check finished', cancelled: 'Check stopped',
  execution_error: 'Tests could not be evaluated', error: 'Check could not finish', interrupted: 'Check interrupted when the application closed', no_tests: 'No applicable checks found'};
const accessReasons: Record<string,string> = {
  dns_resolution_failed: 'The domain name could not be resolved on this computer. Check the spelling and whether the address opens in your browser. DNS may also be temporarily unavailable.',
  destination_blocked: 'The address resolved outside the supported public destination scope. Private network addresses are not supported by this check.',
  tls_verification_failed: 'The HTTPS certificate could not be verified. The connection was stopped before inspecting the page.',
  connection_failed: 'A connection to the website could not be established. Check that the exact HTTPS address is reachable from this computer.',
  inspection_timeout: 'The site inspection exceeded its time limit. The server may be slow or unreachable; no website verdict is available.',
  access_denied: 'The server refused or limited access (HTTP 401, 403 or 429). Sign-in or bot protection may prevent automatic inspection.',
  target_http_error: 'The website returned an unsuccessful HTTP response, so its page could not be inspected.',
  redirect_outside_scope: 'The page redirected to a different hostname outside this check. Open the address in your browser and use its final HTTPS URL, including www if present.',
  inspection_process_error: 'The isolated inspection process could not return usable page evidence. This is a technical error, not a failed website test.',
  inspection_unavailable: 'No usable page could be inspected. Check the final HTTPS address, website availability and access requirements.'};

export function SiteCheck({request, tools, feedback, onOptionsOpen, onCheckCreated, hasUnsavedOptions, edition, onSignOut, demoProjectId}: Props) {
  const [url, setUrl] = useState(''), [check, setCheck] = useState<Check | null>(null);
  const [history, setHistory] = useState<Check[]>([]), [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const serial = useRef(0);
  useEffect(() => {let alive = true;
    request<{checks: Check[]}>('/api/site-checks').then(data => {
      if (!alive) return;
      setHistory(data.checks); setCheck(data.checks[0] ?? null); setUrl(data.checks[0]?.url ?? '');
    }).catch(() => {if (alive) setError('Could not load previous checks. Refresh the page to restore your saved results.');})
      .finally(() => {if (alive) setLoading(false);});
    return () => {alive = false;};
  }, []);
  useEffect(() => {
    if (!active(check)) return;
    let alive = true, timer: ReturnType<typeof setTimeout> | undefined;
    const id = check!.check_id, version = serial.current;
    async function poll() {
      try {
        const next = await request<Check>(`/api/site-checks/${id}`);
        if (!alive || version !== serial.current) return;
        setCheck(next);
        setHistory(previous => [next, ...previous.filter(item => item.check_id !== id)].slice(0, 20));
        if (active(next)) timer = setTimeout(poll, 1000);
      } catch {if (alive) setError('Could not refresh progress. Refreshing this page will not start another check.');}
    }
    timer = setTimeout(poll, 600);
    return () => {alive = false; clearTimeout(timer);};
  }, [check?.check_id, check?.status]);
  async function start() {
    setBusy(true); setError(''); serial.current += 1;
    try {
      const next = await request<Check>('/api/site-checks', 'POST', {url: url.trim()});
      setCheck(next); setHistory(previous => [next, ...previous].slice(0, 20)); onCheckCreated(next.project_id);
    } catch {setError('Could not start the check. Use a valid HTTPS URL and wait for any running check to finish. Existing custom project settings are preserved; review Test options if needed.');}
    finally {setBusy(false);}
  }
  const results = check?.results ?? [];
  const passed = results.filter(result => result.status === 'passed');
  const failed = results.filter(result => result.status === 'failed');
  const other = results.filter(result => !['passed', 'failed'].includes(result.status));
  const unrecorded = Math.max(0, (check?.requested ?? 0) - results.length);
  const groups = [{title: 'Passed checks', items: passed, kind: 'passed'},
    {title: 'Failed checks', items: failed, kind: 'failed'}, {title: 'Not evaluated', items: other, kind: 'other'}];
  return <div className="site-check-shell"><header className="site-check-header"><a className="brand" href="/"> <span className="mark">AQ</span> Adaptive QA</a>
    <div className="header-actions"><span className="badge">{edition}</span>{onSignOut && <button onClick={onSignOut}>Sign out</button>}</div></header>
    <main className="site-check-main"><section className="site-check-hero"><p className="eyebrow">YOUR WEBSITE, CLEAR RESULTS</p>
      <h1>Check your website.</h1><p>Enter a website address. We inspect it, choose applicable checks and show what passed, what failed and what could not be evaluated.</p>
      <form onSubmit={event => {event.preventDefault(); void start();}} className="site-check-form">
        <label htmlFor="site-url">Website URL</label><div className="site-check-input">
          <input id="site-url" type="url" required maxLength={512} placeholder="https://example.com" value={url}
            disabled={busy || active(check)} onChange={event => setUrl(event.target.value)}/>
          <button className="primary" type="submit" disabled={loading || busy || active(check) || hasUnsavedOptions}>{busy ? 'Starting…' : active(check) ? 'Checking…' : 'Test website'}</button></div>
        <p className="hint">Read-only checks. No sign-in, form submissions or data changes. Results stay on this computer.</p>
      </form>
      {hasUnsavedOptions && <p className="message">Save your option edits before starting a check. Your draft has not been applied.</p>}
      <ol className="site-check-steps"><li>1 · Enter a URL</li><li>2 · Automatic checks</li><li>3 · Review results</li></ol>
    </section>
    {feedback}
    {error && <p role="alert" className="message error">{error}</p>}
    {loading && <p role="status">Opening your local workspace…</p>}
    {check && <section className="card site-check-results" aria-label="Website check results">
      <div className="section-label"><div><h2 aria-live="polite">{stages[outcomeStatus(check)] ?? 'Waiting for the check'}</h2><p className="site-check-url">{check.url}</p></div>
        {active(check) && <button disabled={busy || check.status === 'cancelling'} onClick={async () => {
          setBusy(true); try {setCheck(await request<Check>(`/api/site-checks/${check.check_id}/cancel`, 'POST', {}));}
          catch {setError('Could not request a stop. Refresh the status and try again.');} finally {setBusy(false);}
        }}>Stop check</button>}</div>
      {active(check) && <p role="status" className="site-check-progress">{check.status === 'discovering'
        ? 'Inspecting pages and available features. You do not need to run any commands.'
        : check.status === 'testing' ? `${results.length} / ${check.requested ?? 0} check results recorded. Work continues in the background.` : 'Stopping safely…'}</p>}
      <div className="site-check-totals"><div><strong>{results.length ? passed.length : "—"}</strong><span>Passed</span></div><div><strong>{results.length ? failed.length : "—"}</strong><span>Failed</span></div>
        <div><strong>{results.length ? other.length : "—"}</strong><span>Not evaluated</span></div><div><strong>{check.inspected_pages ?? '—'}</strong><span>Pages inspected</span></div></div>
      {!active(check) && ['error', 'interrupted', 'execution_error'].includes(outcomeStatus(check)) && <p className="message error">Technical or access errors prevented a reliable verdict. This is not evidence that your website failed. Review the recorded outcomes below. A retry only starts when you press Test website.</p>}
      {!active(check) && accessReasons[check.diagnostic_code ?? ''] && <p className="message error" role="status">{accessReasons[check.diagnostic_code!]}</p>}
      {!active(check) && !results.length && <p className="message" role="status"><strong>No tests were evaluated.</strong> No pass or fail verdict is available for this check.</p>}
      {groups.map(group => !!group.items.length && <section className={`site-check-group ${group.kind}`} key={group.kind}><h3>{group.title} · {group.items.length}</h3>
        {group.items.map(result => <article key={result.case_id}><strong>{check.names?.[result.case_id] ?? result.case_id}</strong>
          {result.status !== 'passed' && <p>{result.status === 'passed' ? 'The expected condition was satisfied.' : result.status === 'failed'
            ? 'The expected condition was not satisfied. Open the details to review the check.' : 'A reliable verdict was not available. This is a technical outcome, not a failed website assertion.'}</p>}
          <details><summary>Check details</summary><p>{check.names?.[result.case_id]} · {result.case_id} · {result.duration_seconds.toFixed(2)} sec · {result.status}</p><p>{reasons[result.reason_code ?? ''] ?? result.message}</p></details>
          {result.evidence_id && check.run_id && <a target="_blank" rel="noopener noreferrer" href={`/api/projects/${check.project_id}/runs/${check.run_id}/evidence/${result.evidence_id}`}>View screenshot</a>}
        </article>)}</section>)}
      {!active(check) && <details className="check-scope"><summary>What was covered?</summary><p className="hint">HTML checks inspect the initial page structure with scripts and assets excluded. Native email and number checks exercise declared browser constraints on isolated copies of discovered fields without changing the live form. They do not validate visual rendering, JavaScript behavior or server responses. These results cover the checks actually run, not your entire website. Discovery inspects up to five pages and runs up to ten applicable read-only checks.
        {check.not_run !== undefined && ` ${check.not_run} catalog checks were not included in this run.`}
        {unrecorded > 0 && ` ${unrecorded} selected checks produced no result.`} Sign-in, API and database checks require additional configuration.</p></details>}
    </section>}
    <DemoLoginPanel projectId={check?.project_id ?? demoProjectId} request={request} hasUnsavedChanges={hasUnsavedOptions} onProjectCreated={onCheckCreated}/>
    <details className="workspace-options" open={location.hash === '#advanced' ? true : undefined} onToggle={event => {if (event.currentTarget.open) onOptionsOpen(check?.project_id);}}>
      <summary><strong>Test options</strong><span>Optional saved sites, API and database settings</span></summary>
      <p className="hint">A URL is enough for the automatic read-only check. Use these options only when you need a specific project or an explicit API/database contract. Saving settings does not start a test.</p>
      <fieldset disabled={busy || active(check)}>{tools}</fieldset>
    </details>
    {history.length > 1 && <section className="site-check-history"><h2>Previous checks</h2>{history.slice(1).map(item => <button key={item.check_id} disabled={active(check) || busy}
      onClick={() => {serial.current += 1; setCheck(item); setUrl(item.url); setHistory(previous => [item, ...previous.filter(row => row.check_id !== item.check_id)]);}}>{item.url}<span>{stages[outcomeStatus(item)] ?? item.status}</span></button>)}</section>}
    </main><footer>ADAPTIVE QA <span>Local workspace · Clear results</span></footer></div>;
}
