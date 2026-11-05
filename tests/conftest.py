import pytest
from backend.app import create_app
from scripts.testing_database import temporary_database


@pytest.fixture
def app():
    with temporary_database() as dsn:
        yield create_app({'TESTING':True,'DATABASE':dsn,'SECRET_KEY':'testing','DEMO_MODE':True})


@pytest.fixture
def client(app):
    return app.test_client()


def call(c,method,path,data=None,headers=None,**kwargs):
    token=c.get('/api/session').json['csrf_token']
    return c.open('/api'+path,method=method,json=data,headers={'X-CSRF-Token':token,**(headers or {})},**kwargs)


def sign_in(c,role='customer'):
    r=call(c,'POST','/auth/login',{'email':role+'@hoodoo.local','password':'Hoodoo@12345'})
    assert r.status_code==200,r.json
    return r.json
