import {useState} from 'react';

type Props = {candidates: string[]; names?: Record<string, string>; selection: string[];
  disabled: boolean; labelPrefix: string; onChange: (selection: string[]) => void};

export function CaseSelector({candidates, names = {}, selection, disabled, labelPrefix, onChange}: Props) {
  const [query, setQuery] = useState('');
  const needle = query.trim().toLowerCase();
  const visible = candidates.filter(id => `${id} ${names[id] ?? ''}`.toLowerCase().includes(needle));
  return <div className="case-selector" aria-label="Test case selection">
    <label>Search eligible tests<input type="search" value={query} maxLength={100}
      placeholder="Search by test ID or name" onChange={event => setQuery(event.target.value)}/></label>
    <div className="case-selection-summary">
      <p role="status">{selection.length} of 10 selected · {visible.length} of {candidates.length} eligible tests shown</p>
      <button type="button" disabled={disabled || !selection.length} onClick={() => onChange([])}>Clear selection</button>
    </div>
    <p className="hint">Filtering keeps checked tests selected, including tests hidden by the search.</p>
    <div className="case-options" role="group" aria-label="Eligible tests">
      {visible.map(id => <label className="check" key={id}>
        <input type="checkbox" aria-label={`${labelPrefix} ${id}`} checked={selection.includes(id)}
          disabled={disabled || (!selection.includes(id) && selection.length >= 10)}
          onChange={event => onChange(event.target.checked ? [...selection, id] : selection.filter(value => value !== id))}/>
        <span><strong>{id}</strong>{names[id] && <small>{names[id]}</small>}</span>
      </label>)}
      {!visible.length && <p className="hint">{candidates.length ? 'No eligible tests match this search.' : 'No executable UI tests are available in this plan.'}</p>}
    </div>
  </div>;
}
