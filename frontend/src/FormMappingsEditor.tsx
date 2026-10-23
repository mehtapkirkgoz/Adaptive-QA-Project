import {useState} from 'react';

export type FormMapping = {logical_name: string; scope_test_id: string | null;
  locators: {strategy: string; value: string; role: string | null}[]};

const controls = [['login.username', 'Login username'], ['login.password', 'Login password'],
  ['login.submit', 'Login submit'], ['search.query', 'Search query'], ['search.submit', 'Search submit']];

export function FormMappingsEditor({value, onChange}: {value: FormMapping[]; onChange: (value: FormMapping[]) => void}) {
  const [strategies, setStrategies] = useState<Record<string, string>>({});
  const [scopes, setScopes] = useState<Record<string, string>>({});
  function replace(key: string, mapping: FormMapping | null) {
    onChange([...value.filter(item => item.logical_name !== key), ...(mapping ? [mapping] : [])]);
  }
  return <details><summary>Custom form controls</summary>
    <p className="hint">Optional project overrides replace defaults. Enter one exact name per line, up to 20.
      Leave names empty to use defaults. Multiple matching controls remain blocked. Do not enter credentials.</p>
    {controls.map(([key, name]) => {
      const existing = value.find(item => item.logical_name === key);
      const button = key.endsWith('.submit');
      const strategy = strategies[key] ?? existing?.locators[0]?.strategy ?? (button ? 'role' : 'label');
      function update(text: string, kind = strategy, scope = scopes[key] ?? existing?.scope_test_id ?? null) {
        const names = text.split('\n').map(item => item.trim()).filter(Boolean);
        replace(key, names.length ? {logical_name: key, scope_test_id: scope || null,
          locators: names.map(item => ({strategy: kind, value: item, role: kind === 'role' ? 'button' : null}))} : null);
      }
      return <div key={key} className="plan-review">
        <label>{name} matching<select aria-label={`${name} matching`} defaultValue={strategy} onChange={event => {
          setStrategies(previous => ({...previous, [key]: event.target.value}));
          update(existing?.locators.map(item => item.value).join('\n') ?? '', event.target.value);
        }}>
          {button ? <option value="role">Button name</option> : <option value="label">Field label</option>}
          <option value="test_id">Test ID</option>
        </select></label>
        <label>{name} alternatives<textarea aria-label={`${name} alternatives`} rows={2} maxLength={4096}
          defaultValue={existing?.locators.map(item => item.value).join('\n') ?? ''}
          onChange={event => update(event.target.value)}/></label>
        <label>{name} scope test ID<input aria-label={`${name} scope test ID`} maxLength={200} defaultValue={existing?.scope_test_id ?? ''}
          onChange={event => {
            setScopes(previous => ({...previous, [key]: event.target.value}));
            update(existing?.locators.map(item => item.value).join('\n') ?? '', strategy, event.target.value);
          }}/></label>
      </div>;
    })}
  </details>;
}
