"""Fetch a bounded, attributable snapshot of 200 public ADCBook products."""
import io, json, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'frontend/public/assets/adcbook'
DATA = ROOT / 'data/adcbook.json'
GROUPS = [('but-viet',1,34),('so-cac-loai',2,34),('giay-in',3,20),('dung-cu-hoc-sinh',4,40),('van-phong-pham',5,32),('dung-cu-ve',6,40)]
HEADERS = {'User-Agent':'Hoodoo educational catalogue/1.0'}

def fetch(url):
    with urlopen(Request(url,headers=HEADERS),timeout=45) as r:
        return r.read(8*1024*1024+1)

def download(item):
    product,category = item
    url=product['featured_image']
    if urlparse(url).hostname != 'bizweb.dktcdn.net': return None
    try:
        raw=fetch(url)
        if len(raw)>8*1024*1024: return None
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in ('JPEG','PNG','WEBP') or im.width*im.height>16000000: return None
            im.verify()
            ext={'JPEG':'jpg','PNG':'png','WEBP':'webp'}[im.format]
        name=str(product['id'])+'.'+ext
        v=product['variants'][0]
        qty=v.get('inventory_quantity')
        stock=max(0,int(qty)) if v.get('available') and isinstance(qty,(int,float)) else 0
        return ({'source_id':product['id'],'source_url':'https://adcbook.net.vn'+product['url'].split('?')[0], 'category_id':category,'name':product['name'], 'brand':product.get('vendor') or 'ADCBook', 'price':int(v['price']), 'selling_unit':v.get('unit') or 'Sản phẩm','stock':stock,'image':'/assets/adcbook/'+name}, name, raw)
    except (OSError,ValueError,UnidentifiedImageError): return None

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    selected=[]
    seen=set()
    for slug,category,quota in GROUPS:
        url='https://adcbook.net.vn/collections/'+slug+'/products.json?limit=250&page=1'
        products=json.loads(fetch(url))['products']
        candidates=[(p,category) for p in products if p.get('id') not in seen and len(p.get('variants',[]))==1 and p.get('featured_image') and p.get('name') and len(p['name'])<=180 and p['variants'][0].get('price') and 0 < p['variants'][0]['price'] <= 100000000]
        candidates.sort(key=lambda pair: not pair[0].get('available'))
        with ThreadPoolExecutor(max_workers=4) as pool:
            for result in pool.map(download,candidates[:quota+8]):
                if result and result[0]['source_id'] not in seen:
                    product,name,raw=result
                    (OUT/name).write_bytes(raw)
                    selected.append(product);seen.add(product['source_id'])
                    if sum(x['category_id']==category for x in selected)>=quota: break
        print(slug,sum(x['category_id']==category for x in selected),flush=True)
        time.sleep(1)
    if len(selected)!=200: raise RuntimeError(f'Expected 200 complete products, received {len(selected)}')
    DATA.parent.mkdir(exist_ok=True)
    DATA.write_text(json.dumps({'source':'https://adcbook.net.vn/','fetched_at':datetime.now(timezone.utc).isoformat(),'products':selected},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Saved',len(selected),'products;',sum(p['stock']>0 for p in selected),'in stock',flush=True)

if __name__=='__main__': main()
