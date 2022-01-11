from contextlib import contextmanager, asynccontextmanager

from sqlmodel import create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .accounts import *  # noqa
from .transactions import *  # noqa
from .wallets import *  # noqa

from settings.database import DATABASES


engine = create_engine(DATABASES['sync']['url'])
async_engine = create_async_engine(DATABASES['async']['url'])
async_session_maker = sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)


@contextmanager
def session():
    yield Session(engine)


@asynccontextmanager
async def async_session():
    yield async_session_maker()
