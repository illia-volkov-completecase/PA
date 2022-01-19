import json
from uuid import uuid4
from typing import Optional, Union
from decimal import Decimal
from contextvars import ContextVar

import networkx as nx
from networkx.algorithms.shortest_paths.generic import shortest_path
from networkx.algorithms.shortest_paths.weighted import\
    single_source_dijkstra_path
from cachetools.func import ttl_cache
from cryptography.fernet import Fernet

from models.core import session, serializable_session
from models.wallets import Wallet, Currency, ConversionRate
from models.transactions import PaymentSystem, Invoice, Transaction, Attempt
from models.choices import InvoiceStatus, TransactionStatus, AttemptStatus,\
    PaymentSystemType, TransactionType


DAY: int = 60 * 60 * 24


'''
    suppose we have following conv rate config

    uah -----> usd
     |          ^
     |          |
     |          |
     v          v
    gbp <----> eur

    and we want to pay invoice created with eur in uah
    there are 2 path:
    1) uah -> usd -> eur
    2) uah -> gbp -> eur
    with different final conversion rates
    1) (usd/uah) * (eur/usd)
    2) (gbp/uah) * (eur/uah)

    finding cheapest conversion rate from uah to eur essentially
    means finding shortest path in graph whose nodes represent
    currencies, while edges represent conversion rates
'''


@ttl_cache(maxsize=None, ttl=DAY)
def calculate_conv_rate(from_: int, to: int) -> Optional[Decimal]:
    if from_ == to:
        return Decimal('1')

    G = get_conversion_rate_graph()

    try:
        path = shortest_path(G, from_, to, weight='weight')
    except (nx.NodeNotFound, nx.NetworkXNoPath):
        return

    rate = Decimal('1')
    for left, right in zip(path, path[1:]):
        rate *= G.get_edge_data(left, right)['weight']

    return rate


def get_conversion_rate_graph(fresh: bool = False) -> nx.DiGraph:
    if fresh:
        return _get_conversion_rate_graph(uuid4())
    return _get_conversion_rate_graph()


def get_reversed_conversion_rate_graph(fresh: bool = False) -> nx.DiGraph:
    G = get_conversion_rate_graph(fresh=fresh)
    RG = nx.DiGraph()
    RG.add_nodes_from(G.nodes)
    for left, right in G.edges:
        rate = G.get_edge_data(left, right)['weight']
        RG.add_edge(right, left, weight=rate)
    return RG


@ttl_cache(maxsize=1, ttl=DAY)
def _get_conversion_rate_graph(_: Optional[str] = None) -> nx.DiGraph:
    G = nx.DiGraph()

    with session() as s:
        G.add_nodes_from([i for i, in s.query(Currency.id).all()])

        for cr in s.query(ConversionRate).all():
            G.add_edge(cr.from_currency_id, cr.to_currency_id, weight=cr.rate)
            if cr.allow_reversed:
                G.add_edge(
                    cr.to_currency_id, cr.from_currency_id,
                    weight=Decimal('1') / cr.rate
                )

    return G


@ttl_cache(maxsize=1, ttl=DAY)
def calculate_rates(from_currency_id: int):
    RG = get_reversed_conversion_rate_graph()
    paths = single_source_dijkstra_path(RG, from_currency_id)

    for k, v in paths.copy().items():
        rate = Decimal('1')
        path = paths[k]

        for left, right in zip(path, path[1:]):
            rate *= RG.get_edge_data(left, right)['weight']

        paths[k] = rate

    return paths


# to safely nest managers
manager_session = ContextVar('manager_session')


class BaseManager:
    '''
    Managers works as a service classes to invoices, payments & payment attempts
    They designed to be used as context managers. Main operations lock selected rows.
    '''

    def __init__(self):
        self.session = None
        self._token = None

    def __enter__(self):
        try:
            self.session = manager_session.get()
        except LookupError:
            session = serializable_session()
            session.__enter__()
            self._token = manager_session.set(session)
            self.session = session
        return self

    def __exit__(self, *args):
        if self._token:
            return self.session.__exit__(*args)


class InvoiceManager(BaseManager):
    def __init__(self, invoice_id: int):
        self.invoice_id = invoice_id
        self.wallet = None
        self.invoice = None
        self.paid_amount = None
        self.left_amount = None
        super().__init__()

    def fetch(self):
        self.wallet, self.invoice =\
            self.session.query(Wallet, Invoice)\
                        .filter(Wallet.id == Invoice.to_wallet_id)\
                        .filter(Invoice.id == self.invoice_id)\
                        .with_for_update()\
                        .one()
        paid_transactions =\
            self.session.query(Transaction)\
                        .filter(Transaction.invoice_id == self.invoice_id)\
                        .filter(Transaction.status == TransactionStatus.success)\
                        .with_for_update()\
                        .all()
        self.paid_amount = sum(t.effective_amount for t in paid_transactions)
        self.unpaid_amount = self.invoice.amount - self.paid_amount

    def create_transaction(
            self, currency_id: int, *,
            amount: Optional[Decimal] = None,
            effective_amount: Optional[Decimal] = None
    ):
        self.fetch()

        if (rate := calculate_conv_rate(currency_id, self.wallet.currency_id)) is None:
            return

        if (pair := self.calculate_amounts(amount, effective_amount, rate)) is None:
            return

        amount, effective_amount = pair

        transaction = Transaction(
            effective_amount=effective_amount,
            amount=amount,
            invoice_id=self.invoice.id
        )
        # sometimes passing amount in constructor don't work
        transaction.amount = amount
        transaction.effective_amount = effective_amount
        self.session.add(transaction)
        self.session.commit()

        return transaction

    def pay_with_wallet(
            self,
            merchant_id: int,
            wallet_id: int,
            amount: Optional[Decimal] = None,
            effective_amount: Optional[Decimal] = None
    ):
        self.fetch()
        from_wallet = self.session.query(Wallet)\
                                  .filter(Wallet.merchant_id == merchant_id)\
                                  .filter(Wallet.id == wallet_id)\
                                  .with_for_update()\
                                  .one()

        if not (rate := calculate_conv_rate(from_wallet.currency_id, self.wallet.currency_id)):
            return None

        if (pair := self.calculate_amounts(amount, effective_amount, rate)) is None:
            return

        amount, effective_amount = pair

        transaction = Transaction(
            effective_amount=effective_amount,
            amount=amount,
            invoice_id=self.invoice.id,
            from_wallet_id=from_wallet.id,
            transaction_type=TransactionType.internal,
            status=TransactionStatus.pending
        )
        # sometimes passing amount in constructor don't work
        transaction.amount = amount
        transaction.effective_amount = effective_amount
        self.invoice.status = InvoiceStatus.incomplete
        self.session.add(self.invoice)
        self.session.commit()

        try:
            if from_wallet.amount >= amount:
                from_wallet.amount -= amount
                self.wallet.amount += effective_amount
                transaction.status = TransactionStatus.success
                if effective_amount >= self.unpaid_amount:
                    self.invoice.status = InvoiceStatus.complete
                self.session.add_all((self.invoice, from_wallet, self.wallet, transaction))
                self.session.commit()
            else:
                transaction.status = TransactionStatus.fail
                self.session.add(transaction)
                self.session.commit()
        except:  # noqa
            transaction.status = TransactionStatus.fail
            self.session.add(transaction)
            self.session.commit()

        return transaction

    def calculate_amounts(self, amount, effective_amount, rate):
        if amount is not None:
            effective_amount = amount / rate
            if effective_amount > self.unpaid_amount:
                return None
            return (amount, effective_amount)
        elif effective_amount is not None:
            amount = effective_amount * rate
            if effective_amount > self.unpaid_amount:
                return None
            return (amount, effective_amount)
        else:
            return None

    def get_payment_info(self):
        self.fetch()
        return {
            'wallet_id': self.invoice.to_wallet_id,
            'currency_id': self.wallet.currency_id,
            'amount': self.invoice.amount,
            'paid': self.paid_amount,
            'unpaid': self.unpaid_amount
        }


class TransactionManager(BaseManager):
    def __init__(self, transaction_id: int):
        self.transaction_id = transaction_id
        self.transaction = None
        self.invoice = None
        super().__init__()

    def fetch(self, paid=None, complete=None):
        # just lock
        queryset = self.session.query(Transaction, Invoice)\
                               .filter(Transaction.id == self.transaction_id)\
                               .filter(Invoice.id == Transaction.invoice_id)
        if paid is True:
            queryset = queryset.filter(Transaction.status == TransactionStatus.success)
        elif paid is False:
            queryset = queryset.filter(Transaction.status != TransactionStatus.success)

        if complete is True:
            queryset = queryset.filter(Invoice.status == InvoiceStatus.complete)
        elif complete is False:
            queryset = queryset.filter(Invoice.status != InvoiceStatus.complete)

        self.transaction, self.invoice = queryset.with_for_update().one()

    def create_attempt(self, payment_system_id: int):
        self.fetch(complete=False)
        attempt = Attempt(
            transaction_id=self.transaction.id,
            payment_system_id=payment_system_id
        )
        self.session.add(attempt)
        self.session.commit()
        return attempt

    def get_payment_info(self):
        self.fetch(complete=False)
        systems = self.session.query(PaymentSystem).all()
        systems = [{'id': s.id, 'name': s.name, 'type': s.system_type} for s in systems]
        return systems

    def refund(self):
        self.fetch(paid=True)
        self.transaction.status = TransactionStatus.refunded
        self.invoice.status = InvoiceStatus.incomplete
        self.session.add_all((self.transaction, self.invoice))
        self.session.commit()
        return self.transaction


class AttemptManager(BaseManager):
    def __init__(self, attempt_id: int):
        self.attempt_id = attempt_id
        self.attempt = None
        self.transaction = None
        self.invoice = None
        super().__init__()

    def success(self):
        self.fetch()

        self.attempt.status = AttemptStatus.success
        self.transaction.status = TransactionStatus.success

        if self.__is_final_payment(including_self=True):
            self.invoice.status = InvoiceStatus.complete
        elif self.invoice.status == InvoiceStatus.pending:
            self.invoice.status = InvoiceStatus.incomplete

        self.__update()

    def __is_final_payment(self, including_self=False):
        paid = sum(t.effective_amount for t in self.other_paid_transactions)
        if including_self:
            paid += self.transaction.effective_amount
        if paid >= self.invoice.amount:
            return True
        return False

    def fail(self):
        self.fetch()
        self.__mark_failed(TransactionStatus.fail)
        self.__update()

    def error(self):
        self.fetch()
        self.__mark_failed(TransactionStatus.error)
        self.__update()

    def __mark_failed(self, transaction_status: TransactionStatus):
        self.attempt.status = AttemptStatus.fail
        self.transaction.status = transaction_status
        if self.invoice.status == InvoiceStatus.pending:
            self.invoice.status = InvoiceStatus.incomplete

    def send(self):
        self.fetch()
        system = self.session.query(PaymentSystem).get(self.attempt.payment_system_id)
        if system.system_type == PaymentSystemType.visa:
            return {
                'url': ('payment url, use `./manage.py '
                        f'emulate_response {self.attempt_id}` to emulate payment response')
            }
        else:
            return {'error': f'{system.system_type} is not supported'}

    def fetch(self):
        '''
        Note:
        https://www.postgresql.org/docs/14/sql-select.html#SQL-FOR-UPDATE-SHARE:
        `in the case of a join query, the rows locked are those that contribute to returned join rows`
        this allows us to lock all three entities at once. otherwise we would need to perform
        2 more queries (attempt & transaction) before locking invoice
        '''
        self.attempt, self.transaction, self.invoice = \
            self.session.query(Attempt, Transaction, Invoice)\
                        .filter(Attempt.id == self.attempt_id, Attempt.status == AttemptStatus.pending)\
                        .filter(Transaction.id == Attempt.transaction_id)\
                        .filter(Invoice.id == Transaction.invoice_id)\
                        .with_for_update()\
                        .one()
        self.other_paid_transactions = \
            self.session.query(Transaction)\
                        .filter(Transaction.invoice_id == self.invoice.id)\
                        .filter(Transaction.id != self.transaction.id)\
                        .filter(Transaction.status == TransactionStatus.success)\
                        .with_for_update()\
                        .all()

    def __update(self):
        self.session.add_all((self.attempt, self.transaction, self.invoice))
        self.session.commit()


class VisaManager(BaseManager):
    def __init__(self, payment_system_id: int):
        self.payment_system_id = payment_system_id
        self.payment = None
        super().__init__()

    def fetch(self):
        self.system = self.session.query(PaymentSystem)\
                                  .filter(PaymentSystem.system_type == PaymentSystemType.visa)\
                                  .filter(PaymentSystem.id == self.payment_system_id)\
                                  .one()

    def process_response(self, response: Union[str, bytes]):
        self.fetch()

        if not isinstance(response, bytes):
            response = response.encode()

        key = self.system.decryption_key
        if not isinstance(key, bytes):
            key = key.encode()

        fernet = Fernet(key)
        raw_response = fernet.decrypt(response)
        response = json.loads(raw_response)

        attempt_id = response['attempt_id']
        status = response['status']

        with AttemptManager(attempt_id) as manager:
            manager.fetch()
            manager.attempt.response = raw_response
            manager.session.add(manager.attempt)
            manager.session.commit()

            if status == AttemptStatus.success:
                manager.success()
            elif status == AttemptStatus.fail:
                manager.fail()
            else:
                manager.error()
