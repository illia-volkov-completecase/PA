from os import environ
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
HOSTNAME = environ.get('SERVER_HOSTNAME', 'http://localhost:8000/')
