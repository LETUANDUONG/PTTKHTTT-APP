from backend.app import create_app
from backend.data_infrastructure.database.adcbook import DEMO_MIN_AVAILABLE, seed_adcbook, top_up_demo_stock
from backend.data_infrastructure.database.connection import get_db
from scripts.testing_database import temporary_database


def test_demo_top_up_is_audited_and_idempotent(app):
    with app.app_context():
        db = get_db()
        seed_adcbook(db)
        low_stock = db.execute("SELECT id FROM products WHERE attributes::jsonb ? 'source_id' AND stock=1 LIMIT 1").fetchone()['id']
        db.execute('UPDATE products SET reserved=1 WHERE id=%s', (low_stock,))
        expected = db.execute('''SELECT SUM(%s-(stock-reserved)) AS units
                                 FROM products WHERE published=1 AND attributes::jsonb ? 'source_id'
                                   AND stock-reserved < %s''',
                              (DEMO_MIN_AVAILABLE, DEMO_MIN_AVAILABLE)).fetchone()['units']

        changed, added = top_up_demo_stock(db)
        assert changed > 0 and added == expected
        assert db.execute('SELECT stock-reserved AS available FROM products WHERE id=%s',
                          (low_stock,)).fetchone()['available'] == DEMO_MIN_AVAILABLE
        assert db.execute("SELECT COUNT(*) AS count FROM inventory_movements WHERE actor='demo-stock'").fetchone()['count'] == changed
        assert db.execute("SELECT COUNT(*) AS count FROM audit WHERE action='inventory.demo_top_up'").fetchone()['count'] == 1
        assert top_up_demo_stock(db) == (0, 0)


def test_fresh_demo_database_starts_with_available_catalogue():
    with temporary_database() as dsn:
        app = create_app({'DATABASE': dsn, 'DEMO_MODE': True})
        with app.app_context():
            result = get_db().execute('''SELECT COUNT(*) AS count, MIN(stock-reserved) AS minimum
                                         FROM products WHERE published=1''').fetchone()
            assert result == {'count': 200, 'minimum': DEMO_MIN_AVAILABLE}
