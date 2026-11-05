from .catalogue_service import product
from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.database.connection import one
from backend.data_infrastructure.database.connection import rows
from backend.shared.validation import integer
from backend.shared.validation import require


def cart(owner):
    items = [product(p) for p in rows('SELECT p.*,c.quantity FROM cart_items c JOIN products p ON p.id=c.product_id WHERE owner=%s ORDER BY p.id', (owner,))]
    return {'items': items, 'subtotal': sum((p['price'] * p['quantity'] for p in items))}


def view_cart(*, owner):
    return cart(owner)


def add_cart(*, data, owner):
    d = data
    pid = integer(d.get('product_id'), 'Sản phẩm')
    quantity = integer(d.get('quantity'), 'Số lượng', 1, 999)
    require(one('SELECT id FROM products WHERE id=%s AND published=1', (pid,)), 'Sản phẩm không còn được bán.', 404)
    db = get_db()
    existing = one('SELECT quantity FROM cart_items WHERE owner=%s AND product_id=%s', (owner, pid))
    require(quantity + (existing['quantity'] if existing else 0) <= 999, 'Tối đa 999 đơn vị mỗi sản phẩm.')
    db.execute('INSERT INTO cart_items VALUES(%s,%s,%s) ON CONFLICT(owner,product_id) DO UPDATE SET quantity=cart_items.quantity+excluded.quantity', (owner, pid, quantity))
    db.commit()
    return cart(owner)


def update_cart(pid, *, data, owner):
    db = get_db()
    require(one('SELECT 1 FROM cart_items WHERE owner=%s AND product_id=%s', (owner, pid)), 'Không có sản phẩm này trong giỏ.', 404)
    quantity = integer(data.get('quantity'), 'Số lượng', 1, 999)
    db.execute('UPDATE cart_items SET quantity=%s WHERE owner=%s AND product_id=%s', (quantity, owner, pid))
    db.commit()
    return cart(owner)


def remove_cart(pid, *, owner):
    db = get_db()
    require(one('SELECT 1 FROM cart_items WHERE owner=%s AND product_id=%s', (owner, pid)), 'Không có sản phẩm này trong giỏ.', 404)
    db.execute('DELETE FROM cart_items WHERE owner=%s AND product_id=%s', (owner, pid))
    db.commit()
    return cart(owner)
