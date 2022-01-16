from os import environ


DATABASE_URL = environ['DATABASE_URL']
TEST_DATABASE_URL = environ['TEST_DATABASE_URL']
SYNC_DRIVER = environ['SYNC_DRIVER']
ASYNC_DRIVER = environ['ASYNC_DRIVER']
DATABASES = {
    'sync': {
        'driver': SYNC_DRIVER,
        'url': f'{SYNC_DRIVER}:{DATABASE_URL}',
    },
    'async': {
        'driver': ASYNC_DRIVER,
        'url': f'{ASYNC_DRIVER}:{DATABASE_URL}',
    },
    'test': {
        'driver': SYNC_DRIVER,
        'url': f'{SYNC_DRIVER}:{TEST_DATABASE_URL}',
    }
}
ECHO_SQL = True
