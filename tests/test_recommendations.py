from conftest import call, sign_in

from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.indexes.recommendation_index import _tokens, recommend


def item(pid, category=1):
    return {'id': pid, 'category_id': category, 'name': f'Sản phẩm {pid}',
            'brand': 'Hoodoo', 'attributes': {}, 'available': 10}


def test_hybrid_ranker_learns_from_co_purchase():
    products = [item(pid) for pid in range(1, 6)]
    profiles = {1: {1: 3, 2: 3}, 2: {1: 3, 2: 3},
                3: {1: 3, 3: 3}, 4: {1: 3}}
    labels = {1: {1, 2}, 2: {1, 2}, 3: {1, 3}}

    results, mode = recommend(products, profiles, labels, user_id=4, limit=4)
    ids = [p['id'] for p in results]
    assert mode == 'learned'
    assert ids.index(2) < ids.index(3)
    assert 1 not in ids


def test_content_and_cold_start_fallback():
    products = [item(1, 1), item(2, 1), item(3, 2)]
    results, mode = recommend(products, {}, {}, context_id=1)
    assert mode == 'fallback'
    assert [p['id'] for p in results] == [2, 3]


def test_import_metadata_does_not_affect_content_features():
    product = item(1)
    product['attributes'] = {'source_id': '85359253', 'nguồn': 'https://example.test/abc', 'màu': 'xanh'}
    tokens = _tokens(product)
    assert 'mau' in tokens and 'xanh' in tokens
    assert '85359253' not in tokens and 'https' not in tokens


def test_recommendation_api_filters_unavailable_and_own_cart(app, client):
    with app.app_context():
        db = get_db()
        db.execute('UPDATE products SET stock=0 WHERE id=2')
        db.execute('UPDATE products SET published=0 WHERE id=7')
        db.commit()

    assert call(client, 'POST', '/cart/items', {'product_id': 1, 'quantity': 1}).status_code == 200
    response = client.get('/api/recommendations?limit=4&product_id=1')
    assert response.status_code == 200, response.json
    assert response.json['method'] == 'hybrid'
    assert response.json['ranker'] == 'fallback'
    assert len(response.json['items']) == 4
    assert not {1, 2, 7}.intersection(p['id'] for p in response.json['items'])
    assert client.get('/api/recommendations?limit=13').status_code == 400
    assert client.get('/api/recommendations?product_id=oops').status_code == 400
    assert client.get('/api/recommendations?product_id=7').status_code == 404


def test_low_rating_is_not_a_positive_signal(app, client):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO reviews(user_id,product_id,rating,comment,created_at) VALUES(1,1,1,'Không phù hợp','2026-01-01')")
        db.commit()
    sign_in(client)
    response = client.get('/api/recommendations?limit=12')
    assert response.status_code == 200
    assert 1 not in [p['id'] for p in response.json['items']]


def test_api_uses_learned_ranker_after_customer_interactions(app, client):
    with app.app_context():
        db = get_db()
        for user_id, products in ((1, (1, 7)), (2, (1, 7)), (3, (1, 4))):
            for product_id in products:
                db.execute('''INSERT INTO reviews(user_id,product_id,rating,comment,created_at)
                              VALUES(%s,%s,5,'Tốt','2026-01-01')''', (user_id, product_id))
        db.commit()
    response = client.get('/api/recommendations?limit=4&product_id=1')
    assert response.status_code == 200
    assert response.json['ranker'] == 'learned'
    assert all(p['id'] != 1 for p in response.json['items'])
