from typing import Union
from functools import wraps

from pydantic import BaseModel
from pydantic.main import ModelMetaclass
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from bcrypt import hashpw, gensalt

from models.core import session as main_session
from models.accounts import Staff, Merchant


class PaginatedMeta(type):
    __cache = {}

    def __getitem__(cls, key):
        if NewCls := cls.__cache.get(key):
            return NewCls

        class NewCls(BaseModel):
            data: list[key]
            itemsCount: int

            @classmethod
            def from_queryset(cls, queryset, offset, limit):
                data = queryset.offset(offset).limit(limit).all()
                return {'data': data, 'itemsCount': len(data)}

        cls.__cache[key] = NewCls
        return NewCls


class Paginated(metaclass=PaginatedMeta):
    pass


def get_or_create(model, session=None, defaults=None, **kwargs):
    if session is None:
        session = main_session()

    with session as s:
        try:
            instance = s.query(model).filter_by(**kwargs).one()
        except MultipleResultsFound as e:
            raise e
        except NoResultFound:
            instance = model(**(kwargs | defaults))
            session.add(instance)
            session.commit()

        return instance


def add_user(model: Union[Staff, Merchant], username: str, password: str):
    password = hashpw(password.encode(), gensalt()).decode()

    with main_session() as s:
        s.add(instance := model(username=username, password=password))
        s.commit()

    return instance
