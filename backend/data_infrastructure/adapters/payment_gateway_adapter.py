"""Demo gateway boundary; produces no external charge."""


def initial_payment(order_id,method,amount):
    return (order_id,method,'awaiting_collection' if method=='cod' else 'pending',f'HOODOO-PAY-{order_id}',amount)
