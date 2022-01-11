from enum import Enum


class CurrencyEnum(str, Enum):
    """
    as of ISO 4217
    """

    usd = 'USD'
    uah = 'UAH'
    eur = 'EUR'
    gbp = 'GBP'


class InvoiceStatusEnum(str, Enum):
    pending = 'pending'
    incomplete = 'incomplete'
    complete = 'complete'


class TransactionStatusEnum(str, Enum):
    pending = 'pending'
    success = 'success'
    fail = 'fail'
    error = 'error'
    canceled = 'canceled'


class PaymentSystemType(str, Enum):
    visa = 'visa'
