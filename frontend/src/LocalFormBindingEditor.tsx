export type LocalResponse = {status_code: number; field_name: string; expected_value: boolean};
export type LocalFormSettings = {operation: 'login' | 'search'; document_url: string; endpoint_url: string;
  field_names: string[]; accepted: LocalResponse; rejected: LocalResponse};
type Props = {target: string; value: LocalFormSettings | null; onChange: (value: LocalFormSettings | null) => void};
const origin = 'http://127.0.0.1:8000';
export function LocalFormBindingEditor({target, value, onChange}: Props) {
  const local = /^http:\/\/127\.0\.0\.1:8000\/[A-Za-z0-9/_-]*$/.test(target) && !target.slice(origin.length).includes('//');
  function defaults(operation: 'login' | 'search'): LocalFormSettings {
    return {operation, document_url: target, endpoint_url: origin + '/form/submit', field_names: operation === 'login' ? ['user', 'password'] : ['query'],
      accepted: {status_code: 200, field_name: operation === 'login' ? 'authenticated' : 'hasResults', expected_value: true},
      rejected: {status_code: operation === 'login' ? 401 : 200, field_name: operation === 'login' ? 'authenticated' : 'hasResults', expected_value: false}};
  }
  function update(change: Partial<LocalFormSettings>) {if (value) onChange({...value, ...change, document_url: target});}
  return <section className="plan-review local-binding" aria-label="Reusable local form binding">
    <h3>Reusable local form binding</h3>
    <p className="hint">Configure one owned fixture at 127.0.0.1:8000. Only in-page POST forms with a single boolean JSON outcome are supported. General HTTPS targets remain read-only.</p>
    <label className="check"><input type="checkbox" checked={value !== null} disabled={!value && !local} onChange={event => onChange(event.target.checked ? defaults('login') : null)}/><span>Configure reusable local form</span></label>
    {!local && <p className="hint">Use an owned local document URL, or disable this binding before saving another target.</p>}
    {value && <>
      <label>Form operation<select aria-label="Form operation" value={value.operation} onChange={event => onChange(defaults(event.target.value as 'login' | 'search'))}><option value="login">Login</option><option value="search">Search</option></select></label>
      <p className="hint">Document: {target}. Input fields below are HTML names, never usernames, passwords or query values.</p>
      <label>POST endpoint URL<input type="url" value={value.endpoint_url} maxLength={256} onChange={event => update({endpoint_url: event.target.value})}/></label>
      {value.field_names.map((field, index) => <label key={index}>{value.operation === 'login' ? (index === 0 ? 'Username field name' : 'Password field name') : 'Query field name'}<input value={field} maxLength={40} onChange={event => update({field_names: value.field_names.map((name, item) => item === index ? event.target.value : name)})}/></label>)}
      {(['accepted', 'rejected'] as const).map(outcome => <div key={outcome} className="response-binding">
        <h4>{outcome === 'accepted' ? 'Positive' : 'Negative'} server response</h4>
        <label>{outcome} HTTP status<input type="number" min={200} max={499} value={value[outcome].status_code} onChange={event => update({[outcome]: {...value[outcome], status_code: Number(event.target.value)}})}/></label>
        <label>{outcome} JSON boolean field<input value={value[outcome].field_name} maxLength={40} onChange={event => update({[outcome]: {...value[outcome], field_name: event.target.value}})}/></label>
        <label>{outcome} expected boolean<select aria-label={`${outcome} expected boolean`} value={String(value[outcome].expected_value)} onChange={event => update({[outcome]: {...value[outcome], expected_value: event.target.value === 'true'}})}><option value="true">true</option><option value="false">false</option></select></label>
      </div>)}
      <p className="hint">Save configuration first. Saving does not contact the target or start a test. Required reference slots: {value.operation === 'login' ? 'login username and login password' : 'search query'}.</p>
    </>}
  </section>;
}
