"""Read-only deterministic matching; alternatives are a union, never first-match wins."""

from dataclasses import dataclass
from time import monotonic

from playwright.sync_api import ElementHandle, Error, Page

from adaptive_qa.element_models import ElementMapping, LocatorStrategy, MatchResult, MatchStatus


@dataclass
class BoundElement:
    result: MatchResult
    handle: ElementHandle | None = None

    def close(self):
        if self.handle is not None:
            try:
                self.handle.dispose()
            except Error:
                pass
            self.handle = None


_VISIBLE = """el => el.isConnected && !el.closest('[hidden], [inert], [aria-hidden="true"]') &&
    getComputedStyle(el).visibility !== 'hidden' && getComputedStyle(el).visibility !== 'collapse' &&
    el.getClientRects().length > 0"""


def match_element(page: Page, mapping: ElementMapping) -> BoundElement:
    """Bind one current visible DOM element; callers own total process deadlines.

    A static handle cannot silently retarget after DOM replacement. Matching does
    not click/fill, wait for delayed UI, or treat visibility as actionability.
    """
    if not isinstance(mapping, ElementMapping):
        raise ValueError('mapping must be an ElementMapping.')
    handles = []
    selected = None
    started = monotonic()
    def outcome(status, count, reason, indexes=()):
        return BoundElement(MatchResult(mapping.logical_name, status, count, reason, indexes), selected)
    try:
        root = page
        if mapping.scope_test_id is not None:
            root = page.get_by_test_id(mapping.scope_test_id)
            count = root.count()
            if count != 1:
                return outcome(MatchStatus.ERROR, 0, 'Scope must identify exactly one DOM element.')
        rules = []
        for spec in mapping.locators:
            if spec.strategy == LocatorStrategy.ROLE:
                locator = root.get_by_role(spec.role, name=spec.value, exact=True)
            elif spec.strategy == LocatorStrategy.LABEL:
                locator = root.get_by_label(spec.value, exact=True)
            else:
                locator = root.get_by_test_id(spec.value)
            rules.append(locator)
        union = rules[0]
        for locator in rules[1:]:
            union = union.or_(locator)
        if union.count() > 200:
            return outcome(MatchStatus.ERROR, 0, 'Candidate limit exceeded.')
        handles = union.element_handles()
        if len(handles) > 200:
            return outcome(MatchStatus.ERROR, 0, 'Candidate limit exceeded.')
        visible = []
        for handle in handles:
            if monotonic() - started > 5:
                return outcome(MatchStatus.ERROR, 0, 'Matching operation budget exceeded.')
            if handle.is_visible() and handle.evaluate(_VISIBLE):
                visible.append(handle)
        if not visible:
            return outcome(MatchStatus.MISSING, 0, 'No visible candidate matches the configured alternatives.')
        indexes = tuple(index for index, locator in enumerate(rules)
                        if locator.evaluate_all('(elements, targets) => targets.some(target => elements.includes(target))', visible))
        if monotonic() - started > 5:
            return outcome(MatchStatus.ERROR, 0, 'Matching operation budget exceeded.')
        if not indexes:
            return outcome(MatchStatus.ERROR, 0, 'DOM changed while collecting match evidence.')
        if len(visible) > 1:
            return outcome(MatchStatus.AMBIGUOUS, len(visible), 'Multiple visible candidates match the alternatives.', indexes)
        selected = visible[0]
        if not selected.evaluate(_VISIBLE):
            selected = None
            return outcome(MatchStatus.ERROR, 0, 'Candidate changed during matching.')
        return outcome(MatchStatus.MATCHED, 1, 'Exactly one visible DOM candidate matched.', indexes)
    except Error:
        selected = None
        return outcome(MatchStatus.ERROR, 0, 'Browser matching failed; no element was bound.')
    finally:
        for handle in handles:
            if handle is not selected:
                try:
                    handle.dispose()
                except Error:
                    pass
