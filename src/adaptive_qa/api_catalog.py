"""Twenty controlled API behaviors, separate from the forty UI executors."""

from adaptive_qa.api_models import ApiCase, ApiRequest, HttpMethod, JsonCheck, JsonOperator as Op, JsonType as Kind
from adaptive_qa.models import TestCase, TestType


def _case(number, name, request, expected, status=200, checks=(), expect_json=True):
    definition = TestCase(f'API-{number:03}', name, TestType.API, ('api',),
        ('Use the explicitly configured controlled API', name, 'Check status and response assertions'),
        expected, changes_data=request.method not in (HttpMethod.GET, HttpMethod.HEAD))
    return ApiCase(definition, request, status, checks, expect_json)


API_CASES = (
    _case(1, 'Health reports readiness', ApiRequest('/api/health'), 'HTTP 200 with ready=true.',
          checks=(JsonCheck(('ready',), Op.EQUALS, True),)),
    _case(2, 'Catalog returns structured items', ApiRequest('/api/items'), 'Two typed items with integer IDs and numeric prices.',
          checks=(JsonCheck(('items',), Op.LENGTH, 2), JsonCheck(('items', 0, 'id'), Op.TYPE, Kind.INTEGER),
                  JsonCheck(('items', 0, 'price'), Op.TYPE, Kind.NUMBER))),
    _case(3, 'Known item returns its identity', ApiRequest('/api/items/1'), 'Item 1 is Notebook with price 10.',
          checks=(JsonCheck(('id',), Op.EQUALS, 1), JsonCheck(('name',), Op.EQUALS, 'Notebook'),
                  JsonCheck(('price',), Op.EQUALS, 10))),
    _case(4, 'Missing item returns not found', ApiRequest('/api/items/999'), 'HTTP 404 with item_not_found.', 404,
          (JsonCheck(('error',), Op.EQUALS, 'item_not_found'),)),
    _case(5, 'Search returns matching items', ApiRequest('/api/search', query=(('q', 'notebook'),)), 'One Notebook match.',
          checks=(JsonCheck(('items',), Op.LENGTH, 1), JsonCheck(('items', 0, 'name'), Op.EQUALS, 'Notebook'))),
    _case(6, 'Unmatched search returns an empty list', ApiRequest('/api/search', query=(('q', 'no-match'),)),
          'An empty items array and count zero.', checks=(JsonCheck(('items',), Op.LENGTH, 0), JsonCheck(('count',), Op.EQUALS, 0))),
    _case(7, 'Missing search query is rejected', ApiRequest('/api/search'), 'HTTP 400 with query_required.', 400,
          (JsonCheck(('error',), Op.EQUALS, 'query_required'),)),
    _case(8, 'Excessive query length is rejected', ApiRequest('/api/search', query=(('q', 'x' * 65),)),
          'HTTP 422 with query_too_long.', 422, (JsonCheck(('error',), Op.EQUALS, 'query_too_long'),)),
    _case(9, 'Anonymous private access is rejected', ApiRequest('/api/private'), 'HTTP 401 with authentication_required.', 401,
          (JsonCheck(('error',), Op.EQUALS, 'authentication_required'),)),
    _case(10, 'Configured bearer grants private access', ApiRequest('/api/private', use_authentication=True),
          'HTTP 200 with authenticated=true.', checks=(JsonCheck(('authenticated',), Op.EQUALS, True),)),
    _case(11, 'Insufficient scope is forbidden', ApiRequest('/api/admin', use_authentication=True),
          'HTTP 403 with insufficient_scope.', 403, (JsonCheck(('error',), Op.EQUALS, 'insufficient_scope'),)),
    _case(12, 'HEAD succeeds without body assertions', ApiRequest('/api/health', HttpMethod.HEAD),
          'HTTP 200; HEAD requires no JSON body.', expect_json=False),
    _case(13, 'Unsupported method is reported by the API', ApiRequest('/api/echo'), 'HTTP 405 with method_not_allowed.', 405,
          (JsonCheck(('error',), Op.EQUALS, 'method_not_allowed'),)),
    _case(14, 'Valid echo request is accepted', ApiRequest('/api/echo', HttpMethod.POST, body_json='{"name":"sample"}'),
          'HTTP 201 echoes the configured name and accepted=true.', 201,
          (JsonCheck(('name',), Op.EQUALS, 'sample'), JsonCheck(('accepted',), Op.EQUALS, True))),
    _case(15, 'Missing required payload field is rejected', ApiRequest('/api/echo', HttpMethod.POST, body_json='{}'),
          'HTTP 422 with invalid_name.', 422, (JsonCheck(('error',), Op.EQUALS, 'invalid_name'),)),
    _case(16, 'Oversized payload field is rejected', ApiRequest('/api/echo', HttpMethod.POST, body_json='{"name":"xxxxxxxxxxxxxxxxxxxxx"}'),
          'HTTP 422 with invalid_name.', 422, (JsonCheck(('error',), Op.EQUALS, 'invalid_name'),)),
    _case(17, 'Quantity below minimum is rejected', ApiRequest('/api/quantity', HttpMethod.POST, body_json='{"quantity":0}'),
          'HTTP 422 with invalid_quantity.', 422, (JsonCheck(('error',), Op.EQUALS, 'invalid_quantity'),)),
    _case(18, 'Valid quantity satisfies the business total', ApiRequest('/api/quantity', HttpMethod.POST, body_json='{"quantity":3}'),
          'Quantity three yields total 30.', checks=(JsonCheck(('total',), Op.EQUALS, 30), JsonCheck(('total',), Op.MINIMUM, 0))),
    _case(19, 'Quantity above maximum is rejected', ApiRequest('/api/quantity', HttpMethod.POST, body_json='{"quantity":11}'),
          'HTTP 422 with invalid_quantity.', 422, (JsonCheck(('error',), Op.EQUALS, 'invalid_quantity'),)),
    _case(20, 'Redirect response is observed without following', ApiRequest('/api/redirect', use_authentication=True),
          'HTTP 307 is returned without a second request or credential forwarding.', 307, expect_json=False),
)
API_BY_ID = {case.definition.case_id: case for case in API_CASES}
