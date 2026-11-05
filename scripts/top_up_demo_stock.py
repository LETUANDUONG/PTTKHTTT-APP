"""Make the local ADCBook catalogue purchasable without changing the snapshot."""
import os

from backend.data_infrastructure.database.adcbook import top_up_demo_stock
from backend.data_infrastructure.database.connection import connect


def main():
    if os.environ.get('DEMO_MODE', '1') != '1':
        raise SystemExit('Demo stock top-up requires DEMO_MODE=1.')
    with connect() as db:
        changed, added = top_up_demo_stock(db)
    print(f'Demo stock updated: {changed} products, {added} units added.')


if __name__ == '__main__':
    main()
