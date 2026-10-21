"""Fifteen distinct read-only behaviors against the controlled SQLite fixture."""

from adaptive_qa.database_models import DatabaseCase, DatabaseCheck, DatabaseOperator, QueryTemplate
from adaptive_qa.models import TestCase, TestType


def _case(number, name, sql, expected, parameters=(), *, count=False):
    definition = TestCase(f'DB-{number:03}', name, TestType.DATABASE, ('database',),
                          ('Execute the configured parameterized query against the prepared fixture.',),
                          name + ' satisfies its explicit assertion.')
    template = QueryTemplate('local-database', f'query_{number:03}', sql,
                             tuple(key for key, _ in parameters))
    check = DatabaseCheck(DatabaseOperator.ROW_COUNT if count else DatabaseOperator.CELL_EQUALS, expected)
    return DatabaseCase(definition, template, parameters, (check,))


DATABASE_CASES = (
    _case(1, 'Product primary key lookup', 'SELECT name FROM products WHERE id=:id', 'Notebook', (('id', 1),)),
    _case(2, 'Unknown product returns no rows', 'SELECT id FROM products WHERE id=:id', 0, (('id', 999),), count=True),
    _case(3, 'Catalog contains three products', 'SELECT id FROM products', 3, count=True),
    _case(4, 'Stored product price matches', 'SELECT price FROM products WHERE id=:id', 10, (('id', 1),)),
    _case(5, 'Out of stock product remains identifiable', 'SELECT name FROM products WHERE stock=0', 'Pencil'),
    _case(6, 'Available stock excludes unavailable products', 'SELECT id FROM products WHERE stock>0', 2, count=True),
    _case(7, 'Unicode product lookup', 'SELECT id FROM products WHERE name=:name', 3, (('name', 'Çanta'),)),
    _case(8, 'Order belongs to its customer', 'SELECT customer FROM orders WHERE id=:id', 'demo-user', (('id', 1),)),
    _case(9, 'Paid order status is persisted', 'SELECT status FROM orders WHERE id=:id', 'paid', (('id', 1),)),
    _case(10, 'Customer filter isolates orders', 'SELECT id FROM orders WHERE customer=:customer', 1,
          (('customer', 'demo-user'),), count=True),
    _case(11, 'Optional order note preserves null', 'SELECT note FROM orders WHERE id=:id', None, (('id', 1),)),
    _case(12, 'Order line quantities aggregate', 'SELECT sum(quantity) FROM order_items WHERE order_id=:id', 5, (('id', 1),)),
    _case(13, 'Order total follows stored line prices',
          'SELECT sum(quantity*unit_price) FROM order_items WHERE order_id=:id', 26, (('id', 1),)),
    _case(14, 'Order lines reference existing products',
          'SELECT i.product_id FROM order_items i LEFT JOIN products p ON p.id=i.product_id WHERE p.id IS NULL',
          0, count=True),
    _case(15, 'SQL-like customer input remains literal', 'SELECT id FROM orders WHERE customer=:customer', 0,
          (('customer', "demo-user' OR 1=1 --"),), count=True),
)

DATABASE_BY_ID = {case.definition.case_id: case for case in DATABASE_CASES}
