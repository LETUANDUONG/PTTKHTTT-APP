import sys
import os
import re
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app import create_app
from scripts.testing_database import temporary_database

marker=ROOT/'.test-runtime/e2e-database.txt'
if '--cleanup' in sys.argv:
    # Playwright force-kills the Windows webServer, so its finally block cannot run.
    if marker.exists():
        name=marker.read_text(encoding='utf-8')
        if not re.fullmatch(r'hoodoo_test_[0-9a-f]{32}',name):
            raise ValueError('Invalid E2E database marker')
        dsn=os.environ.get('TEST_DATABASE_URL',os.environ.get('DATABASE_URL',''))
        with psycopg.connect(dsn,autocommit=True) as db:
            db.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
        marker.unlink()
else:
    marker.parent.mkdir(exist_ok=True)
    try:
        with temporary_database() as dsn:
            marker.write_text(conninfo_to_dict(dsn)['dbname'],encoding='utf-8')
            app=create_app({'DATABASE':dsn,'SECRET_KEY':'e2e-only','DEMO_MODE':True})
            app.run(host='0.0.0.0',port=5099,debug=False)
    finally:
        marker.unlink(missing_ok=True)
