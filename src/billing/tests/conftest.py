from models import core

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session
from sqlalchemy.orm import sessionmaker
from plumbum import local
from cachetools import func

func.ttl_cache = lambda *_, **__: lambda f: f


from main import app  # noqa
from models.settings import DATABASES, TEST_DATABASE_URL  # noqa
from settings.core import ROOT  # noqa
from views import router  # noqa
from dependencies import static_files  # noqa



import misc, services, views, dependencies  # noqa


test_engine = create_engine(DATABASES['test']['url'])
test_session = sessionmaker(test_engine, expire_on_commit=False)
test_app = FastAPI()
test_app.include_router(router)
test_app.mount("/static", static_files, name="static")
test_client = TestClient(test_app)


misc.main_session = core.session = services.session =\
    dependencies.session = views.db =\
        core.serializable_session = services.serializable_session =\
            test_session


@pytest.fixture(scope='function')
def client():
    return test_client


@pytest.fixture(scope='function')
def session():
    yield test_session()


def migrate():
    alembic = local['alembic']
    with local.cwd(ROOT / 'models'):
        with local.env(DATABASE_URL=TEST_DATABASE_URL):
            code, err, out = alembic.run(('upgrade', 'head'))
            if code != 0:
                raise Exception('failed to run migrations')


def populate(session):
    from cryptography.fernet import Fernet

    from models.wallets import Currency
    from models.transactions import PaymentSystem
    from models.choices import PaymentSystemType

    session.add(Currency(code='uah'))
    session.add(Currency(code='usd'))
    session.add(Currency(code='eur'))
    session.add(Currency(code='gbp'))

    session.add(PaymentSystem(
        name='test',
        system_type=PaymentSystemType.visa,
        decryption_key=Fernet.generate_key().decode()
    ))
    session.commit()


@pytest.fixture(scope='session', autouse=True)
def database():
    with Session(create_engine(DATABASES['sync']['url'])) as session:
        session.connection().connection.set_isolation_level(0)
        session.execute('DROP DATABASE IF EXISTS test;')
        session.execute('CREATE DATABASE test;')
        session.connection().connection.set_isolation_level(1)
        migrate()

    with Session(test_engine) as session:
        populate(session)

    yield

    test_engine.dispose()
