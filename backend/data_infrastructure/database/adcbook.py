"""Import the checked-in ADCBook snapshot without changing existing orders."""
import json

from backend.shared.paths import PROJECT_ROOT


def seed_adcbook(db):
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
                   (p['category_id'],p['name'],description,p['brand'],p['price'],p['selling_unit'],attrs,p['image'],p['stock']))
