import {FormMappingsEditor} from './FormMappingsEditor';
import type {FormMapping} from './FormMappingsEditor';
import {useEffect, useRef, useState} from 'react';
import type {FormEvent} from 'react';
import {DiscoveryPanel} from './DiscoveryPanel';
import {OrganizationRunPanel} from './OrganizationRunPanel';
import {OrganizationAccessPanel} from './OrganizationAccessPanel';
import {ExecutionScope, supportsDiscovery, matchesSavedTarget} from './ExecutionScope';

type Request = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
type Organization = {organization_id: string; name: string; role: string};
type Project = {project_id: string; organization_id: string; name: string};
type Settings = {form_mappings?: FormMapping[]; discovery_support?: {supported: boolean; profile: string | null; execution_scope: string}; configured: boolean; base_url?: string; allowed_hosts?: string[];
  allow_data_changes?: boolean;
  available_secret_references: Record<string, string>;
  secret_references?: Record<string, {environment_variable: string; value: string}>};

export function OrganizationPanel({request}: {request: Request}) {
  const [open, setOpen] = useState(false);
  return <section className="card"><button aria-expanded={open} onClick={() => setOpen(!open)}>Organizations</button>
    {open && <OrganizationWorkspace request={request}/>}</section>;
}

function OrganizationWorkspace({request}: {request: Request}) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selected, setSelected] = useState<Organization | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const [target, setTarget] = useState(''), [hosts, setHosts] = useState(''), [slots, setSlots] = useState<string[]>([]);
  const [maxProjects, setMaxProjects] = useState<number | null>(null);
  const [planSummary, setPlanSummary] = useState('');
  const [runPlan, setRunPlan] = useState<{jobId: string; candidates: string[]; names: Record<string, string>} | null>(null);
  const [formMappings, setFormMappings] = useState<FormMapping[]>([]);
  const generation = useRef(0);
  const canConfigure = selected?.role === 'owner' || selected?.role === 'admin';
  const path = selected ? `/api/organizations/${selected.organization_id}/projects` : '';
  function fail(e: unknown) {setError(e instanceof Error ? e.message : 'Organization request failed.');}
  async function perform(task: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try {await task();} catch (e) {fail(e);} finally {setBusy(false);}
  }
  useEffect(() => {let alive = true;
    request<{organizations: Organization[]}>('/api/organizations').then(data => {if (alive) setOrganizations(data.organizations);})
      .catch(e => {if (alive) fail(e);});
    return () => {alive = false; generation.current++;};
  }, [request]);
  function choose(organization: Organization) {
    const epoch = ++generation.current;
    setSelected(null); setProjects([]); setProject(null); setSettings(null); setMaxProjects(null); setPlanSummary(''); setRunPlan(null);
    void perform(async () => {
      const [list, detail] = await Promise.all([
        request<{projects: Project[]}>(`/api/organizations/${organization.organization_id}/projects`),
        request<{role: string; quota: {max_projects: number}}>(`/api/organizations/${organization.organization_id}`)]);
      if (epoch !== generation.current) return;
      setSelected({...organization, role: detail.role}); setProjects(list.projects); setMaxProjects(detail.quota.max_projects);
    });
  }
  function chooseProject(value: Project) {
    const epoch = ++generation.current;
    setProject(null); setSettings(null); setPlanSummary(''); setRunPlan(null);
    void perform(async () => {
      const data = await request<Settings>(`${path}/${value.project_id}/configuration`);
      if (epoch !== generation.current) return;
      setProject(value); setSettings(data); setTarget(data.base_url ?? ''); setHosts(data.allowed_hosts?.join('\n') ?? '');
      setSlots(Object.keys(data.secret_references ?? {})); setFormMappings(data.form_mappings ?? []);
    });
  }
  function createOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget, name = String(new FormData(form).get('name'));
    void perform(async () => {await request('/api/organizations', 'POST', {name});
      setOrganizations((await request<{organizations: Organization[]}>('/api/organizations')).organizations);
      form.reset(); setNotice('Organization created.');});
  }
  function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget, name = String(new FormData(form).get('name'));
    void perform(async () => {await request(path, 'POST', {name});
      setProjects((await request<{projects: Project[]}>(path)).projects); form.reset(); setNotice('Organization project created.');});
  }
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!project || !settings) return;
    const secret_references = Object.fromEntries(slots.map(slot => [slot, settings.available_secret_references[slot]]));
    void perform(async () => {
      setSettings(await request<Settings>(`${path}/${project.project_id}/configuration`, 'PUT', {
        base_url: target, allowed_hosts: hosts.split('\n').map(h => h.trim()).filter(Boolean),
        allow_data_changes: settings.allow_data_changes ?? false, secret_references, form_mappings: formMappings}));
      setNotice('Organization configuration saved. No work was started.');
      setPlanSummary('');
      setRunPlan(null);
    });
  }
  return <div aria-label="Organization workspace">
    <p className="hint">Shared membership and project settings. Personal projects remain separate.</p>
    {error && <p role="alert" className="message error">{error}</p>}
    {notice && <p role="status" className="message success">{notice}</p>}
    <form onSubmit={createOrganization}><fieldset disabled={busy} className="inline">
      <label>New organization name<input name="name" required maxLength={100}/></label><button>Create organization</button>
    </fieldset></form>
    {!organizations.length && <p className="hint">No organizations available.</p>}
    <div>{organizations.map(organization => <button key={organization.organization_id} disabled={busy}
      onClick={() => choose(organization)}>{organization.name} · {organization.role}</button>)}</div>
    {selected && <div><h3>{selected.name}</h3><p className="hint">Role: {selected.role} · Projects: {projects.length} / {maxProjects}</p>
      <OrganizationAccessPanel key={selected.organization_id} base={`/api/organizations/${selected.organization_id}`} role={selected.role} request={request}/>
      {canConfigure && <form onSubmit={createProject}><fieldset disabled={busy} className="inline">
        <label>Organization project name<input name="name" required maxLength={100}/></label><button>Create shared project</button>
      </fieldset></form>}
      {projects.map(value => <button key={value.project_id} disabled={busy} onClick={() => chooseProject(value)}>{value.name}</button>)}
      {project && settings && <><form onSubmit={save}><h3>{project.name}</h3><fieldset disabled={busy || !canConfigure}>
        <label>Organization target URL<input type="url" required maxLength={512} value={target} onChange={e => setTarget(e.target.value)}/></label>
        <label>Organization allowed hosts<textarea aria-label="Organization allowed hosts" required rows={3} value={hosts} onChange={e => setHosts(e.target.value)}/></label>
        <p className="hint">One exact hostname per line. Existing data-change policy is retained; new shared projects default to read-only.</p>
        <FormMappingsEditor key={project.project_id + JSON.stringify(settings)} value={formMappings} onChange={setFormMappings}/>
        <h4>Organization secret references</h4>
        {Object.keys(settings.available_secret_references).map(slot => <label className="check" key={slot}>
          <input type="checkbox" checked={slots.includes(slot)} onChange={e => setSlots(e.target.checked ? [...slots, slot] : slots.filter(s => s !== slot))}/>
          <span>{slot.replaceAll('_', ' ')}{slots.includes(slot) && <small>[REDACTED]</small>}</span></label>)}
        {slots.length > 0 && <details><summary>Organization environment variable names</summary>
          {slots.map(slot => <code key={slot}>{settings.available_secret_references[slot]}</code>)}</details>}
        {canConfigure && <button>Save shared configuration</button>}
      </fieldset><p className="hint">Saving does not visit the target or queue tests. Review current discovery before explicitly starting selected tests.</p></form>
        <ExecutionScope settings={settings}/>
        <DiscoveryPanel key={'shared-discovery:' + project.project_id + JSON.stringify(settings)} projectId={project.project_id}
          basePath={`${path}/${project.project_id}`} configured={supportsDiscovery(settings)} publicTarget={settings.discovery_support?.profile === 'public_https'}
          canExecute={['owner', 'admin', 'member'].includes(selected.role)} request={request}
          onReport={(report, jobId) => {
            setPlanSummary(`Inspected pages: ${report.inspected_pages}. Catalog: ${report.counts.catalog}. Selected: ${report.counts.selected}. Execution authorized: No.`);
            setRunPlan({jobId, names: Object.fromEntries(report.cases.map(item => [item.case_id, item.name])), candidates: report.cases.filter(item => item.decision === 'selected' && item.test_type === 'ui'
              && matchesSavedTarget(settings, item) && item.changes_data === false).map(item => item.case_id)});
          }}/>
        {planSummary && <p role="status">{planSummary}</p>}
        <OrganizationRunPanel key={'shared-runs:' + project.project_id + JSON.stringify(settings)} base={`${path}/${project.project_id}`}
          candidateNames={runPlan?.names} discoveryJobId={runPlan?.jobId} candidates={runPlan?.candidates ?? []}
          canExecute={['owner', 'admin', 'member'].includes(selected.role)} request={request}/>
      </>}
    </div>}
  </div>;
}
