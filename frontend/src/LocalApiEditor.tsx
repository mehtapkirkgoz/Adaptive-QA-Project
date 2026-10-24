export type LocalApiBinding = {path: string; expected_status: number; json_field: string; expected_boolean: boolean};
type Props = {target: string; value: LocalApiBinding | null; onChange: (value: LocalApiBinding | null) => void};

export function LocalApiEditor({target, value, onChange}: Props) {
  const supported = /^http:\/\/127\.0\.0\.1:8000\/?$/.test(target);
  const change = (update: Partial<LocalApiBinding>) => {if (value) onChange({...value, ...update});};
  return <section className="plan-review" aria-label="Explicit local API binding">
    <h3>Explicit local API binding</h3>
    <p className="hint">Configure one GET endpoint on your owned local API. Saving does not inspect the endpoint or start a test. No authentication or request values are sent by this profile.</p>
    {!supported && <p className="hint">This profile requires the exact target http://127.0.0.1:8000/ and its allowed hostname. Public APIs are not enabled.</p>}
    <label className="check"><input type="checkbox" checked={!!value} disabled={!supported && !value}
      onChange={event => onChange(event.target.checked ? {path: '/api/health', expected_status: 200, json_field: 'ready', expected_boolean: true} : null)}/><span>Configure explicit API response</span></label>
    {value && <>
      <label>GET endpoint path<input aria-label="GET endpoint path" value={value.path} maxLength={256} required onChange={event => change({path: event.target.value})}/></label>
      <label>Expected API HTTP status<input aria-label="Expected API HTTP status" type="number" min={200} max={499} step={1} required value={Number.isNaN(value.expected_status) ? '' : value.expected_status} onChange={event => {
        const status = event.target.valueAsNumber;
        event.target.setCustomValidity(status >= 300 && status < 400 ? 'Use a 2xx or 4xx status. Redirect expectations are not supported.' : '');
        change({expected_status: status});
      }}/></label>
      <label>API JSON boolean field<input aria-label="API JSON boolean field" value={value.json_field} pattern="[A-Za-z][A-Za-z0-9_]{0,39}" maxLength={40} required onChange={event => change({json_field: event.target.value})}/></label>
      <label>Expected API boolean<select aria-label="Expected API boolean" value={String(value.expected_boolean)} onChange={event => change({expected_boolean: event.target.value === 'true'})}><option value="true">true</option><option value="false">false</option></select></label>
      <p className="hint">Use a 2xx or 4xx status and one top-level boolean field. Redirect expectations, queries and secret values are not supported. Disable this binding before changing to another target.</p>
    </>}
  </section>;
}
