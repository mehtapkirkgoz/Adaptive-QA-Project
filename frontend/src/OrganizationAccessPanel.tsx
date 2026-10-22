import {useEffect, useState} from 'react';
import type {FormEvent} from 'react';

type Member = {user_id: string; email: string; role: string};
type Usage = {pending_runs: number; active_runs: number; daily_admitted_runs: number};
type Quota = {max_pending_runs: number; max_active_runs: number; max_daily_runs: number};
type Props = {base: string; role: string; request: <T>(path: string, method?: string, body?: unknown) => Promise<T>};

export function OrganizationAccessPanel({base, role, request}: Props) {
  const [members, setMembers] = useState<Member[]>([]), [usage, setUsage] = useState<Usage | null>(null);
  const [quota, setQuota] = useState<Quota | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const manage = role === 'owner' || role === 'admin';
  async function load() {
    const [snapshot, detail] = await Promise.all([request<Usage>(`${base}/usage`), request<{quota: Quota}>(base)]);
    const rows = manage ? (await request<{members: Member[]}>(`${base}/members`)).members : [];
    return {snapshot, quota: detail.quota, rows};
  }
  function show(data: Awaited<ReturnType<typeof load>>) {setUsage(data.snapshot); setQuota(data.quota); setMembers(data.rows);}
  function fail() {setMembers([]); setUsage(null); setQuota(null); setError('Could not update organization access. Reopen the organization and check your role.');}
  useEffect(() => {let alive = true;
    load().then(data => {if (alive) show(data);}).catch(() => {if (alive) fail();});
    return () => {alive = false;};
  }, [base, role, request]);
  async function perform(task: () => Promise<void>) {
    setBusy(true); setError('');
    try {await task(); show(await load());} catch {fail();} finally {setBusy(false);}
  }
  function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget, data = new FormData(form);
    void perform(async () => {await request(`${base}/members`, 'PUT', {email: String(data.get('email')), role: String(data.get('role'))}); form.reset();});
  }
  return <section className="plan-review" aria-label="Organization access and usage"><h4>Access and usage</h4>
    {error && <p role="alert" className="message error">{error}</p>}
    {usage && quota && <p>Pending: {usage.pending_runs} / {quota.max_pending_runs} · Active: {usage.active_runs} / {quota.max_active_runs} · UTC daily admissions: {usage.daily_admitted_runs} / {quota.max_daily_runs}</p>}
    <p className="hint">Snapshot at last refresh. Cancelled admissions still count toward the daily limit.</p>
    <button disabled={busy} onClick={() => void perform(async () => {})}>Refresh access and usage</button>
    {manage && <><form onSubmit={add}><fieldset disabled={busy}>
      <label>Existing account email<input type="email" name="email" required maxLength={254}/></label>
      <label>New member role<select name="role" aria-label="New member role" defaultValue="member"><option value="member">Member</option>
        <option value="viewer">Viewer</option>{role === 'owner' && <option value="admin">Admin</option>}</select></label>
      <button>Add existing member</button></fieldset></form>
      <p className="hint">Accounts must be provisioned locally first. No account creation, email invitation or ownership transfer occurs here.</p>
      <ul>{members.map(member => {const editable = member.role !== 'owner' && (role === 'owner' || member.role !== 'admin');
        return <li key={member.user_id}><span>{member.email} · {member.role}</span>
          {editable && <><label>Role for {member.email}<select aria-label={`Role for ${member.email}`} disabled={busy} value={member.role} onChange={event => {
            const next = event.target.value;
            void perform(async () => {await request(`${base}/members`, 'PUT', {email: member.email, role: next});});
          }}><option value="member">Member</option><option value="viewer">Viewer</option>{role === 'owner' && <option value="admin">Admin</option>}</select></label>
            <button disabled={busy} onClick={() => void perform(async () => {await request(`${base}/members/${member.user_id}/remove`, 'POST', {});})}>Remove {member.email}</button></>}
        </li>;})}</ul></>}
  </section>;
}
