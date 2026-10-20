"""Bounded breadth-first traversal with explicit coverage limitations."""

from collections import deque
from dataclasses import dataclass
import math
from time import monotonic
from typing import Callable
from urllib.parse import urljoin, urlsplit, urlunsplit

from adaptive_qa.config import extract_hostname
from adaptive_qa.discovery import PageSnapshot


@dataclass(frozen=True)
class CrawlBudget:
    max_pages: int = 5
    max_depth: int = 2
    max_requests: int = 100
    timeout_seconds: float = 30

    def __post_init__(self):
        for name, value, minimum, maximum in (
            ('max_pages', self.max_pages, 1, 50),
            ('max_depth', self.max_depth, 0, 5),
            ('max_requests', self.max_requests, 1, 200),
        ):
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f'{name} must be an integer between {minimum} and {maximum}.')
        if (isinstance(self.timeout_seconds, bool)
                or not isinstance(self.timeout_seconds, (int, float))
                or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 120):
            raise ValueError('timeout_seconds must be finite and between 0 and 120 seconds.')


@dataclass(frozen=True)
class CrawlResult:
    pages: tuple[PageSnapshot, ...]
    attempted_pages: int
    limitations: tuple[str, ...]


def canonical_url(url: str) -> str:
    """Exclude credentials, fragments, and queries from traversal identifiers."""
    hostname = extract_hostname(url)
    parsed = urlsplit(url)
    host = f'[{hostname}]' if ':' in hostname else hostname
    default_port = 443 if parsed.scheme == 'https' else 80
    authority = host if parsed.port in (None, default_port) else f'{host}:{parsed.port}'
    result = urlunsplit((parsed.scheme, authority, parsed.path or '/', '', ''))
    if len(result) > 2048:
        raise ValueError('Traversal URL exceeds the length limit.')
    return result


def crawl_pages(start_url: str, budget: CrawlBudget, *,
                authorize: Callable[[str], object],
                load: Callable[[str, float], PageSnapshot],
                clock: Callable[[], float] = monotonic) -> CrawlResult:
    """Traverse authorized links; load must enforce network and operation limits.

    The local runner supplies an isolated process for a hard total deadline.
    No result implies site-wide coverage, even when the frontier is exhausted.
    """
    if not isinstance(budget, CrawlBudget):
        raise ValueError('budget must be a CrawlBudget.')
    start = canonical_url(start_url)
    authorize(start)
    frontier = deque([(start, 0)])
    seen = {start}
    visited = set()
    pages = []
    reasons = set()
    attempted = 0
    deadline = clock() + budget.timeout_seconds
    while frontier:
        remaining = deadline - clock()
        if remaining <= 0:
            reasons.add('time_limit')
            break
        if attempted >= budget.max_pages:
            reasons.add('page_limit')
            break
        url, depth = frontier.popleft()
        if url in visited:
            continue
        attempted += 1
        try:
            authorize(url)
            snapshot = load(url, remaining)
            if not isinstance(snapshot, PageSnapshot):
                raise ValueError('Loader returned an invalid snapshot.')
            final_url = canonical_url(snapshot.url)
            authorize(final_url)
        except Exception:
            # Never expose exception text, which may contain target secrets.
            reasons.add('page_load_or_policy_error')
            continue
        if clock() >= deadline:
            reasons.add('time_limit')
            break
        if final_url in visited:
            visited.add(url)
            continue
        visited.update((url, final_url))
        seen.add(final_url)
        pages.append(snapshot)
        if not snapshot.collection_complete:
            reasons.add('incomplete_page')
        for link in snapshot.links:
            try:
                target = canonical_url(urljoin(final_url, link.href))
                if target in seen:
                    continue
                authorize(target)
            except ValueError:
                reasons.add('excluded_link')
                continue
            if depth >= budget.max_depth:
                reasons.add('depth_limit')
            elif len(seen) >= 500:
                reasons.add('frontier_limit')
            else:
                seen.add(target)
                frontier.append((target, depth + 1))
    return CrawlResult(tuple(pages), attempted, tuple(sorted(reasons)))
