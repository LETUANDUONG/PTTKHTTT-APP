"""Import the checked-in ADCBook snapshot without changing existing orders."""
import json

from backend.data_infrastructure.database.connection import now
from backend.shared.paths import PROJECT_ROOT


DEMO_MIN_AVAILABLE = 20


def seed_adcbook(db, minimum_stock=0):
    snapshot=json.loads((PROJECT_ROOT/'data/adcbook.json').read_text(encoding='utf-8'))
    products=snapshot['products']
    if len(products)!=200 or len({p['source_id'] for p in products})!=200:
        raise ValueError('ADCBook snapshot must contain 200 unique products')
    for p in products:
        path=PROJECT_ROOT/'frontend/public'/p['image'].lstrip('/')
        if not path.is_file():
            raise ValueError(f"Missing catalogue image: {p['source_id']}")
        exists=db.execute("SELECT id FROM products WHERE attributes::jsonb->>'source_id'=%s",(str(p['source_id']),)).fetchone()
        if exists:
            continue
        attrs=json.dumps({'source_id':str(p['source_id']),'nguồn':p['source_url'],'cập nhật':snapshot['fetched_at']},ensure_ascii=False)
        description='Thông tin sản phẩm tham khảo từ ADCBook. Giá và tồn kho là dữ liệu tại thời điểm thu thập.'
        db.execute('INSERT INTO products(category_id,name,description,brand,price,selling_unit,pack_quantity,attributes,image,published,stock) VALUES(%s,%s,%s,%s,%s,%s,1,%s,%s,1,%s)',
                   (p['category_id'],p['name'],description,p['brand'],p['price'],p['selling_unit'],attrs,p['image'],max(p['stock'], minimum_stock)))


def top_up_demo_stock(db, minimum_available=DEMO_MIN_AVAILABLE):
    """Top up imported demo products once, preserving reservations and an audit trail."""
    db.execute('SELECT pg_advisory_xact_lock(726031)')
    targets = db.execute('''SELECT id, stock, reserved FROM products
                            WHERE published=1 AND attributes::jsonb ? 'source_id'
                              AND stock-reserved < %s FOR UPDATE''', (minimum_available,)).fetchall()
    timestamp = now()
    added = 0
    for item in targets:
        quantity = minimum_available - (item['stock'] - item['reserved'])
        db.execute('UPDATE products SET stock=stock+%s WHERE id=%s', (quantity, item['id']))
        db.execute('''INSERT INTO inventory_movements
                      (product_id,quantity,kind,reason,actor,created_at)
                      VALUES(%s,%s,'receipt',%s,'demo-stock',%s)''',
                   (item['id'], quantity, f'Demo stock: minimum {minimum_available} available', timestamp))
        added += quantity
    if targets:
        db.execute('INSERT INTO audit(actor,action,record,created_at) VALUES(%s,%s,%s,%s)',
                   ('demo-stock', 'inventory.demo_top_up', f'{len(targets)} products; {added} units', timestamp))
    return len(targets), added
