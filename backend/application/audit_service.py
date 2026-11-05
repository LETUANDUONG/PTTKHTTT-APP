from backend.data_infrastructure.database.connection import get_db
from backend.data_infrastructure.database.connection import now


def audit(actor, action, record):
    get_db().execute('INSERT INTO audit(actor,action,record,created_at) VALUES(%s,%s,%s,%s)', (str(actor), action, str(record), now()))
