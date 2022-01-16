import pytest
from requests.auth import _basic_auth_str

from misc import add_user
from models.accounts import Merchant


def basic_auth(test_name: str):
    add_user(Merchant, test_name, test_name)
    return {'Authorization': _basic_auth_str(test_name, test_name)}
