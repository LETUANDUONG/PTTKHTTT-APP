"""Archive only original demo catalogue entries and import the snapshot atomically."""
from backend.data_infrastructure.database.connection import connect
from backend.data_infrastructure.database.adcbook import seed_adcbook

MOCK_NAMES=(
    'Bút gel Thiên Long FlexOffice 0.5mm','Sổ tay lò xo Pastel A5 120 trang',
    'Giấy in Double A A4 80gsm','Bộ thước học sinh 4 món','Bìa còng văn phòng A4 7cm',
    'Bút chì màu Colokit 24 màu','Hộp 12 bút gel xanh 0.5mm','Tập học sinh 96 trang ô ly',
    'Kéo thủ công an toàn 135mm','Băng keo giấy trang trí Pastel',
    'Kẹp giấy màu hộp 50 chiếc','Màu nước sáng tạo 12 màu',
)


def import_snapshot():
    with connect() as db:
        db.execute('SELECT pg_advisory_xact_lock(726031)')
        db.execute('UPDATE products SET published=0 WHERE id BETWEEN 1 AND 12 AND name=ANY(%s)',(list(MOCK_NAMES),))
        seed_adcbook(db)
        return db.execute("SELECT count(*) AS count FROM products WHERE attributes::jsonb ? 'source_id' AND published=1").fetchone()['count']


if __name__=='__main__':
    print('Imported visible ADCBook products:',import_snapshot())
