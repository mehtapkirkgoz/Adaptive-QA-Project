"""Trusted local imports of browser observations, never automatic engine verdicts."""
from collections import Counter
import hashlib
import json
from urllib.parse import urlsplit

from adaptive_qa.project_store import ProjectNotFound

STATUSES = ('passed', 'failed', 'blocked', 'not_run')


def _text(value, maximum):
    if (not isinstance(value, str) or not value.strip() or len(value) > maximum
            or any(ord(c) < 32 and c not in '\n\t' for c in value)):
        raise ValueError('Bounded review text is required.')
    return value


def validate_review(data):
    if not isinstance(data, dict) or set(data) != {'name', 'target', 'period', 'checks', 'notes'}:
        raise ValueError('Invalid browser review fields.')
    name = _text(data['name'], 160)
    target = _text(data['target'], 512)
    parsed = urlsplit(target)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.port not in (None, 443)):
        raise ValueError('An HTTPS report target without credentials or query is required.')
    period = _text(data['period'], 80)
    if not isinstance(data['checks'], list) or not 1 <= len(data['checks']) <= 200:
        raise ValueError('A bounded check list is required.')
    checks, identities = [], set()
    for item in data['checks']:
        if not isinstance(item, dict) or set(item) != {'id', 'name', 'status', 'evidence'}:
            raise ValueError('Invalid review check.')
        identity = _text(item['id'], 100)
        if identity in identities or item['status'] not in STATUSES:
            raise ValueError('Review identities and statuses must be unambiguous.')
        identities.add(identity)
        checks.append(dict(id=identity, name=_text(item['name'], 300), status=item['status'],
                           evidence=_text(item['evidence'], 3000)))
    if not isinstance(data['notes'], list) or len(data['notes']) > 20:
        raise ValueError('A bounded notes list is required.')
    result = dict(name=name, target=target, period=period, checks=checks,
                  notes=[_text(note, 3000) for note in data['notes']])
    if len(json.dumps(result).encode()) > 65536:
        raise ValueError('Review is too large.')
    return result


class BrowserReviews:
    def __init__(self, projects):
        self.projects = projects

    def import_review(self, actor, project_id, data):
        """Trusted offline operation; no HTTP import or target execution endpoint."""
        self.projects.get(actor, project_id)
        payload = validate_review(data)
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        identity = hashlib.sha256((actor.user_id + project_id + raw).encode()).hexdigest()[:32]
        with self.projects._connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_browser_reviews ('
                      'sequence INTEGER PRIMARY KEY AUTOINCREMENT, review_id TEXT UNIQUE NOT NULL, '
                      'owner_id TEXT NOT NULL, project_id TEXT NOT NULL, review_json TEXT NOT NULL)')
            c.execute('INSERT OR IGNORE INTO dashboard_browser_reviews '
                      '(review_id,owner_id,project_id,review_json) VALUES (?,?,?,?)',
                      (identity, actor.user_id, project_id, raw))
        return identity

    def list(self, actor):
        self.projects._actor(actor)
        with self.projects._connection() as c:
            if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dashboard_browser_reviews'").fetchone():
                return []
            rows = c.execute('SELECT * FROM dashboard_browser_reviews WHERE owner_id=? '
                             'ORDER BY sequence DESC LIMIT 20', (actor.user_id,)).fetchall()
        output = []
        for row in rows:
            try:
                self.projects.get(actor, row['project_id'])
            except ProjectNotFound:
                continue
            payload = validate_review(json.loads(row['review_json']))
            counts = Counter(check['status'] for check in payload['checks'])
            output.append(dict(review_id=row['review_id'], project_id=row['project_id'],
                               source='browser_review', execution_authorized=False,
                               **payload, counts={status: counts[status] for status in STATUSES}))
        return output
