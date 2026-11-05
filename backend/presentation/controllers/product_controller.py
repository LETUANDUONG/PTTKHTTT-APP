from ..http import owner, respond
from backend.application import catalogue_service, recommendation_service
from backend.shared.validation import require
from flask import Blueprint, g, request
bp = Blueprint('product_controller', __name__)


@bp.get('/api/categories')
def categories():
    return respond(catalogue_service.categories())


@bp.get('/api/products/<int:pid>')
def detail(pid):
    return respond(catalogue_service.detail(pid))


@bp.get('/api/recommendations')
def recommendations():
    raw_limit = request.args.get('limit', '4')
    raw_product = request.args.get('product_id')
    require(raw_limit.isdigit() and 1 <= int(raw_limit) <= 12, 'Giới hạn gợi ý phải từ 1 đến 12.')
    require(raw_product is None or (raw_product.isdigit() and int(raw_product) > 0), 'Mã sản phẩm không hợp lệ.')
    return respond(recommendation_service.recommendations(
        user_id=g.user['id'] if g.user else None,
        cart_owner=owner(),
        product_id=int(raw_product) if raw_product is not None else None,
        limit=int(raw_limit),
    ))
