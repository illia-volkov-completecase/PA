from typing import Optional
from uuid import uuid4, UUID

from sqlmodel import Field, SQLModel, Relationship, Column, Enum, String, Text
from sqlalchemy.orm import relationship
from pydantic import condecimal

from .wallets import Wallet, Currency
from .choices import InvoiceStatusEnum, TransactionStatusEnum, PaymentSystemType


class Invoice(SQLModel, table=True):
    __tablename__ = 'invoice'

    id: Optional[int] = Field(default=None, primary_key=True)
    # token is exposed to user
    token: UUID = Field(default_factory=uuid4, index=True, sa_column=Column(String(36)))
    amount: condecimal(max_digits=20, decimal_places=3)
    status: str = Field(sa_column=Column(Enum(InvoiceStatusEnum)), default=TransactionStatusEnum.pending)

    to_wallet_id: int = Field(default=None, nullable=False, foreign_key='wallet.id')
    to_wallet: Wallet = Relationship(sa_relationship_kwargs={'foreign_keys': 'Invoice.to_wallet_id'})


class PaymentSystem(SQLModel, table=True):
    __tablename__ = 'payment_system'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(36)))
    system_type: str = Field(sa_column=Column(Enum(PaymentSystemType)))
    decryption_key: str = Field(sa_column=Column(String(1024)))


class Transaction(SQLModel, table=True):
    __tablename__ = 'transaction'

    id: Optional[int] = Field(default=None, primary_key=True)
    # token is exposed to user
    token: UUID = Field(default_factory=uuid4, index=True, sa_column=Column(String(36)))
    amount: condecimal(max_digits=20, decimal_places=3)
    status: str = Field(sa_column=Column(Enum(TransactionStatusEnum)), default=TransactionStatusEnum.pending)
    # b64 encoded decrypted response
    response: str = Field(sa_column=Column(Text))

    payment_system_id: int = Field(default=None, nullable=False, foreign_key='payment_system.id')
    payment_system: PaymentSystem = Relationship()

    invoice_id: int = Field(default=None, nullable=False, foreign_key='invoice.id')
    invoice: Invoice = Relationship()
