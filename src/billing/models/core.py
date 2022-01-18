from sqlmodel import create_engine
from sqlalchemy.orm import sessionmaker

from .settings import DATABASES


engine = create_engine(DATABASES['sync']['url'])
serializable_engine = engine.execution_options(isolation_level="SERIALIZABLE")

session = sessionmaker(engine, expire_on_commit=False)
serializable_session = sessionmaker(serializable_engine, expire_on_commit=False)
