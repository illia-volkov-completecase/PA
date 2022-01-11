from pydantic import BaseModel
from pydantic.main import ModelMetaclass


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
