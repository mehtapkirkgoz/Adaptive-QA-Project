import {FormMappingsEditor} from './FormMappingsEditor';
import type {FormMapping} from './FormMappingsEditor';
import {useEffect, useState} from 'react';
import type {FormEvent} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';
import './plan.css';
import {DiscoveryPanel} from './DiscoveryPanel';
import {RunPanel} from './RunPanel';
import {DemoWorkspace} from './DemoWorkspace';
import {LicensePanel} from './LicensePanel';
import {OrganizationPanel} from './OrganizationPanel';
import {ExecutionScope, supportsDiscovery, matchesSavedTarget} from './ExecutionScope';

type Project = {project_id: string; name: string};
type Plan = {execution_authorized: false; inspected_pages: number; discovery_status: string; discovery_job_id?: string;
  counts: {catalog: number; selected: number; skipped: number; blocked: number};
  cases: {case_id: string; name: string; test_type: string; decision: string; reason: string; target_binding?: string | null; document_path?: string | null; document_url?: string | null; changes_data?: boolean}[]};
type Settings = {form_mappings?: FormMapping[]; discovery_support?: {supported: boolean; profile: string | null; execution_scope: string}; configured: boolean; base_url?: string; allowed_hosts?: string[];
  allow_data_changes?: boolean; available_secret_references: Record<string, string>;
  secret_references?: Record<string, {environment_variable: string; value: string}>};
class ApiError extends Error { constructor(public status: number, message: string) {super(message);} }
async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== 'GET') {
    headers['Content-Type'] = 'application/json';
    const csrf = document.cookie.split('; ').find(c => c.startsWith('adaptive_csrf='));
    if (csrf) headers['X-CSRF-Token'] = decodeURIComponent(csrf.split('=')[1]);
  }
  const response = await fetch(path, {method, headers, credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(15000)});
  if (!response.ok) throw new ApiError(response.status, response.status === 401
    ? 'Sign in again to continue.' : response.status === 404 ? 'Project is unavailable.'
    : response.status === 400 ? 'Check your input. Changes were not saved.' : 'Request failed. Please try again.');
  return response.json() as Promise<T>;
}

function App() {
  const [freeEdition, setFreeEdition] = useState(false);
  const [licensedEdition, setLicensedEdition] = useState(false);
  const [signedIn, setSignedIn] = useState(false), [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const [projects, setProjects] = useState<Project[]>([]), [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Project | null>(null), [settings, setSettings] = useState<Settings | null>(null);
  const [target, setTarget] = useState(''), [hosts, setHosts] = useState(''), [changes, setChanges] = useState(false);
  const [slots, setSlots] = useState<string[]>([]);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [formMappings, setFormMappings] = useState<FormMapping[]>([]);
  function clear() {setSignedIn(false); setProjects([]); setSelected(null); setSettings(null); setPlan(null); setTarget(''); setHosts(''); setSlots([]); setFormMappings([]); setChanges(false); setOffset(0);}
  function fail(e: unknown) {if (e instanceof ApiError && e.status === 401) clear(); setError(e instanceof Error ? e.message : 'Request failed.');}
  async function perform(task: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try {await task();} catch (e) {fail(e);} finally {setBusy(false);}
  }
  async function load(page = 0) {
    const data = await api<{projects: Project[]}>(`/api/projects?limit=20&offset=${page}`);
    setProjects(data.projects); setOffset(page);
  }
  useEffect(() => {let alive = true;
    (async () => {try {const session = await api<{edition?: string}>('/api/auth/me');
      if (alive) {setFreeEdition(session.edition === 'free'); setLicensedEdition(session.edition === 'professional');}
      const data = await api<{projects: Project[]}>('/api/projects');
      if (alive) {setProjects(data.projects); setSignedIn(true);}
    } catch (e) {if (alive && !(e instanceof ApiError && e.status === 401)) fail(e);}
    finally {if (alive) setChecking(false);}})();
    return () => {alive = false;};
  }, []);
  async function choose(project: Project) {
    await perform(async () => {
      setSelected(null); setSettings(null); setPlan(null);
      const data = await api<Settings>(`/api/projects/${project.project_id}/configuration`);
      setSelected(project); setSettings(data); setTarget(data.base_url ?? '');
      setHosts(data.allowed_hosts?.join('\n') ?? ''); setChanges(data.allow_data_changes ?? false);
      setSlots(Object.keys(data.secret_references ?? {})); setFormMappings(data.form_mappings ?? []);
    });
  }
  function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget, data = new FormData(form);
    const email = String(data.get('email')), password = String(data.get('password'));
    form.reset();
    void perform(async () => {await api('/api/auth/login', 'POST', {email, password});
      const session = await api<{edition?: string}>('/api/auth/me'); setLicensedEdition(session.edition === 'professional');
      setSignedIn(true); await load();});
  }
  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget, name = String(new FormData(form).get('name'));
    void perform(async () => {await api('/api/projects', 'POST', {name}); form.reset(); await load(); setNotice('Project created. Select it to configure your target.');});
  }
  function rename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selected) return;
    const name = String(new FormData(event.currentTarget).get('name'));
    void perform(async () => {const project = await api<Project>(`/api/projects/${selected.project_id}`, 'PATCH', {name});
      setSelected(project); await load(offset); setNotice('Project name saved.');});
  }
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selected || !settings) return;
    const secret_references = Object.fromEntries(slots.map(slot => [slot, settings.available_secret_references[slot]]));
    void perform(async () => {const data = await api<Settings>(`/api/projects/${selected.project_id}/configuration`, 'PUT', {
      base_url: target, allowed_hosts: hosts.split('\n').map(h => h.trim()).filter(Boolean), allow_data_changes: changes, secret_references, form_mappings: formMappings});
      setSettings(data); setPlan(null); setNotice('Configuration saved. No tests were started.');});
  }
  return <div className="shell">
    <aside><a className="brand" href="/" aria-label="Adaptive QA home"><span className="mark">AQ</span> Adaptive QA</a>
      <p className="eyebrow">WORKSPACE</p><div className="nav-item">Projects <span aria-hidden="true">●</span></div>
      <div className="sidebar-note"><span className="dot"/> Local workspace<p>Configure with confidence.<br/>Keep every project in scope.</p></div>
    </aside>
    <div className="workspace"><header><span>Workspace <span className="slash">/</span> Projects</span><div className="header-actions"><span className="badge">{freeEdition ? 'FREE · LOCAL' : 'LOCAL'}</span>
      {signedIn && !freeEdition && <button className="quiet" disabled={busy} onClick={() => void perform(async () => {await api('/api/auth/logout', 'POST', {}); clear();})}>Sign out</button>}</div></header>
      <main><div className="page-title"><div><p className="eyebrow">ADAPTIVE TESTING</p><h1>{signedIn ? 'Project workspace' : 'Welcome to your workspace'}</h1>
        <p className="subtitle">{signedIn ? 'Manage your projects and define what is in scope.' : 'Sign in to manage your QA projects.'}</p></div><span className="step">LOCAL WORKSPACE</span></div>
        {error && <div role="alert" className="message error">{error}</div>}
        {notice && <div role="status" className="message success">{notice}</div>}
        {checking ? <p role="status">Checking your session…</p> : !signedIn ? <section className="card login"><p className="eyebrow">YOUR ACCOUNT</p><h2>Sign in</h2>
          <form onSubmit={login}><fieldset disabled={busy}><label>Email<input name="email" type="email" autoComplete="username" required maxLength={254}/></label>
            <label>Password<input name="password" type="password" autoComplete="current-password" required/></label>
            <button className="primary" type="submit">{busy ? 'Signing in…' : 'Sign in'}</button></fieldset></form><p className="hint">Use the account created by your local workspace administrator.</p></section>
        : <>{!freeEdition && !licensedEdition && <OrganizationPanel request={api}/>}
            {licensedEdition && <LicensePanel request={api}/>}
            {freeEdition && <p className="hint">Free local edition: one active site/project. No account required. Targets and results stay on this computer.</p>}<section className="card create"><div><h2>Your projects</h2><p className="hint">Start with a name. Add target settings when you are ready.</p></div>
          <form onSubmit={create}><fieldset disabled={busy} className="inline"><label className="sr-only" htmlFor="new-project">New project name</label><input id="new-project" name="name" placeholder="New project name" required maxLength={100}/><button className="primary" disabled={freeEdition && projects.length > 0}>+ Create project</button></fieldset></form></section>
          <div className="columns"><section className="card project-list"><div className="section-label"><h2>Projects</h2><span className="count">{projects.length} on this page</span></div>
            {!projects.length && <div className="empty"><h3>No projects here yet</h3><p>Create a project to define your first testing scope.</p></div>}
            {projects.map(project => <button className={`project-row ${selected?.project_id === project.project_id ? 'selected' : ''}`} key={project.project_id} disabled={busy} onClick={() => void choose(project)}><span className="project-icon">▣</span><span>{project.name}<small>Project configuration</small></span><span className="arrow">→</span></button>)}
            <div className="pagination"><button disabled={busy || offset === 0} onClick={() => void perform(() => load(Math.max(0, offset - 20)))}>Previous</button><span>Page {offset / 20 + 1}</span><button disabled={busy || projects.length < 20} onClick={() => void perform(() => load(offset + 20))}>Next</button></div></section>
            <section className="card details">{!selected || !settings ? <div className="empty detail-empty"><span className="empty-icon">⌘</span><h2>{busy ? 'Loading…' : 'Select a project'}</h2><p>Review its target, allowed hosts and secret references.</p></div> : <>
              <div className="section-label"><h2>Project settings</h2><span className="badge">{settings.configured ? 'CONFIGURED' : 'NEW'}</span></div>
              <form onSubmit={rename} key={selected.project_id + selected.name}><fieldset disabled={busy}><div className="inline"><label>Project name<input name="name" defaultValue={selected.name} required maxLength={100}/></label><button type="submit">Rename</button></div></fieldset></form>
              <form onSubmit={save}><fieldset disabled={busy}><label>Target URL<input type="url" value={target} onChange={e => setTarget(e.target.value)} placeholder="http://127.0.0.1:8000/" maxLength={512} required/></label>
                <label>Allowed hosts<textarea value={hosts} onChange={e => setHosts(e.target.value)} rows={3} placeholder="127.0.0.1" required/></label><p className="hint">One exact hostname per line. No ports or wildcards.</p>
                <label className="check"><input type="checkbox" checked={changes} onChange={e => setChanges(e.target.checked)}/><span>Allow tests that change data</span></label>
                <FormMappingsEditor key={selected.project_id + JSON.stringify(settings)} value={formMappings} onChange={setFormMappings}/>
                <h3>Secret references</h3><p className="hint">Choose the references this project needs. Secret values are never entered or displayed here.</p>
                {Object.keys(settings.available_secret_references).map(slot => <label className="check" key={slot}><input type="checkbox" checked={slots.includes(slot)} onChange={e => setSlots(e.target.checked ? [...slots, slot] : slots.filter(s => s !== slot))}/><span>{slot.replaceAll('_', ' ')}{slots.includes(slot) && <small className="masked">[REDACTED]</small>}</span></label>)}
                {slots.length > 0 && <details><summary>Environment variable names</summary>{slots.map(slot => <code key={slot}>{settings.available_secret_references[slot]}</code>)}</details>}
                <div className="save-bar"><p className="hint">Saving configuration does not start a test.</p><button className="primary" type="submit">{busy ? 'Saving…' : 'Save configuration'}</button></div>
              </fieldset></form>
              <ExecutionScope settings={settings}/>
              <DiscoveryPanel key={'discovery:' + selected.project_id + JSON.stringify(settings)} projectId={selected.project_id} configured={supportsDiscovery(settings)} publicTarget={settings.discovery_support?.profile === 'public_https'} request={api} onReport={(report, jobId) => setPlan({...report, discovery_job_id: jobId})}/>
              <section className="plan-review"><h3>Test plan review</h3><p className="hint">Review the saved configuration. Unsaved edits are not included. Reviewing never starts tests or visits your target.</p>
                <button disabled={busy || !settings.configured} onClick={() => void perform(async () => {
                  setPlan(null); setPlan(await api<Plan>(`/api/projects/${selected.project_id}/plan`));
                })}>Review saved plan</button>
                {!settings.configured && <p className="hint">Save a target configuration first.</p>}
                {plan && <div aria-label="Plan review results"><p className="message">{plan.discovery_status === 'completed' ? `Discovery completed. ${plan.inspected_pages} pages inspected; uninspected routes remain outside this plan.` : 'Discovery has not run. No pages have been inspected. Features remain unknown.'}</p>
                  <p className="hint">Catalog: {plan.counts.catalog} · Selected: {plan.counts.selected} · Skipped: {plan.counts.skipped} · Blocked: {plan.counts.blocked}</p>
                  <p className="hint">Execution authorized: No. Configured references do not establish API or database bindings.</p>
                  <div className="plan-cases">{plan.cases.map(item => <details key={item.case_id}><summary>{item.case_id} · {item.name} · {item.decision}</summary><p>{item.test_type} — {item.reason}</p></details>)}</div>
                </div>}
              </section><RunPanel key={'runs:' + selected.project_id + JSON.stringify(settings)} projectId={selected.project_id} discoveryJobId={plan?.discovery_job_id}
                candidateNames={Object.fromEntries(plan?.cases.map(item => [item.case_id, item.name]) ?? [])}
                candidates={plan?.cases.filter(item => item.decision === 'selected' && item.test_type === 'ui' && matchesSavedTarget(settings, item) && item.changes_data === false).map(item => item.case_id) ?? []} request={api}/></>}
            </section></div><div className="roadmap"><span className="dot"/><p>Local discovery, explicit UI runs and owner-authorized screenshots are available.</p></div></>}
      </main><footer>ADAPTIVE QA <span>Controlled scope. Clear evidence.</span></footer>
    </div></div>;
}

createRoot(document.getElementById('root')!).render(import.meta.env.VITE_DEMO === 'true' ? <DemoWorkspace/> : <App/>);
