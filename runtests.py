import os
import sys
from datetime import datetime
import time

try:
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    from django_sharding_library.settings_helpers import database_configs
except ImportError:
    import traceback
    traceback.print_exc()
    raise ImportError("To fix this error, run: pip install -r requirements-test.txt")


TRAVISCI = os.environ.get('TRAVIS')

DATABASES = database_configs(databases_dict={
    'unsharded_databases': [
        {
            'name': 'default',
            'environment_variable': 'DATABASE_URL',
            'default_database_url': 'postgres://postgres:@localhost/default' if TRAVISCI else 'sqlite://testing123'
        }
    ],
    'sharded_databases': [
        {
            'name': 'app_shard_001',
            'environment_variable': 'SHARD_001_DATABASE_URL',
            'default_database_url': 'postgres://postgres:@localhost/sharding_001' if TRAVISCI else 'sqlite://testing124',
            'replicas': [
                {
                    'name': 'app_shard_001_replica_001',
                    'environment_variable': 'REPLICA_001_DATABASE_URL',
                    'default_database_url': 'postgres://postgres:@localhost/sharding_replica_001' if TRAVISCI else 'sqlite://testing125'
                },
                {
                    'name': 'app_shard_001_replica_002',
                    'environment_variable': 'REPLICA_002_DATABASE_URL',
                    'default_database_url': 'postgres://postgres:@localhost/sharding_replica_002' if TRAVISCI else 'sqlite://testing126'
                },
            ]
        },
        {
            'name': 'app_shard_002',
            'environment_variable': 'SHARD_002_DATABASE_URL',
            'default_database_url': 'mysql://travis:@localhost/sharding_002' if TRAVISCI else 'sqlite://testing127'
        },
    ]
})
settings.configure(
    DEBUG=True,
    USE_TZ=True,
    DATABASES=DATABASES,
    DATABASE_ROUTERS=['django_sharding_library.router.ShardedRouter'],
    AUTH_USER_MODEL='tests.User',
    ROOT_URLCONF="django_sharding.urls",
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sites",
        "django_sharding",
        "django_nose",
        "tests",
    ],
    SITE_ID=1,
    MIDDLEWARE_CLASSES=(),
    SHARD_EPOCH=int(time.mktime(datetime(2016, 1, 1).timetuple()) * 1000),
)
django.setup()


def run_tests(*test_args):
    if not test_args:
        test_args = ['tests']

    from django.core.management import call_command

    call_command('makemigrations', 'tests')

    # Run tests
    TestRunner = get_runner(settings)
    test_runner = TestRunner()

    failures = test_runner.run_tests(test_args, interactive=False)

    if failures:
        sys.exit(bool(failures))
    sys.exit(0)


if __name__ == '__main__':
    run_tests(*sys.argv[1:])
