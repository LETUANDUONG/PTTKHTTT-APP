from backend.data_infrastructure.database.connection import lock_workflow
from .inventory_service import movement
from .order_records import history
from .order_records import order_detail
from .order_records import safe_order
from backend.data_infrastructure.database.connection import get_db
from backend.shared.validation import require


def transition(order_id, status, actor):
    db = get_db()
    o = order_detail(order_id)
    transitions = {'confirmed': 'picking', 'picking': 'packed', 'packed': 'shipped', 'shipped': 'delivered'}
    require(transitions.get(o['status']) == status, 'Không thể chuyển trạng thái đơn hàng theo thứ tự này.', 409)
    if status == 'shipped':
        for line in o['items']:
            db.execute('UPDATE products SET stock=stock-%s,reserved=reserved-%s WHERE id=%s', (line['quantity'], line['quantity'], line['product_id']))
            movement(line['product_id'], -line['quantity'], 'dispatch', actor, order_id)
    if status == 'delivered' and o['payment']['method'] == 'cod':
        db.execute("UPDATE payments SET status='collected' WHERE order_id=%s", (order_id,))
    db.execute('UPDATE orders SET status=%s WHERE id=%s', (status, order_id))
    history(order_id, status, actor)


def fulfil(oid, *, data, user):
    status = data.get('status')
    require(status in ['picking', 'packed', 'shipped', 'delivered'], 'Trạng thái không hợp lệ.')
    db = get_db()
    lock_workflow()
    transition(oid, status, user['id'])
    db.commit()
    return safe_order(oid, user=user)
