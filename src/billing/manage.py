#!/usr/bin/env python

import fire


def alembic(*args):
    from plumbum import local

    from settings.core import ROOT

    alembic = local['alembic']

    with local.cwd(ROOT / 'models'):
        code, err, out = alembic.run(args)
        print(f'exit code {code}')
        print(err.strip())
        print(out.strip())


def runserver(host='0.0.0.0', port=8000):
    from uvicorn import run
    run('main:app', host=host, port=port)


def add_merchant():
    from bcrypt import hashpw, gensalt
    from models.accounts import Merchant
    from models.core import session

    username = input('username: ')
    password = input('password: ')
    password = hashpw(password.encode(), gensalt()).decode()

    with session() as s:
        s.add(Merchant(username=username, password=password))
        s.commit()


def add_staff():
    from bcrypt import hashpw, gensalt
    from models.accounts import Staff
    from models.core import session

    username = input('username: ')
    password = input('password: ')
    password = hashpw(password.encode(), gensalt()).decode()

    with session() as s:
        s.add(Staff(username=username, password=password))
        s.commit()


def shell():
    from models.accounts import Merchant, Staff
    from models.wallets import Currency, Wallet, ConversionRate
    from models.transactions import Invoice, PaymentSystem, Transaction
    from models.core import session, async_session

    try:
        import IPython
        IPython.embed()
    except ImportError:
        import code
        code.InteractiveConsole(locals=locals()).interact()


fire.Fire()
