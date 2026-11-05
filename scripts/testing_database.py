"""Create an isolated PostgreSQL database and always remove only that database."""
import os
import uuid
from contextlib import contextmanager

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo


@contextmanager
def temporary_database():
    dsn = os.environ.get('TEST_DATABASE_URL', os.environ.get('DATABASE_URL', ''))
    name = 'hoodoo_test_' + uuid.uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:
            yield make_conninfo(dsn, dbname=name)
        finally:
            admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
