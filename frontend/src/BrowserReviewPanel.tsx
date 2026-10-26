import {useEffect, useState} from 'react';

type Status = 'passed' | 'failed' | 'blocked' | 'not_run';
type Review = {review_id: string; name: string; target: string; period: string;
  source: 'browser_review'; counts: Record<Status, number>; notes: string[];
  checks: {id: string; name: string; status: Status; evidence: string}[]};
type Request = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
const labels: Record<Status, string> = {passed: 'Passed', failed: 'Failed', blocked: 'Blocked', not_run: 'Not run'};

export function BrowserReviewPanel({request}: {request: Request}) {
  const [reviews, setReviews] = useState<Review[]>([]), [selected, setSelected] = useState('');
  const [filter, setFilter] = useState<Status | 'all'>('all'), [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  async function load() {
    setLoading(true); setError('');
    try {
      const data = await request<{reviews: Review[]}>('/api/browser-reviews');
      setReviews(data.reviews);
      setSelected(previous => data.reviews.some(r => r.review_id === previous) ? previous : data.reviews[0]?.review_id ?? '');
    } catch {setError('Could not load saved browser reviews. Your existing results are preserved.');}
    finally {setLoading(false);}
  }
  useEffect(() => {void load();}, []);
  const review = reviews.find(item => item.review_id === selected);
  return <section className="card browser-reviews" id="reports" aria-label="Saved browser reviews">
    <div className="section-label"><div><p className="eyebrow">YOUR SAVED REPORTS</p><h2>Browser reviews</h2></div>
      <button type="button" disabled={loading} onClick={() => {void load();}}>Refresh reports</button></div>
    <p className="hint">Saved observations from a live browser review. These are separate from the automatic check above. Opening a report never starts a test.</p>
    {loading && <p role="status">Loading saved reports…</p>}
    {error && <p role="alert" className="message error">{error}</p>}
    {!loading && !error && !reviews.length && <p>No browser reviews saved yet. Automatic website checks remain available above.</p>}
    {!!reviews.length && <><label htmlFor="browser-review-choice">Choose a report · {reviews.length} saved</label>
      <select id="browser-review-choice" value={selected} onChange={event => {setSelected(event.target.value); setFilter('all');}}>
        {reviews.map(item => <option key={item.review_id} value={item.review_id}>{item.name} · {item.period}</option>)}
      </select></>}
    {review && <div className="browser-review-detail"><h3>{review.name}</h3><p className="site-check-url">{review.target}</p>
      <p className="hint">{review.period} · Imported browser observations · Not an automatic engine run</p>
      <div className="site-check-totals">{(Object.keys(labels) as Status[]).map(status => <div key={status}><strong>{review.counts[status]}</strong><span>{labels[status]}</span></div>)}</div>
      <label htmlFor="browser-review-filter">Show checks</label><select id="browser-review-filter" value={filter} onChange={event => setFilter(event.target.value as Status | 'all')}>
        <option value="all">All checks</option>{(Object.keys(labels) as Status[]).map(status => <option key={status} value={status}>{labels[status]}</option>)}
      </select>
      <div className="browser-review-checks">{review.checks.filter(item => filter === 'all' || item.status === filter).map(item => <article key={item.id}>
        <div><span className={`review-status ${item.status}`}>{labels[item.status]}</span><strong>{item.name}</strong></div>
        <p>{item.evidence}</p><small>{item.id}</small></article>)}</div>
      {!review.checks.some(item => filter === 'all' || item.status === filter) && <p>No checks in this category.</p>}
      {!!review.notes.length && <details className="check-scope"><summary>Scope and review notes</summary><ul>{review.notes.map((note, i) => <li key={i}>{note}</li>)}</ul></details>}
    </div>}
  </section>;
}
