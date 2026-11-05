"""Small-catalogue hybrid recommender with an implicit-feedback pairwise ranker."""
from collections import Counter, defaultdict
from functools import lru_cache
import math
import re
import unicodedata


FALLBACK_WEIGHTS = (0.35, 0.40, 0.15, 0.10)


def _tokens(product):
    def words(value):
        value = unicodedata.normalize('NFD', str(value).lower().replace('đ', 'd'))
        value = ''.join(c for c in value if unicodedata.category(c) != 'Mn')
        return re.findall(r'[a-z0-9]+', value)

    tokens = Counter({f"category:{product['category_id']}": 3})
    tokens.update(words(product['name']))
    tokens.update(words(product['brand']))
    tokens.update(words(product.get('description', '')))
    for key, value in product['attributes'].items():
        tokens.update(words(key))
        tokens.update(words(value))
    return tokens


def _content_vectors(products):
    documents = {p['id']: _tokens(p) for p in products}
    frequency = Counter(token for document in documents.values() for token in document)
    count = len(documents)
    vectors = {}
    for pid, document in documents.items():
        vector = {token: (1 + math.log(weight)) * (1 + math.log((count + 1) / (frequency[token] + 1)))
                  for token, weight in document.items()}
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1
        vectors[pid] = {token: value / norm for token, value in vector.items()}
    return vectors


def _cosine(left, right):
    return sum(weight * right.get(token, 0) for token, weight in left.items())


def _signals(products, profiles, user_id, context_id, vectors):
    categories = {product['id']: product['category_id'] for product in products}
    active = profiles.get(user_id, {}) if user_id is not None else {}
    seeds = dict(active)
    if context_id in vectors:
        seeds[context_id] = max(seeds.get(context_id, 0), 3)
    seed_total = sum(seeds.values()) or 1

    # Item-item collaborative cosine from distinct users; the target user's
    # own history is excluded so one user cannot manufacture a co-occurrence.
    users_by_item = defaultdict(dict)
    for uid, history in profiles.items():
        if uid == user_id:
            continue
        for pid, weight in history.items():
            users_by_item[pid][uid] = weight
    item_norm = {pid: math.sqrt(sum(w * w for w in users.values()))
                 for pid, users in users_by_item.items()}
    popularity = {pid: len(users) for pid, users in users_by_item.items()}
    max_popularity = max(popularity.values(), default=0) or 1

    features = {}
    for product in products:
        pid = product['id']
        content = sum(weight * _cosine(vectors[pid], vectors[seed])
                      for seed, weight in seeds.items() if seed in vectors) / seed_total
        collaborative = 0
        for seed, weight in seeds.items():
            left, right = users_by_item.get(pid, {}), users_by_item.get(seed, {})
            denominator = item_norm.get(pid, 0) * item_norm.get(seed, 0)
            if denominator:
                collaborative += weight * sum(value * right.get(uid, 0)
                                               for uid, value in left.items()) / denominator
        collaborative /= seed_total
        same_category = sum(weight for seed, weight in seeds.items()
                            if product['category_id'] == categories.get(seed)) / seed_total
        features[pid] = (min(1, collaborative), min(1, content),
                         popularity.get(pid, 0) / max_popularity, same_category)
    return features


@lru_cache(maxsize=16)
def _fit_pairwise(pairs):
    """Fit a regularized RankNet-style linear scorer on positive/negative pairs."""
    weights = list(FALLBACK_WEIGHTS)
    for epoch in range(60):
        rate = 0.16 / (1 + epoch * 0.04)
        for difference in pairs:
            margin = sum(a * b for a, b in zip(weights, difference))
            gradient = 1 / (1 + math.exp(max(-30, min(30, margin))))
            for index, delta in enumerate(difference):
                weights[index] += rate * (gradient * delta - 0.02 * weights[index])
    return tuple(weights)


def recommend(products, profiles, labels, user_id=None, context_id=None, limit=4, blocked=()):
    """Rank published in-stock products, with content/popularity cold-start fallback."""
    eligible = [p for p in products if p['available'] > 0]
    if not eligible:
        return [], 'fallback'
    vectors = _content_vectors(products)
    feature_rows = _signals(products, profiles, user_id, context_id, vectors)

    # Leave one observed purchase/review out of each training user's profile.
    # Other users remain available to collaborative filtering, while the held
    # item is never a seed for its own training example.
    pairs = []
    training_users = 0
    for uid, positives in sorted(labels.items()):
        history = profiles.get(uid, {})
        if len(history) < 2:
            continue
        training_users += 1
        for target in sorted(positives):
            if target not in vectors:
                continue
            reduced = {key: value for key, value in history.items() if key != target}
            training_profiles = {**profiles, uid: reduced}
            training = _signals(products, training_profiles, uid, None, vectors)
            negatives = [p['id'] for p in eligible if p['id'] not in history][:8]
            for negative in negatives:
                pairs.append(tuple(a - b for a, b in zip(training[target], training[negative])))
    weights = _fit_pairwise(tuple(pairs)) if len(pairs) >= 8 and training_users >= 2 else FALLBACK_WEIGHTS
    mode = 'learned' if weights is not FALLBACK_WEIGHTS else 'fallback'

    seen = set(profiles.get(user_id, {})) if user_id is not None else set()
    excluded = seen | set(blocked) | ({context_id} if context_id is not None else set())
    candidates = [p for p in eligible if p['id'] not in excluded]
    scored = sorted(candidates,
                    key=lambda p: (-sum(w * x for w, x in zip(weights, feature_rows[p['id']])), p['id']))
    return scored[:limit], mode
