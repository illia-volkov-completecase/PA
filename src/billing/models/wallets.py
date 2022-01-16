from typing import Optional

from sqlmodel import Field, SQLModel, Relationship
from pydantic import condecimal
from sqlalchemy import UniqueConstraint, Column, Enum

from .accounts import Merchant
from .choices import CurrencyCode


class Currency(SQLModel, table=True):
    __tablename__ = 'currency'
    __table_args__ = (UniqueConstraint('code', name='uniq_currency'),)

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(sa_column=Column(Enum(CurrencyCode)))


class Wallet(SQLModel, table=True):
    __tablename__ = 'wallet'
    __table_args__ = (UniqueConstraint('merchant_id', 'currency_id', name='uniq_wallet'),)

    id: Optional[int] = Field(default=None, primary_key=True)
    amount: condecimal(max_digits=20, decimal_places=3) = Field(default=0)

    merchant_id: int = Field(default=None, nullable=False, foreign_key='merchant.id')
    merchant: Merchant = Relationship()

    currency_id: int = Field(default=None, nullable=False, foreign_key='currency.id')
    currency: Currency = Relationship()


class ConversionRate(SQLModel, table=True):
    __tablename__ = 'conversion_rate'
    __table_args__ = (UniqueConstraint('from_currency_id', 'to_currency_id', name='uniq_conv_rate'),)

    id: Optional[int] = Field(default=None, primary_key=True)
    rate: condecimal(max_digits=20, decimal_places=3)  # for simplicity same as amount
    allow_reversed: bool  # allows backward conversion with reversed rate

    from_currency_id: int = Field(default=None, nullable=False, foreign_key='currency.id')
    from_currency: Currency = Relationship(sa_relationship_kwargs={
        'foreign_keys': 'ConversionRate.from_currency_id'
    })

    to_currency_id: int = Field(default=None, nullable=False, foreign_key='currency.id')
    to_currency: Currency = Relationship(sa_relationship_kwargs={
        'foreign_keys': 'ConversionRate.to_currency_id'
    })
