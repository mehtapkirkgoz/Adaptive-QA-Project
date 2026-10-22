import {useState} from 'react';
import {demoCatalog} from './demo-catalog';
import './demo.css';

type View = 'Overview' | 'Test catalog' | 'Example report';
const projects = [
  {name: 'Northstar Store', kind: 'E-commerce', host: 'store.example.test', features: ['Login', 'Search', 'Products', 'Cart', 'Forms']},
  {name: 'Editorial Studio', kind: 'Content website', host: 'journal.example.test', features: ['Search', 'Navigation', 'Forms']},
  {name: 'Atlas Portal', kind: 'Business portal', host: 'portal.example.test', features: ['Login', 'Forms', 'Navigation']},
];
const examples = [
  {id: 'LOGIN-001', name: 'Login form is visible', status: 'Passed', note: 'Required fields and submit action are visible.'},
  {id: 'SEARCH-001', name: 'Search field is visible', status: 'Passed', note: 'An accessible search input was found.'},
  {id: 'DOC-001', name: 'Document title', status: 'Failed', note: 'Illustration: the example page has an empty title.'},
  {id: 'API-001', name: 'API configuration', status: 'Blocked', note: 'No API contract supplied in this example.'},
  {id: 'DB-001', name: 'Database configuration', status: 'Blocked', note: 'No database reference supplied in this example.'},
];

export function DemoWorkspace() {
  const [view, setView] = useState<View>('Overview');
  const [project, setProject] = useState(0);
  const [query, setQuery] = useState('');
  const [layer, setLayer] = useState('all');
  const selected = projects[project];
  const rows = demoCatalog.filter(row => (layer === 'all' || row.test_type === layer)
    && `${row.case_id} ${row.name}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="demo-shell">
    <aside className="demo-sidebar">
      <a className="brand" href="./"><span className="mark">AQ</span> Adaptive QA</a>
      <p className="eyebrow">YOUR WORKSPACE</p>
      <nav aria-label="Demo navigation">{(['Overview', 'Test catalog', 'Example report'] as View[]).map((item, index) =>
        <button key={item} aria-label={item} className={view === item ? 'demo-nav active' : 'demo-nav'} aria-current={view === item ? 'page' : undefined}
          onClick={() => setView(item)}><span aria-hidden="true">{['◫', '▤', '◷'][index]}</span>{item}{item === 'Test catalog' && <small>100</small>}</button>)}</nav>
      <div className="demo-local"><span className="dot"/> Explore with confidence<p>This is a public interface demo.<br/>Real execution stays in your local workspace.</p></div>
    </aside>
    <div className="demo-body">
      <header><div>Workspace <span className="slash">/</span> {view}</div><div className="header-actions"><span className="demo-mode">INTERACTIVE DEMO</span><span className="demo-avatar" aria-label="Demo workspace">AQ</span></div></header>
      <main>
        <div className="demo-notice" role="note"><span aria-hidden="true">◉</span><div><strong>Explore the interface. Your systems stay untouched.</strong><p>Sample projects and illustrative results only. No sign-in, API calls, saved data or test execution.</p></div></div>
        <div className="demo-heading"><div><p className="eyebrow">ADAPTIVE QUALITY ASSURANCE</p><h1>{view === 'Overview' ? 'A clearer view of quality.' : view}</h1><p className="subtitle">{view === 'Overview' ? 'Discover capabilities. Choose the right checks. Keep the evidence.' : view === 'Test catalog' ? '100 defined scenarios across UI, API and database layers.' : 'An illustrative report showing how outcomes remain distinct.'}</p></div><span className="demo-outline">Local execution · controlled scope</span></div>
        {view === 'Overview' && <>
          <section className="demo-stats" aria-label="Accepted catalog counts">{[['100', 'Defined scenarios', 'Across three testing layers'], ['51', 'UI scenarios', 'Forms, navigation & accessibility'], ['34', 'API scenarios', 'Explicit endpoint contracts'], ['15', 'Database scenarios', 'Read-only query validation']].map(([value, title, hint]) =>
            <article className="demo-stat" key={title}><p>{title}</p><strong>{value}</strong><span>{hint}</span></article>)}</section>
          <div className="demo-grid"><section className="demo-card"><div className="demo-section-title"><div><p className="eyebrow">SAMPLE PROJECTS</p><h2>A plan shaped by your application</h2></div><span className="demo-pill">3 examples</span></div>
            <div className="demo-projects">{projects.map((item, index) => <button key={item.name} className={project === index ? 'demo-project selected' : 'demo-project'} aria-pressed={project === index} onClick={() => setProject(index)}><span className="project-icon" aria-hidden="true">{['▦', '▤', '◈'][index]}</span><span>{item.name}<small>{item.kind}</small></span><span className="demo-chevron" aria-hidden="true">›</span></button>)}</div>
            <div className="demo-project-detail"><div className="demo-detail-label">EXAMPLE TARGET <span>Not contacted</span></div><p className="demo-host">{selected.host}</p><div className="demo-tags">{selected.features.map(feature => <span key={feature}>{feature}</span>)}</div><p className="hint">These capabilities are illustrative, not AI discovery results. The real planner uses observed features and explicit configuration.</p></div>
          </section>
          <section className="demo-card demo-journey"><p className="eyebrow">FROM URL TO EVIDENCE</p><h2>A deliberate testing workflow</h2><p className="subtitle">Every action has a clear boundary.</p>{[['01', 'Discover', 'Inspect authorized pages and identify supported capabilities.'], ['02', 'Review the plan', 'See selected, skipped and blocked checks before execution.'], ['03', 'Run locally', 'Start explicitly approved checks in isolated worker processes.'], ['04', 'Review the evidence', 'Inspect outcomes, screenshots and historical comparisons.']].map(([number, title, text]) => <div className="demo-stage" key={number}><span>{number}</span><div><h3>{title}</h3><p>{text}</p></div></div>)}<button className="primary" onClick={() => setView('Test catalog')}>Explore the test catalog <span aria-hidden="true">→</span></button></section></div>
          <section className="demo-card demo-bottom"><div><span className="demo-pill">EVIDENCE, NOT ASSUMPTIONS</span><h2>Different outcomes tell different stories.</h2><p className="subtitle">A missing capability, an assertion failure and an execution error are recorded separately.</p></div><button onClick={() => setView('Example report')}>View example report →</button></section>
        </>}
        {view === 'Test catalog' && <section className="demo-card"><div className="demo-filters"><label>Search scenarios<input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search by ID or name"/></label><label>Testing layer<select value={layer} onChange={e => setLayer(e.target.value)}><option value="all">All layers</option><option value="ui">UI</option><option value="api">API</option><option value="database">Database</option></select></label><p role="status">{rows.length} definitions</p></div><p className="hint">Catalog size is not the number of checks applicable to every website. Prerequisites and configuration determine selection.</p><div className="demo-table-scroll"><table><thead><tr><th>Scenario</th><th>Layer</th><th>Prerequisites</th><th>Data policy</th></tr></thead><tbody>{rows.map(row => <tr key={row.case_id}><td><strong>{row.case_id}</strong><details><summary>{row.name}</summary><p>{row.expected_result}</p></details></td><td><span className="demo-pill">{row.test_type.toUpperCase()}</span></td><td>{row.required_features.join(', ') || 'Inspected document'}</td><td>{row.changes_data ? 'Explicit write permission' : 'Read-only definition'}</td></tr>)}</tbody></table>{rows.length === 0 && <p className="empty">No matching scenarios. Try another search.</p>}</div></section>}
        {view === 'Example report' && <section className="demo-card"><div className="demo-section-title"><div><p className="eyebrow">ILLUSTRATIVE REPORT</p><h2>Sample outcome breakdown</h2></div><span className="demo-pill">Synthetic data · no run performed</span></div><p className="subtitle">The rows below explain result states. They are not a live run or acceptance evidence.</p><div className="demo-table-scroll"><table><thead><tr><th>Example check</th><th>Outcome</th><th>Explanation</th></tr></thead><tbody>{examples.map(row => <tr key={row.id}><td><strong>{row.name}</strong></td><td><span className={'demo-result ' + row.status.toLowerCase()}>{row.status}</span></td><td>{row.note}</td></tr>)}</tbody></table></div><div className="demo-report-note"><strong>Execution is available in the local application.</strong><p>Use a locally provisioned account to configure a project, review its real plan and explicitly start supported tests. This public demo stores nothing.</p></div></section>}
      </main><footer>ADAPTIVE QA <span>Purposeful checks. Reviewable evidence.</span></footer>
    </div>
  </div>;
}
