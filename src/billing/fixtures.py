def load_currencies(session):
    from models.wallets import Currency, ConversionRate
    from models.choices import CurrencyCode
    from misc import get_or_create

    uah = get_or_create(Currency, session, code=CurrencyCode.uah)
    usd = get_or_create(Currency, session, code=CurrencyCode.usd)
    eur = get_or_create(Currency, session, code=CurrencyCode.eur)
    gbp = get_or_create(Currency, session, code=CurrencyCode.gbp)

    uah2usd = get_or_create(
        ConversionRate, session,
        from_currency_id=uah.id, to_currency_id=usd.id,
        defaults=dict(rate='27.96', allow_reversed=False)
    )
    usd2eur = get_or_create(
        ConversionRate, session,
        from_currency_id=usd.id, to_currency_id=eur.id,
        defaults=dict(rate='1.14', allow_reversed=False)
    )

    uah2gbp = get_or_create(
        ConversionRate, session,
        from_currency_id=uah.id, to_currency_id=gbp.id,
        defaults=dict(rate='38.23', allow_reversed=False)
    )
    gbp2eur = get_or_create(
        ConversionRate, session,
        from_currency_id=gbp.id, to_currency_id=eur.id,
        defaults=dict(rate='0.83', allow_reversed=False)
    )

    uah2eur = get_or_create(
        ConversionRate, session,
        from_currency_id=uah.id, to_currency_id=eur.id,
        defaults=dict(rate='31.92', allow_reversed=True)
    )


def load_payment_system(session):
    from cryptography.fernet import Fernet

    from models.transactions import PaymentSystem
    from models.choices import PaymentSystemType
    from misc import get_or_create

    key = Fernet.generate_key().decode()

    get_or_create(
        PaymentSystem,
        session=session,
        system_type=PaymentSystemType.visa,
        defaults=dict(decryption_key=key, name='visa')
    )
