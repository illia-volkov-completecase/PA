import pytest
from urllib.parse import urljoin
from decimal import Decimal
from requests.auth import _basic_auth_str

from misc import add_user, get_or_create
from models.accounts import Merchant, Staff
from models.wallets import Wallet, Currency, ConversionRate
from models.transactions import Invoice, Transaction, Attempt
from models.choices import CurrencyCode, AttemptStatus, InvoiceStatus
from services import calculate_rates, AttemptManager, InvoiceManager
from settings.core import HOSTNAME


def basic_auth(model, test_name: str):
    user = add_user(model, test_name, test_name)
    return user, {'Authorization': _basic_auth_str(test_name, test_name)}


def test_app_session(session, client):
    user, auth = basic_auth(Merchant, 'test_app_session')

    response = client.get('/')
    assert response.status_code == 401

    response = client.get('/', headers=auth)
    assert response.status_code == 200

    response = client.get('/currencies')
    assert response.status_code == 200
    assert response.json() == {'currencies': [
        c.dict() for c in session.query(Currency).all()
    ]}

    response = client.get('/currencies')
    assert response.status_code == 200
    assert response.json() == {'currencies': [
        c.dict() for c in session.query(Currency).all()
    ]}

    get_or_create(
        ConversionRate, session=session,
        from_currency_id=1, to_currency_id=2,
        defaults=dict(rate='2.2', allow_reversed=False)
    )

    response = client.get('/rates/1')
    assert response.status_code == 200
    rates = response.json().get('rates')
    rates = {int(k): float(v) for k, v in rates.items()}
    calculated_rates = {int(k): float(v) for k, v in calculate_rates(1).items()}
    assert rates == calculated_rates

    response = client.get('/wallets')
    assert response.status_code == 401

    response = client.get('/wallets', headers=auth)
    assert response.status_code == 200
    assert response.json() == {'data': [], 'itemsCount': 0}

    assert 0 == session.query(Wallet).filter(Wallet.merchant_id == user.id).count()

    response = client.post('/wallet')
    assert response.status_code == 401

    response = client.post('/wallet', json={'currency_id': 1}, headers=auth)
    assert response.status_code == 200

    assert 1 == session.query(Wallet).filter(Wallet.merchant_id == user.id).count()
    wallet = session.query(Wallet).filter(Wallet.merchant_id == user.id).one()

    response = client.get('/wallets', headers=auth)
    assert response.status_code == 200
    assert response.json() == {'data': [{
        'id': wallet.id, 'amount': 0.0, 'currency_id': 1, 'merchant_id': user.id
    }], 'itemsCount': 1}

    response = client.get('/invoices')
    assert response.status_code == 401

    response = client.get('/invoices', headers=auth)
    assert response.status_code == 200
    assert response.json() == {'data': [], 'itemsCount': 0}

    response = client.post('/invoice')
    assert response.status_code == 401

    response = client.post('/invoice', json={
        'to_wallet_id': wallet.id,
        'amount': 22.2
    }, headers=auth)
    assert response.status_code == 200
    inv_token = response.json()['token']

    assert 1 == session.query(Invoice).filter(Invoice.to_wallet_id == wallet.id).count()
    invoice = session.query(Invoice).filter(Invoice.to_wallet_id == wallet.id).one()

    url = f'/pay/{inv_token}'

    response = client.get(url)
    assert response.status_code == 200
    assert response.json() == {
        'wallet_id': wallet.id,
        'currency_id': 1,
        'amount': 22.2,
        'paid': 0,
        'unpaid': 22.2
    }

    response = client.post(url, json={'amount': '11.1', 'currency_id': 1})
    assert response.status_code == 200
    token = response.json()['token']

    url = f'/attempt/{token}'

    response = client.get(url)
    assert response.status_code == 200
    assert response.json() == [{'id': 1, 'name': 'test', 'type': 'visa'}]

    response = client.post(url, json={'payment_system_id': 1})
    assert response.status_code == 200

    attempt = session.query(Attempt)\
                     .filter(Attempt.transaction_id == Transaction.id)\
                     .filter(Transaction.token == token)\
                     .one()

    with AttemptManager(attempt.id) as manager:
        manager.success()

    with InvoiceManager(invoice.id) as manager:
        manager.fetch()
        assert manager.paid_amount == manager.unpaid_amount == Decimal('11.1')

    payer_user, payer_auth = basic_auth(Merchant, 'test_app_session_payer')
    payer_wallet = Wallet(
        merchant_id=payer_user.id,
        currency_id=1,
        amount=Decimal('100')
    )
    session.add(payer_wallet)
    session.commit()

    url = f'/pay/{inv_token}'
    response = client.post(
        url, json={'amount': '10.0', 'from_wallet_id': payer_wallet.id},
        headers=payer_auth
    )
    assert response.status_code == 200

    with InvoiceManager(invoice.id) as manager:
        manager.fetch()
        assert manager.paid_amount == Decimal('21.1')
        assert manager.invoice.status != InvoiceStatus.complete

    url = f'/pay/{inv_token}'
    response = client.post(
        url, json={'amount': '1.1', 'from_wallet_id': payer_wallet.id},
        headers=payer_auth
    )
    assert response.status_code == 200

    with InvoiceManager(invoice.id) as manager:
        manager.fetch()
        assert manager.paid_amount == Decimal('22.2')
        assert manager.invoice.status == InvoiceStatus.complete


    staff, staff_auth = basic_auth(Staff, 'test_app_session_staff')
    url = f'/refund/{token}'

    response = client.post(url)
    assert response.status_code == 200
    status = response.json()['status']

    assert status == session.query(Transaction.status)\
                            .filter(Transaction.token == token)\
                            .scalar()

    with InvoiceManager(invoice.id) as manager:
        manager.fetch()
        assert manager.paid_amount == Decimal('11.1')
        assert manager.invoice.status == InvoiceStatus.incomplete
