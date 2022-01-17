from typing import Union
from decimal import Decimal
from urllib.parse import urljoin

from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from settings.core import ROOT, HOSTNAME
from models.accounts import Merchant, Staff
from models.wallets import Wallet, Currency
from models.transactions import Invoice, Transaction, PaymentSystem
from dependencies import get_user, get_merchant, db_session as db, \
    paging, templates, try_get_merchant
from misc import Paginated
from services import *


router = APIRouter()


User = Union[Merchant, Staff]


class AddWalletRequest(BaseModel):
    currency_id: int


class WalletTransferRequest(BaseModel):
    from_wallet_id: int
    to_wallet_id: int
    amount: str


class CreateTransactionRequest(BaseModel):
    amount: str
    currency_id: Optional[int]
    from_wallet_id: Optional[int]


class CreateAttemptRequest(BaseModel):
    payment_system_id: int


class ConversionRateRequest(BaseModel):
    from_currency_id: int
    to_currency_id: int


class AddInvoiceRequest(BaseModel):
    amount: str
    to_wallet_id: int


@router.get('/')
def index(
        request: Request,
        session: Session = Depends(db), user: User = Depends(get_user)
):
    ctx = {
        'request': request, 'user': user,
        'pay_url': urljoin(HOSTNAME, 'pay'),
        'payment_systems': ', '.join(
            f'{{id: {s.id}, name: "{s.system_type}"}}'
            for s in session.query(PaymentSystem).all()
        ),
        'currencies': ', '.join(
            f'{{id: {c.id}, name: "{c.code}"}}'
            for c in session.query(Currency).all()
        )
    }
    if isinstance(user, Staff):
        return templates.TemplateResponse("staff.html", ctx)
    elif isinstance(user, Merchant):
        return templates.TemplateResponse("merchant.html", ctx)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nor staff, nor merchant",
        )


@router.get('/currencies')
def currencies(session: Session = Depends(db)):
    return {
        'currencies': [c.dict() for c in session.query(Currency).all()],
    }


@router.get('/rates/{from_currency_id}')
def rates(from_currency_id: int, session: Session = Depends(db)):
    return {'rates': calculate_rates(from_currency_id)}


@router.get('/wallets', response_model=list[Wallet])
def wallets(session: Session = Depends(db), user: User = Depends(get_user)):
    queryset = session.query(Wallet)
    if not isinstance(user, Staff):
        queryset = queryset.filter(Wallet.merchant_id == user.id)
    return queryset.all()


@router.post('/wallet', response_model=Wallet)
def add_wallet(
        add_wallet: AddWalletRequest,
        session: Session = Depends(db), merchant: Merchant = Depends(get_merchant)
):
    wallet = Wallet(merchant_id=merchant.id, currency_id=add_wallet.currency_id)
    session.add(wallet)
    session.commit()
    return wallet


@router.get('/invoices', response_model=Paginated[Invoice])
def get_invoices(
        paging: dict = Depends(paging),
        session: Session = Depends(db), user: User = Depends(get_user)
):
    queryset = session.query(Invoice)
    if not isinstance(user, Staff):
        queryset = queryset.join(Wallet).filter(Wallet.merchant_id == user.id)
    return Paginated[Invoice].from_queryset(queryset, **paging)


@router.post('/invoice', response_model=Invoice)
def add_invoice(
        add_invoice: AddInvoiceRequest,
        session: Session = Depends(db), merchant: Merchant = Depends(get_merchant)
):
    invoice = Invoice(
        amount=add_invoice.amount,
        to_wallet_id=add_invoice.to_wallet_id
    )
    session.add(invoice)
    session.commit()
    return invoice


@router.get('/transactions', response_model=Paginated[Transaction])
def transactions(
        paging: dict = Depends(paging),
        session: Session = Depends(db), user: User = Depends(get_user)
):
    queryset = session.query(Transaction)
    if not isinstance(user, Staff):
        queryset = queryset.join(Invoice)\
                           .join(Wallet).filter(Wallet.merchant_id == user.id)
    return Paginated[Transaction].from_queryset(queryset, **paging)


@router.get('/pay/{token}')
def get_payment_info_invoice(
        token: str,
        session: Session = Depends(db)
):
    invoice_id = session.query(Invoice.id).filter(Invoice.token == token).scalar()
    with InvoiceManager(invoice_id) as manager:
        return manager.get_payment_info()


@router.post('/pay/{token}')
def create_transaction(
        token: str,
        transaction_request: CreateTransactionRequest,
        session: Session = Depends(db),
        merchant: Optional[User] = Depends(try_get_merchant)
):
    merchant = session.query(Merchant).one()
    if merchant:
        invoice_id = session.query(Invoice.id).filter(Invoice.token == token).scalar()
        return create_internal_transaction(merchant.id, invoice_id, transaction_request)
    else:
        invoice_id = session.query(Invoice.id).filter(Invoice.token == token).scalar()
        return create_external_transaction(invoice_id, transaction_request)


def create_internal_transaction(
        merchant_id,
        invoice_id,
        request
):
    if request.from_wallet_id is None:
        detail = {
            "loc": ["body", "from_wallet_id"],
            "msg": "field required for internal transactions",
            "type": "value_error.missing"
        }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'detail': [detail]}
        )

    with InvoiceManager(invoice_id) as manager:
        transaction = manager.pay_with_wallet(
            merchant_id=merchant_id,
            wallet_id=request.from_wallet_id,
            effective_amount=Decimal(request.amount)
        )
        if transaction:
            return {'transaction': transaction.id, 'status': transaction.status}
        return {'error': 'transaction creation failed'}


def create_external_transaction(
        invoice_id,
        request
):
    if request.currency_id is None:
        detail = {
            "loc": ["body", "currency_id"],
            "msg": "field required for external transactions",
            "type": "value_error.missing"
        }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'detail': [detail]}
        )

    with InvoiceManager(invoice_id) as manager:
        transaction = manager.create_transaction(
            currency_id=request.currency_id,
            amount=Decimal(request.amount)
        )
        if transaction:
            return {
                'token': transaction.token,
                'attempt': urljoin(HOSTNAME, f'/attempt/{transaction.token}')
            }
        return {'error': 'transaction creation failed'}


@router.get('/attempt/{token}')
def get_payment_info_transaction(
        token: str,
        session: Session = Depends(db)
):
    transaction_id = session.query(Transaction.id).filter(Transaction.token == token).scalar()
    with TransactionManager(transaction_id) as manager:
        return manager.get_payment_info()


@router.post('/attempt/{token}')
def create_attempt(
        token: str,
        attempt_request: CreateAttemptRequest,
        session: Session = Depends(db)
):
    transaction_id = session.query(Transaction.id).filter(Transaction.token == token).scalar()
    with TransactionManager(transaction_id) as tmanager:
        attempt = tmanager.create_attempt(payment_system_id=attempt_request.payment_system_id)
        with AttemptManager(attempt.id) as amanager:
            return amanager.send()


@router.post('/visa/{payment_system_id}')
async def visa_response(
        payment_system_id: int,
        request: Request
):
    body = await request.body()
    with VisaManager(payment_system_id) as manager:
        manager.process_response(body)
    return {}
