"""Build recommendation signals from real catalogue and customer activity."""
from collections import defaultdict
import math

from backend.data_infrastructure.database.connection import rows
from backend.data_infrastructure.indexes.recommendation_index import recommend
from backend.shared.validation import require

from .catalogue_service import published_products


def recommendations(*, user_id=None, cart_owner=None, product_id=None, limit=4):
    products = published_products()
    available_ids = {p['id'] for p in products}
    if product_id is not None:
        require(product_id in available_ids, 'Sản phẩm không còn được bán.', 404)

    profiles = defaultdict(dict)
    labels = defaultdict(set)
    purchases = rows('''SELECT o.user_id, i.product_id, SUM(i.quantity) AS quantity
                        FROM orders o JOIN order_items i ON i.order_id=o.id
                        WHERE o.status IN ('confirmed','picking','packed','shipped','delivered')
                        GROUP BY o.user_id, i.product_id''')
    for event in purchases:
        pid = event['product_id']
        if pid in available_ids:
            uid = event['user_id']
            profiles[uid][pid] = min(5, 2 + math.log1p(event['quantity']))
            labels[uid].add(pid)

    reviews = rows('SELECT user_id, product_id, rating FROM reviews')
    disliked = set()
    for event in reviews:
        uid, pid, rating = event['user_id'], event['product_id'], event['rating']
        if pid not in available_ids:
            continue
        if rating >= 4:
            profiles[uid][pid] = max(profiles[uid].get(pid, 0), rating - 1)
            labels[uid].add(pid)
        elif rating <= 2:
            profiles[uid].pop(pid, None)
            labels[uid].discard(pid)
            if uid == user_id:
                disliked.add(pid)

    if cart_owner:
        active_user = user_id if user_id is not None else cart_owner
        for item in rows('SELECT product_id, quantity FROM cart_items WHERE owner=%s', (cart_owner,)):
            if item['product_id'] in available_ids:
                pid = item['product_id']
                profiles[active_user][pid] = max(profiles[active_user].get(pid, 0), 0.75)

    active_user = user_id if user_id is not None else cart_owner
    items, ranker = recommend(products, profiles, labels, active_user, product_id, limit, disliked)
    return {'items': items, 'method': 'hybrid', 'ranker': ranker}
