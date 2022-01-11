from typing import Optional

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, String


class Merchant(SQLModel, table=True):
    __tablename__ = 'merchant'

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(sa_column=Column(String(128)))
    password: str = Field(sa_column=Column(String(128)))


class Staff(SQLModel, table=True):
    __tablename__ = 'staff'

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(sa_column=Column(String(128)))
    password: str = Field(sa_column=Column(String(128)))
