import psycopg
import pytest
from test_orders import checkout
from backend.data_infrastructure.database.connection import connect, init_db


def test_durability_constraints_and_restart(app, client):
    oid = checkout(client, 'cod').json['id']
    dsn = app.config['DATABASE']
    with connect(dsn) as db:
        assert db.execute('SELECT reserved FROM products WHERE id=1').fetchone()['reserved'] == 2
        assert db.execute('SELECT status FROM orders WHERE id=%s', (oid,)).fetchone()['status'] == 'confirmed'
        with pytest.raises(psycopg.IntegrityError):
            with db.transaction():
                db.execute('UPDATE products SET stock=0 WHERE id=1')
        with pytest.raises(psycopg.IntegrityError):
            with db.transaction():
                db.execute("INSERT INTO cart_items VALUES('invalid-owner',99999,1)")
    init_db(dsn)
    with connect(dsn) as db:
        assert db.execute('SELECT COUNT(*) AS count FROM order_items').fetchone()['count'] == 1
        assert db.execute('SELECT COUNT(*) AS count FROM products').fetchone()['count'] == 12
        assert db.execute('SELECT reserved FROM products WHERE id=1').fetchone()['reserved'] == 2
