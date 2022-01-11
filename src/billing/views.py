from typing import Union

from fastapi import Request, Form, APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from starlette.responses import FileResponse

from settings.core import ROOT
from models.core import Session
from models.accounts import Merchant, Staff
from models.wallets import Wallet, Currency
from models.transactions import Invoice
from dependencies import get_user, get_merchant, db_session as db, paging, templates
from misc import Paginated


router = APIRouter()


User = Union[Merchant, Staff]


class AddWalletRequest(BaseModel):
    currency_id: int


class AddInvoiceRequest(BaseModel):
    amount: str
    to_wallet_id: int


@router.get('/')
def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@router.get('/config')
def currencies(session: Session = Depends(db)):
    return {
        'currencies': [c.dict() for c in session.query(Currency).all()],
        'pay_prefix': 'https://pay.com/payment/'
    }


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
def invoices(
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


@router.get('/payment/{token}', response_class=HTMLResponse)
def payment(request: Request, token: str, session: Session = Depends(db)):
    ctx = {'request': request}
    currencies = session.query(Currency).all()
    ctx = {'request': request, 'currencies': currencies}
    return templates.TemplateResponse("payment.html", ctx)


@router.post('/payment/{token}', response_class=HTMLResponse)
def create_transaction(
        request: Request, token: str, session: Session = Depends(db),
        currency_id: int = Form(...)
):
    pass
