export type LocalApiBinding = {path: string; expected_status: number; json_field?: string; expected_boolean?: boolean; profile?: 'public_https'; response_mode?: 'status_only'};
type Props = {target: string; publicHttpsEnabled: boolean; value: LocalApiBinding | null; onChange: (value: LocalApiBinding | null) => void};

export function LocalApiEditor({target, publicHttpsEnabled, value, onChange}: Props) {
  const local = /^http:\/\/127\.0\.0\.1:8000\/?$/.test(target);
  let https = false;
  try {const url = new URL(target); https = url.protocol === 'https:' && (!url.port || url.port === '443')
    && url.pathname === '/' && !url.search && !url.hash && !url.username && !url.password;} catch { /* Incomplete target. */ }
  const supported = local || (https && publicHttpsEnabled);
  const change = (update: Partial<LocalApiBinding>) => {if (value) onChange({...value, ...update});};
  return <section className="plan-review" aria-label="Explicit local API binding">
    <h3>Explicit API response binding</h3>
    <p className="hint">Configure one explicit GET endpoint and response contract. Saving does not contact the endpoint. No authentication, query values or request bodies are sent.</p>
    {!supported && <p className="hint">Use a public HTTPS origin on port 443 without a path/query, or the owned local fixture http://127.0.0.1:8000/.</p>}
    {https && !publicHttpsEnabled && <p className="hint">This running server does not support public HTTPS API bindings. Use the updated local runtime.</p>}
    <label className="check"><input type="checkbox" checked={!!value} disabled={!supported && !value}
      onChange={event => onChange(event.target.checked ? {path: '/api/health', expected_status: 200, ...(https ? {profile:'public_https' as const,response_mode:'status_only' as const} : {json_field:'ready',expected_boolean:true})} : null)}/><span>Configure explicit API response</span></label>
    {value && <>
      <label>API destination profile<select aria-label="API destination profile" value={value.profile ?? 'controlled_local'} onChange={event => {
        if (event.target.value === 'public_https') onChange({...value,profile:'public_https'});
        else onChange({path:value.path,expected_status:value.expected_status,json_field:value.json_field ?? 'ready',expected_boolean:value.expected_boolean ?? true});
      }}><option value="controlled_local" disabled={!local}>Owned local fixture</option><option value="public_https" disabled={!https || !publicHttpsEnabled}>Public HTTPS · read-only</option></select></label>
      {value.profile === 'public_https' && <label>API response assertion<select aria-label="API response assertion" value={value.response_mode ?? 'json_boolean'} onChange={event => onChange(event.target.value === 'status_only'
        ? {path:value.path,expected_status:value.expected_status,profile:'public_https',response_mode:'status_only'}
        : {path:value.path,expected_status:value.expected_status,profile:'public_https',json_field:'ready',expected_boolean:true})}>
        <option value="status_only">HTTP status only</option><option value="json_boolean">HTTP status and JSON boolean</option></select></label>}
      <label>GET endpoint path<input aria-label="GET endpoint path" value={value.path} maxLength={256} required onChange={event => change({path: event.target.value})}/></label>
      <label>Expected API HTTP status<input aria-label="Expected API HTTP status" type="number" min={200} max={499} step={1} required value={Number.isNaN(value.expected_status) ? '' : value.expected_status} onChange={event => {
        const status = event.target.valueAsNumber;
        event.target.setCustomValidity(status >= 300 && status < 400 ? 'Use a 2xx or 4xx status. Redirect expectations are not supported.' : '');
        change({expected_status: status});
      }}/></label>
      {value.response_mode !== 'status_only' && <>
        <label>API JSON boolean field<input aria-label="API JSON boolean field" value={value.json_field ?? ''} pattern="[A-Za-z][A-Za-z0-9_]{0,39}" maxLength={40} required onChange={event => change({json_field: event.target.value})}/></label>
        <label>Expected API boolean<select aria-label="Expected API boolean" value={String(value.expected_boolean ?? true)} onChange={event => change({expected_boolean: event.target.value === 'true'})}><option value="true">true</option><option value="false">false</option></select></label>
      </>}
      <p className="hint">Use a 2xx or 4xx status, optionally with one top-level JSON boolean. Status-only mode does not assert the response body. Public HTTPS requires an explicitly allowed public host and a valid TLS certificate; private IPs and redirect following are blocked. Review and confirm again after changes.</p>
    </>}
  </section>;
}
