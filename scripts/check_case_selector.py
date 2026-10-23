"""Browser assertions shared by personal and organization acceptance flows."""

from playwright.sync_api import expect


def verify_case_selector(panel, prefix):
    selector = panel.get_by_label('Test case selection', exact=True)
    search = selector.get_by_role('searchbox', name='Search eligible tests', exact=True)
    options = selector.get_by_role('group', name='Eligible tests', exact=True)
    boxes = options.get_by_role('checkbox')
    assert boxes.count() > 10
    assert options.locator('small').count() == boxes.count()
    assert options.evaluate('(element) => element.clientHeight') <= 320
    for index in range(10):
        boxes.nth(index).check()
    expect(boxes.nth(10)).to_be_disabled()
    expect(selector.get_by_role('status')).to_contain_text('10 of 10 selected')
    selector.get_by_role('button', name='Clear selection', exact=True).click()
    expect(boxes.nth(10)).to_be_enabled()
    # Search by the actual discovered name as well as by stable identifier.
    name = options.locator('small').first.inner_text()
    search.fill(name)
    expect(options.locator('small').first).to_have_text(name)
    search.fill('LOGIN-001')
    expect(boxes).to_have_count(1)
    panel.get_by_label(f'{prefix} LOGIN-001', exact=True).check()
    search.fill('SEARCH-001')
    panel.get_by_label(f'{prefix} SEARCH-001', exact=True).check()
    expect(selector.get_by_role('status')).to_contain_text('2 of 10 selected')
    search.fill('no-matching-case-identifier')
    expect(boxes).to_have_count(0)
    expect(selector.get_by_text('No eligible tests match this search.', exact=True)).to_be_visible()
    expect(selector.get_by_role('status')).to_contain_text('2 of 10 selected')
    search.fill('')
    expect(panel.get_by_label(f'{prefix} LOGIN-001', exact=True)).to_be_checked()
    expect(panel.get_by_label(f'{prefix} SEARCH-001', exact=True)).to_be_checked()
    selector.get_by_role('button', name='Clear selection', exact=True).click()
    expect(selector.get_by_role('status')).to_contain_text('0 of 10 selected')
