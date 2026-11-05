from backend.data_infrastructure.database.connection import get_db, now, one, rows
from backend.shared.validation import require
from .audit_service import audit


def history(order_id, status, actor):
    db = get_db()
    db.execute('INSERT INTO order_history(order_id,status,actor,created_at) VALUES(%s,%s,%s,%s)', (order_id, status, str(actor), now()))
    db.execute('INSERT INTO notifications(user_id,message,created_at) SELECT user_id,%s,%s FROM orders WHERE id=%s', (f'Đơn HOODOO-{order_id:05d}: {status}', now(), order_id))
    audit(actor, 'order.' + status, order_id)


def order_detail(order_id):
    o = one('SELECT * FROM orders WHERE id=%s', (order_id,))
    require(o, 'Không tìm thấy đơn hàng.', 404)
    o['items'] = rows('SELECT * FROM order_items WHERE order_id=%s', (order_id,))
    o['payment'] = one('SELECT * FROM payments WHERE order_id=%s', (order_id,))
    o['history'] = rows('SELECT * FROM order_history WHERE order_id=%s ORDER BY id', (order_id,))
    o['shipment'] = one('SELECT * FROM shipments WHERE order_id=%s', (order_id,))
    o['tracking'] = rows('SELECT * FROM tracking_events WHERE order_id=%s ORDER BY created_at,event_id', (order_id,))
    return o


def own_order(oid, *, user):
    o = one('SELECT * FROM orders WHERE id=%s AND user_id=%s', (oid, user['id']))
    require(o, 'Không tìm thấy đơn hàng.', 404)
    return o


def safe_order(oid, *, user):
    o = order_detail(oid)
    if user['role'] == 'warehouse':
        for key in ['recipient', 'phone', 'address', 'user_id', 'idem_key', 'request_hash']:
            o.pop(key, None)
    return o
