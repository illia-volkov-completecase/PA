from enum import Enum


class CurrencyCode(str, Enum):
    """
    as of ISO 4217
    """

    usd = 'USD'
    uah = 'UAH'
    eur = 'EUR'
    gbp = 'GBP'


class InvoiceStatus(str, Enum):
    pending = 'pending'
    incomplete = 'incomplete'
    complete = 'complete'


class TransactionStatus(str, Enum):
    pending = 'pending'
    success = 'success'
    fail = 'fail'
    refunded = 'refunded'


class TransactionType(str, Enum):
    external = 'external'
    internal = 'internal'


class AttemptStatus(str, Enum):
    pending = 'pending'
    success = 'success'
    fail = 'fail'


class PaymentSystemType(str, Enum):
    visa = 'visa'
