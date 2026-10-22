"""Stateless read-only contracts for contrasting generic/account/commerce APIs."""


def extended_get(path, query, items):
    if path == '/api/page':
        offset, limit = query.get('offset', ['0'])[0], query.get('limit', ['10'])[0]
        if (not offset.isascii() or not limit.isascii() or not offset.isdigit() or not limit.isdigit()
                or len(offset) > 4 or len(limit) > 2 or not 0 <= int(offset) <= 1000 or not 1 <= int(limit) <= 20):
            return 400, {'error': 'invalid_pagination'}
        offset, limit = int(offset), int(limit)
        return 200, {'items': items[offset:offset + limit], 'total': len(items),
                     'next_offset': offset + limit if offset + limit < len(items) else None}
    if path == '/api/sorted':
        return 200, {'items': sorted(items, key=lambda item: item['price'])}
    if path == '/api/categories':
        return 200, {'categories': [{'id': 'paper', 'name': 'Paper'}, {'id': 'writing', 'name': 'Writing'}]}
    if path == '/api/filter':
        tagged = [dict(item, category='paper' if item['id'] == 1 else 'writing') for item in items]
        return 200, {'items': [item for item in tagged if item['category'] == query.get('category', [''])[0]]}
    if path in ('/api/stock/1', '/api/stock/2'):
        quantity = 8 if path.endswith('/1') else 0
        return 200, {'available': quantity > 0, 'quantity': quantity}
    if path == '/api/cart/empty':
        return 200, {'items': [], 'total': 0, 'checkout_enabled': False}
    if path == '/api/cart/demo':
        price, quantity = items[0]['price'], 2
        return 200, {'items': [{'id': 1, 'quantity': quantity, 'unit_price': price, 'line_total': price * quantity}],
                     'subtotal': price * quantity}
    if path == '/api/discount':
        subtotal = items[0]['price'] * 2
        discount = subtotal * 10 // 100
        return 200, {'subtotal': subtotal, 'discount': discount, 'payable': subtotal - discount}
    if path == '/api/shipping':
        region = query.get('region', [''])[0]
        if region not in ('TR', 'EU'):
            return 422, {'error': 'unsupported_region'}
        return 200, {'region': region, 'amount': 5 if region == 'TR' else 15, 'currency': 'TRY'}
    if path == '/api/validation':
        email = query.get('email', [''])[0]
        if '@' not in email or email.startswith('@') or email.endswith('@'):
            return 422, {'errors': [{'field': 'email', 'code': 'invalid_email'}]}
        return 200, {'valid': True}
    return None
