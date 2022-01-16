from contextlib import contextmanager, asynccontextmanager
from contextvars import ContextVar

from sqlmodel import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .settings import DATABASES


engine = create_engine(DATABASES['sync']['url'])
serializable_engine = engine.execution_options(isolation_level="SERIALIZABLE")

session_maker = sessionmaker(engine, expire_on_commit=False)
serializable_session_maker = sessionmaker(serializable_engine, expire_on_commit=False)

session_cv = ContextVar('session')
serializable_session_cv = ContextVar('serializable_session')


@contextmanager
def session():
    try:
        s = session_cv.get()
        yield s
    except LookupError:
        s = session_maker()
        with s:
            token = session_cv.set(s)
            yield s
        session_cv.reset(token)


@contextmanager
def serializable_session():
    try:
        s = serializable_session_cv.get()
        yield s
    except LookupError:
        s = serializable_session_maker()
        with s:
            token = serializable_session_cv.set(s)
            yield s
        serializable_session_cv.reset(token)
