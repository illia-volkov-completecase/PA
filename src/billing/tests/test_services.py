from decimal import Decimal

from models.wallets import Wallet, Currency, ConversionRate
from models.transactions import Attempt, Transaction
from models.accounts import Merchant
from models.choices import TransactionStatus, InvoiceStatus
from misc import add_user, get_or_create
from services import *


def test_calculate_conv_rate(session):
    c1 = session.query(Currency).filter(Currency.code == 'uah').first()
    c2 = session.query(Currency).filter(Currency.code == 'usd').first()
    c3 = session.query(Currency).filter(Currency.code == 'eur').first()
    c4 = session.query(Currency).filter(Currency.code == 'gbp').first()

    assert calculate_conv_rate(c1.id, c1.id) == Decimal('1')

    get_or_create(
        ConversionRate,
        session=session,
        from_currency_id=c1.id, to_currency_id=c2.id,
        defaults=dict(rate='2', allow_reversed=False),
    )

    cr = get_or_create(
        ConversionRate,
        session=session,
        from_currency_id=c3.id, to_currency_id=c4.id,
        defaults=dict(rate='2', allow_reversed=False),
    )

    assert calculate_conv_rate(c1.id, c3.id) is None

    get_or_create(
        ConversionRate,
        session=session,
        from_currency_id=c2.id, to_currency_id=c3.id,
        defaults=dict(rate='3', allow_reversed=False),
    )

    assert calculate_conv_rate(c1.id, c3.id) == Decimal('6')

    get_or_create(
        ConversionRate,
        session=session,
        from_currency_id=c1.id, to_currency_id=c4.id,
        defaults=dict(rate='2', allow_reversed=False),
    )

    assert calculate_conv_rate(c1.id, c3.id) == Decimal('6')

    cr.allow_reversed = True
    session.add(cr)
    session.commit()

    assert calculate_conv_rate(c1.id, c3.id) == Decimal('1')

    assert calculate_rates(1) == {1: Decimal('1')}
    assert calculate_rates(2) == {2: Decimal('1'), 1: Decimal('2')}
    assert calculate_rates(3) == {
        4: Decimal('0.5'), 3: Decimal('1'), 2: Decimal('3'), 1: Decimal('1')
    }
    assert calculate_rates(4) == {
        4: Decimal('1'), 3: Decimal('2'), 2: Decimal('6'), 1: Decimal('2')
    }


def test_transaction_success(session):
    merchant = add_user(Merchant, 'test_transaction', 'test_transaction')

    c1 = session.query(Currency).filter(Currency.code == 'uah').first()
    amount = Decimal('10')

    wallet = Wallet(merchant_id=merchant.id, currency_id=c1.id)
    session.add(wallet)
    session.commit()

    invoice = Invoice(
        amount=amount,
        from_currency_id=c1.id,
        to_wallet_id=wallet.id
    )
    session.add(invoice)
    session.commit()

    with InvoiceManager(invoice.id) as manager:
        transaction = manager.create_transaction(currency_id=c1.id, effective_amount=Decimal('5'))

    with TransactionManager(transaction.id) as manager:
        attempt = manager.create_attempt(payment_system_id=1)

    assert 0 == session.query(Transaction)\
        .filter(Transaction.status != TransactionStatus.pending)\
        .filter(Transaction.invoice_id == invoice.id)\
        .count()

    with AttemptManager(attempt.id) as manager:
        manager.success()

    assert 1 == session.query(Transaction)\
        .filter(Transaction.status != TransactionStatus.pending)\
        .filter(Transaction.invoice_id == invoice.id)\
        .count()
    assert InvoiceStatus.incomplete == session.query(Invoice.status)\
        .filter(Invoice.id == invoice.id)\
        .scalar()

    with InvoiceManager(invoice.id) as manager:
        transaction = manager.create_transaction(currency_id=c1.id, effective_amount=Decimal('5'))

    with TransactionManager(transaction.id) as manager:
        attempt = manager.create_attempt(payment_system_id=1)

    with AttemptManager(attempt.id) as manager:
        manager.fail()

    assert 1 == session.query(Transaction)\
        .filter(Transaction.status == TransactionStatus.success)\
        .filter(Transaction.invoice_id == invoice.id)\
        .count()
    assert 1 == session.query(Transaction)\
        .filter(Transaction.status == TransactionStatus.fail)\
        .filter(Transaction.invoice_id == invoice.id)\
        .count()
    assert InvoiceStatus.incomplete == session.query(Invoice.status)\
        .filter(Invoice.id == invoice.id)\
        .scalar()

    with TransactionManager(transaction.id) as manager:
        attempt = manager.create_attempt(payment_system_id=1)

    with AttemptManager(attempt.id) as manager:
        manager.success()

    assert 2 == session.query(Transaction)\
        .filter(Transaction.status == TransactionStatus.success)\
        .filter(Transaction.invoice_id == invoice.id)\
        .count()
    assert InvoiceStatus.complete == session.query(Invoice.status)\
        .filter(Invoice.id == invoice.id)\
        .scalar()
    assert 3 == session.query(Attempt)\
        .join(Transaction)\
        .filter(Transaction.id == Attempt.transaction_id)\
        .count()


def test_transaction_conversion(session):
    merchant = add_user(Merchant, 'test_transaction_conversion', 'test_transaction_conversion')

    c1 = session.query(Currency).filter(Currency.code == 'uah').first()
    c2 = session.query(Currency).filter(Currency.code == 'usd').first()

    wallet = Wallet(merchant_id=merchant.id, currency_id=c2.id)
    session.add(wallet)
    session.commit()

    cr = get_or_create(
        ConversionRate,
        session=session,
        from_currency_id=c1.id, to_currency_id=c2.id,
        defaults=dict(rate='2', allow_reversed=False),
    )
    cr.rate = Decimal('2')
    session.add(cr)
    session.commit()

    invoice = Invoice(
        amount=Decimal('30'),
        from_currency_id=c2.id,
        to_wallet_id=wallet.id
    )
    session.add(invoice)
    session.commit()

    with InvoiceManager(invoice.id) as manager:
        transaction1 = manager.create_transaction(currency_id=c2.id, effective_amount=Decimal('10'))
        transaction2 = manager.create_transaction(currency_id=c1.id, effective_amount=Decimal('19.9'))
        transaction3 = manager.create_transaction(currency_id=c1.id, effective_amount=Decimal('0.1'))

    assert transaction1.amount == Decimal('10')
    assert transaction2.amount == Decimal('39.8')
    assert transaction3.amount == Decimal('0.2')

    with TransactionManager(transaction1.id) as manager:
        attempt1 = manager.create_attempt(payment_system_id=1)

    with TransactionManager(transaction2.id) as manager:
        attempt2 = manager.create_attempt(payment_system_id=1)

    with TransactionManager(transaction3.id) as manager:
        attempt3 = manager.create_attempt(payment_system_id=1)

    with AttemptManager(attempt1.id) as amanager, InvoiceManager(invoice.id) as imanager:
        amanager.success()
        imanager.fetch()
        assert imanager.paid_amount == Decimal('10')
        assert imanager.invoice.status == InvoiceStatus.incomplete

    with AttemptManager(attempt2.id) as amanager, InvoiceManager(invoice.id) as imanager:
        amanager.success()
        imanager.fetch()
        assert imanager.paid_amount == Decimal('29.9')
        assert imanager.invoice.status == InvoiceStatus.incomplete

    with AttemptManager(attempt3.id) as amanager, InvoiceManager(invoice.id) as imanager:
        amanager.success()
        imanager.fetch()
        assert imanager.paid_amount == Decimal('30')
        assert imanager.invoice.status == InvoiceStatus.complete


def test_internal_transaction(session):
    uah = session.query(Currency).filter(Currency.code == 'uah').first()

    merchant1 = add_user(Merchant, 'test_internal_transaction1', 'test')
    merchant2 = add_user(Merchant, 'test_internal_transaction2', 'test')

    wallet1 = Wallet(merchant_id=merchant1.id, currency_id=uah.id)
    session.add(wallet1)
    session.commit()

    wallet2 = Wallet(merchant_id=merchant2.id, currency_id=uah.id, amount=Decimal('100'))
    session.add(wallet2)
    session.commit()

    invoice = Invoice(
        amount=Decimal('20'),
        from_currency_id=uah.id,
        to_wallet_id=wallet2.id
    )
    session.add(invoice)
    session.commit()

    with InvoiceManager(invoice.id) as manager:
        transaction = manager.pay_with_wallet(
            merchant_id=merchant1.id,
            wallet_id=wallet1.id,
            effective_amount=Decimal('10')
        )
    assert transaction
    assert transaction.id
    assert transaction.status == TransactionStatus.fail
    assert InvoiceStatus.incomplete == session.query(Invoice.status)\
                                              .filter(Invoice.id == invoice.id)\
                                              .scalar()

    wallet1.amount = Decimal('100')
    session.add(wallet1)
    session.commit()

    with InvoiceManager(invoice.id) as manager:
        transaction = manager.pay_with_wallet(
            merchant_id=merchant1.id,
            wallet_id=wallet1.id,
            effective_amount=Decimal('10')
        )
    assert transaction
    assert transaction.id
    assert transaction.status == TransactionStatus.success
    assert InvoiceStatus.incomplete == session.query(Invoice.status)\
                                              .filter(Invoice.id == invoice.id)\
                                              .scalar()

    with InvoiceManager(invoice.id) as manager:
        manager.fetch()
        assert manager.paid_amount == Decimal('10')
        assert manager.unpaid_amount == Decimal('10')

    with InvoiceManager(invoice.id) as manager:
        transaction = manager.pay_with_wallet(
            merchant_id=merchant1.id,
            wallet_id=wallet1.id,
            effective_amount=Decimal('10')
        )
    assert transaction
    assert transaction.id
    assert transaction.status == TransactionStatus.success
    assert InvoiceStatus.complete == session.query(Invoice.status)\
                                            .filter(Invoice.id == invoice.id)\
                                            .scalar()

    assert Decimal('80') == session.query(Wallet.amount)\
        .filter(Wallet.id == wallet1.id)\
        .scalar()

    assert Decimal('120') == session.query(Wallet.amount)\
        .filter(Wallet.id == wallet2.id)\
        .scalar()


def test_internal_transaction_conversion(session):
    uah = session.query(Currency).filter(Currency.code == 'uah').first()
    usd = session.query(Currency).filter(Currency.code == 'usd').first()

    merchant1 = add_user(Merchant, 'test_internal_transaction_conversion1', 'test')
    merchant2 = add_user(Merchant, 'test_internal_transaction_conversion2', 'test')

    wallet1 = Wallet(merchant_id=merchant1.id, currency_id=usd.id, amount=Decimal('100'))
    session.add(wallet1)
    session.commit()

    wallet2 = Wallet(merchant_id=merchant2.id, currency_id=uah.id, amount=Decimal('100'))
    session.add(wallet2)
    session.commit()

    cr = get_or_create(
        ConversionRate,
        session=session,
        from_currency_id=uah.id, to_currency_id=usd.id,
        defaults=dict(rate=Decimal('20'), allow_reversed=True)
    )
    cr.rate = Decimal('20')
    cr.allow_reversed = True
    session.add(cr)
    session.commit()

    invoice = Invoice(
        amount=Decimal('100'),
        from_currency_id=uah.id,
        to_wallet_id=wallet2.id
    )
    session.add(invoice)
    session.commit()

    with InvoiceManager(invoice.id) as manager:
        transaction = manager.pay_with_wallet(
            merchant_id=merchant1.id,
            wallet_id=wallet1.id,
            effective_amount=Decimal('100')
        )
    assert transaction
    assert transaction.id
    assert transaction.status == TransactionStatus.success
    assert InvoiceStatus.complete == session.query(Invoice.status)\
                                            .filter(Invoice.id == invoice.id)\
                                            .scalar()


    assert Decimal('95') == session.query(Wallet.amount)\
                                   .filter(Wallet.id == wallet1.id)\
                                   .scalar()

    assert Decimal('200') == session.query(Wallet.amount)\
                                    .filter(Wallet.id == wallet2.id)\
                                    .scalar()
