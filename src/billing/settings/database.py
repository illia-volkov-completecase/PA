from os import environ

DATABASE_URL = environ['DATABASE_URL']
SYNC_DRIVER = environ['SYNC_DRIVER']
ASYNC_DRIVER = environ['ASYNC_DRIVER']
DATABASES = {
    'sync': {
        'url': f'{SYNC_DRIVER}:{DATABASE_URL}',
    },
    'async': {
        'url': f'{ASYNC_DRIVER}:{DATABASE_URL}',
    }
}
ECHO_SQL = True
