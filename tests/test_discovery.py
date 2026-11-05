import io
import math
import wave
from pathlib import Path
from conftest import call
from backend.data_infrastructure.database.connection import get_db


def test_public_catalogue_combined_filters(client):
    result=client.get('/api/products?q=but&brand=Thiên+Long&category=1&attribute=màu:xanh&min_price=10000&max_price=15000').json
    assert [p['id'] for p in result['items']]==[1]
    assert client.get('/api/products?q=nonexistent').json['total']==0
    assert client.get('/api/products?page=2').json['page']==2
    prices=[p['price'] for p in client.get('/api/products?sort=price_asc').json['items']]
    assert prices==sorted(prices)
    assert client.get('/api/products?page=-1').status_code==400
    assert client.get('/api/products?min_price=oops').status_code==400
    assert client.get('/api/products?sort=unknown').status_code==400


def test_hidden_product_and_detail(app,client):
    with app.app_context():
        get_db().execute('UPDATE products SET published=0 WHERE id=1')
        get_db().commit()
    assert client.get('/api/products/1').status_code==404
    assert not any(p['id']==1 for p in client.get('/api/products?q=but').json['items'])
    p=client.get('/api/products/7').json
    assert p['selling_unit']=='Hộp' and p['pack_quantity']==12


def test_image_rank_validation_and_no_business_changes(app,client):
    token=client.get('/api/session').json['csrf_token']
    path=Path(__file__).resolve().parents[1]/'frontend/public/assets/pen-blue.png'
    with path.open('rb') as f:
        r=client.post('/api/search/image',data={'image':(f,'pen.png')},headers={'X-CSRF-Token':token})
    assert r.status_code==200,r.json
    assert r.json['items'][0]['id']==1
    assert 'CLIP' in r.json['method']
    assert r.json['items'][0]['similarity'] > 0.99
    with path.open('rb') as f:
        filtered=client.post('/api/search/image?category=2',data={'image':(f,'pen.png')},headers={'X-CSRF-Token':token})
    assert all(p['category_id']==2 for p in filtered.json['items'])
    r=client.post('/api/search/image',data={'image':(io.BytesIO(b'not an image'),'fake.png')},headers={'X-CSRF-Token':token})
    assert r.status_code==400
    r=client.post('/api/search/image',data={'image':(io.BytesIO(b'x'*(5*1024*1024+1)),'big.png')},headers={'X-CSRF-Token':token})
    assert r.status_code==413
    with app.app_context():
        assert get_db().execute('SELECT SUM(reserved) AS reserved FROM products').fetchone()['reserved']==0
        assert get_db().execute('SELECT count(*) AS count FROM orders').fetchone()['count']==0


def audio_upload(client, raw):
    token=client.get('/api/session').json['csrf_token']
    return client.post('/api/search/voice',data={'audio':(io.BytesIO(raw),'voice.wav')},headers={'X-CSRF-Token':token})


def wav(seconds, tone=False):
    import struct
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b''.join(struct.pack('<h',int(1000*math.sin(i/10)) if tone else 0) for i in range(int(seconds*16000))))
    return buffer.getvalue()


def test_voice_input_validation_and_csrf(client):
    assert client.post('/api/search/voice',data={}).status_code==403
    assert call(client,'POST','/search/voice',{}).status_code==400
    assert audio_upload(client,b'').status_code==400
    assert audio_upload(client,b'not audio').status_code==400
    assert audio_upload(client,b'x'*(5*1024*1024+1)).status_code==413
    assert audio_upload(client,wav(16)).status_code==413
    assert audio_upload(client,wav(.05)).status_code==400
    assert audio_upload(client,wav(1)).status_code==400


def test_real_whisper_vad_rejects_non_speech(client):
    # Real model/VAD, not a mocked transcription; a tone must never become a search.
    response=audio_upload(client,wav(1,tone=True))
    assert response.status_code==400,response.json


def test_clip_transformed_image_and_cache(client):
    from PIL import Image, ImageEnhance
    from backend.data_infrastructure.adapters.image_embedding_adapter import _cached_catalogue
    path=Path(__file__).resolve().parents[1]/'frontend/public/assets/pen-blue.png'
    with Image.open(path) as image:
        changed=ImageEnhance.Brightness(image.convert('RGB')).enhance(.8).rotate(12,fillcolor='white')
        buffer=io.BytesIO()
        changed.save(buffer,format='JPEG')
    token=client.get('/api/session').json['csrf_token']
    before=_cached_catalogue.cache_info().hits
    response=client.post('/api/search/image',data={'image':(io.BytesIO(buffer.getvalue()),'photo.jpg')},headers={'X-CSRF-Token':token})
    assert response.status_code==200,response.json
    assert response.json['items'][0]['id'] in (1,7)
    assert _cached_catalogue.cache_info().hits > before


def test_missing_clip_model_is_actionable(client,monkeypatch,tmp_path):
    from backend.data_infrastructure.adapters import image_embedding_adapter as adapter
    adapter._model.cache_clear()
    monkeypatch.setattr(adapter,'PROJECT_ROOT',tmp_path)
    image=io.BytesIO()
    from PIL import Image
    Image.new('RGB',(20,20),'white').save(image,format='PNG')
    token=client.get('/api/session').json['csrf_token']
    response=client.post('/api/search/image',data={'image':(io.BytesIO(image.getvalue()),'image.png')},headers={'X-CSRF-Token':token})
    assert response.status_code==503,response.json
    assert 'model' in response.json['error']
