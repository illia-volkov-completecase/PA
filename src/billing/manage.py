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
        exit(code)


def runserver(host='0.0.0.0', port=8000):
    from uvicorn import run
    run('main:app', host=host, port=port)


def shell():
    from models.accounts import Merchant, Staff
    from models.wallets import Currency, Wallet, ConversionRate
    from models.transactions import Invoice, PaymentSystem, Transaction
    from models.core import session

    try:
        import IPython
        IPython.embed()
    except ImportError:
        import code
        code.InteractiveConsole(locals=locals()).interact()


def dbshell():
    from plumbum import local, FG

    from models.settings import DATABASE_URL

    pgcli = local['pgcli']
    pgcli[f'postgresql:{DATABASE_URL}'] & FG


def test(*args):
    from _pytest.config import main
    exit(main(args=['-sss', *args]))


def add_user(model):
    from models.accounts import Staff, Merchant
    from misc import add_user

    model = {'staff': Staff, 'merchant': Merchant}[model]

    username = input('username: ')
    password = input('password: ')
    add_user(model, username, password)


def emulate_response(attempt_id, hostname=None):
    from urllib.parse import urljoin
    import json

    import requests
    from settings.core import HOSTNAME
    from models.choices import AttemptStatus
    from models.transactions import Attempt, PaymentSystem
    from models.core import session
    from services import AttemptManager
    from cryptography.fernet import Fernet

    if hostname is None:
        hostname = HOSTNAME

    status = input('choose status [s]uccess/[f]ail/[e]rror: ')
    status = {
        'success': 'success',
        's': 'success',
        'fail': 'fail',
        'f': 'fail',
        'error': 'error',
        'e': 'error'
    }[status.strip()]

    with session() as s:
        attempt, system = s.query(Attempt, PaymentSystem)\
                           .filter(Attempt.id == attempt_id)\
                           .filter(PaymentSystem.id == Attempt.payment_system_id)\
                           .one()
        key = system.decryption_key
        fernet = Fernet(key.encode() if not isinstance(key, bytes) else key)

        url = urljoin(HOSTNAME, f'/{system.name}/{system.id}/')
        data = json.dumps({'attempt_id': attempt_id, 'status': status})
        data = fernet.encrypt(data.encode())
        print(f'sending {data}\nto {url}')
        response = requests.post(url, data=data)
        print(f'status code: {response.status_code}')
        print(f'body: {response.content}')


a = alembic
r = runserver
s = shell
db = dbshell
t = test

if __name__ == '__main__':
    fire.Fire()
