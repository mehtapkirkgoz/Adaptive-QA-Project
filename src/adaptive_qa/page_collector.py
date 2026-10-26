"""Read bounded structural snapshots from an already guarded browser page."""

from playwright.sync_api import Page

from adaptive_qa.discovery import CommerceSnapshot, FieldSnapshot, FormSnapshot, LinkSnapshot, PageSnapshot


_COLLECT = r"""() => {
    let complete = true;
    const text = value => {
        const result = (value || '').replace(/\s+/g, ' ').trim();
        if (result.length > 160) complete = false;
        return result.slice(0, 160);
    };
    const visible = element => {
        const style = getComputedStyle(element);
        return !element.closest('[hidden], [inert], [aria-hidden="true"]') &&
            style.visibility !== 'hidden' && style.visibility !== 'collapse' &&
            element.getClientRects().length > 0;
    };
    const bounded = (items, limit) => {
        if (items.length > limit) complete = false;
        return Array.from(items).slice(0, limit);
    };
    const safeUrl = raw => {
        try {
            const url = new URL(raw, location.href);
            if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password)
                return null;
            url.search = ''; url.hash = '';
            if (url.href.length > 2048) { complete = false; return null; }
            return url.href;
        } catch { return null; }
    };
    const numberBound = (el,attribute) => {
        if (el.tagName!=='INPUT' || el.type!=='number' || el.disabled || el.readOnly) return false;
        const raw=el.getAttribute(attribute);
        if (!raw || !/^-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(raw)) return false;
        const value=Number(raw);
        return Number.isFinite(value) && Math.abs(value)<=1e12;
    };
    const forms = bounded(document.forms, 50).filter(visible).map(form => {
        const controls = bounded(form.elements, 100).filter(visible);
        return {
            form_id: text(form.id), role: text(form.getAttribute('role')),
            fields: controls.filter(el => ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)
                && !['submit', 'button', 'reset', 'image', 'hidden'].includes(el.type)).map(el => ({
                    input_type: text(el.type || el.tagName.toLowerCase()),
                    label: text(el.getAttribute('aria-label') ||
                        Array.from(el.labels || []).map(label => label.textContent).join(' ')),
                    autocomplete: text(el.getAttribute('autocomplete')),
                    native_minimum: numberBound(el,'min'),native_maximum: numberBound(el,'max'),
                })),
            buttons: controls.filter(el => el.tagName === 'BUTTON' ||
                (el.tagName === 'INPUT' && ['submit', 'button', 'image'].includes(el.type)))
                .map(el => text(el.getAttribute('aria-label') ||
                    (el.tagName === 'BUTTON' ? el.textContent : el.getAttribute('alt')))),
        };
    });
    const links = bounded(document.querySelectorAll('a[href]'), 200).filter(visible)
        .map(el => ({text: text(el.getAttribute('aria-label') || el.textContent),
                     href: safeUrl(el.getAttribute('href'))})).filter(el => el.href);
    const normalize = value => text(value).toLocaleLowerCase('en').normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '').replace(/ı/g, 'i').replace(/\s+/g, ' ').trim();
    const cartNames = ['cart', 'shopping cart', 'basket', 'sepet', 'sepetim', 'alisveris sepeti'];
    const emptyNames = ['your cart is empty', 'your basket is empty', 'cart is empty',
        'sepetiniz bos', 'sepetiniz bos.'];
    const actions = (region, product = false) => bounded(region.querySelectorAll('button, input[type="submit"], [role="button"]'), 100)
        .filter(el => visible(el) && (!product || el.closest('[itemscope]') === region))
        .map(el => text(el.getAttribute('aria-label') ||
            (el.tagName === 'INPUT' ? '' : el.textContent)));
    const commerce = [];
    for (const region of bounded(document.querySelectorAll('[itemscope][itemtype]'), 100).filter(visible)) {
        if (!region.getAttribute('itemtype').split(/\s+/).some(type =>
            ['https://schema.org/Product', 'http://schema.org/Product'].includes(type))) continue;
        const property = name => bounded(region.querySelectorAll('[itemprop]'), 100).filter(el =>
            visible(el) && el.getAttribute('itemprop').split(/\s+/).includes(name) &&
            el.closest('[itemscope]') === region);
        commerce.push({kind: 'product', name: text(property('name')[0]?.textContent),
            has_price: property('price').some(el => /\d/.test(el.textContent)),
            has_currency: property('priceCurrency').some(el => /^[A-Z]{3}$/.test(text(el.textContent))),
            actions: actions(region, true)});
    }
    for (const region of bounded(document.querySelectorAll('main[aria-label], form[aria-label], [role="region"][aria-label]'), 100)
        .filter(visible)) {
        const name = text(region.getAttribute('aria-label'));
        if (!cartNames.includes(normalize(name))) continue;
        const items = bounded(region.querySelectorAll('[itemprop~="itemListElement"]'), 100).filter(visible);
        const quantities = bounded(region.querySelectorAll('input[type="number"]'), 100).filter(visible);
        const statuses = bounded(region.querySelectorAll('[role="status"], p'), 100).filter(visible);
        commerce.push({kind: 'cart', name, has_items: items.length > 0,
            has_quantity: quantities.some(el => ['quantity', 'adet', 'miktar'].includes(normalize(el.getAttribute('aria-label')))),
            empty: statuses.some(el => emptyNames.includes(normalize(el.textContent))), actions: actions(region)});
    }
    // Embedded documents, custom elements, and shadow trees need separate coverage.
    const elements = document.getElementsByTagName('*');
    for (const el of bounded(elements, 5000)) {
        if (el.shadowRoot || el.localName.includes('-') ||
            ['IFRAME', 'FRAME', 'OBJECT', 'EMBED'].includes(el.tagName) ||
            (['form', 'search', 'button'].includes(el.getAttribute('role')) && !el.closest('form')) ||
            (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(el.tagName) && !el.form))
            complete = false;
    }
    return {url: safeUrl(location.href), forms, links, commerce, collection_complete: complete};
}"""


def collect_page_snapshot(page: Page) -> PageSnapshot:
    """Read current light DOM without navigating, clicking, or reading input values.

    The caller owns navigation policy and total execution deadlines. Collection
    failures propagate; callers must not turn them into evidence of absence.
    URLs omit query strings and fragments. Visible labels remain untrusted text.
    """
    data = page.evaluate(_COLLECT)
    forms = tuple(FormSnapshot(
        form_id=form['form_id'], role=form['role'],
        fields=tuple(FieldSnapshot(**item) for item in form['fields']),
        buttons=tuple(form['buttons']),
    ) for form in data['forms'])
    return PageSnapshot(data['url'], forms,
                        tuple(LinkSnapshot(**item) for item in data['links']),
                        data['collection_complete'],
                        tuple(CommerceSnapshot(**{**item, 'actions': tuple(item['actions'])})
                              for item in data.get('commerce', [])))
