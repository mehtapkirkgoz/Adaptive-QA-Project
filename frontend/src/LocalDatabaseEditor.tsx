export type LocalDatabaseBinding = {table: string; expected_count: number};
type Props = {target: string; value: LocalDatabaseBinding | null; onChange: (value: LocalDatabaseBinding | null) => void};

export function LocalDatabaseEditor({target,value,onChange}: Props) {
  const supported=/^http:\/\/127\.0\.0\.1:8000\/?$/.test(target);
  return <section className="plan-review" aria-label="Explicit local database binding">
    <h3>Explicit local database binding</h3>
    <p className="hint">Count records in one owned SQLite fixture table. No SQL, row values or file paths are entered here. Saving never opens the database.</p>
    {!supported && <p className="hint">This controlled fixture profile requires the exact target http://127.0.0.1:8000/.</p>}
    <label className="check"><input type="checkbox" checked={!!value} disabled={!supported && !value} onChange={event => onChange(event.target.checked ? {table:'inventory',expected_count:0}:null)}/><span>Configure explicit database count</span></label>
    {value && <>
      <label>Database table name<input aria-label="Database table name" value={value.table} maxLength={64} pattern="[a-z][a-z0-9_]{0,63}" required onChange={event => onChange({...value,table:event.target.value})}/></label>
      <label>Expected database record count<input aria-label="Expected database record count" type="number" min={0} max={2147483647} step={1} required value={value.expected_count} onChange={event => onChange({...value,expected_count:Number(event.target.value)})}/></label>
      <p className="hint">Select the database path reference below and set its value only in your local worker environment. Only the fixed project fixture directory is permitted.</p>
    </>}
  </section>;
}
