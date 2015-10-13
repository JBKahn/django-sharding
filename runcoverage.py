import os
import sys

try:
    from django.conf import settings
    from django.test.utils import get_runner
    from django_sharding_library.settings_helpers import database_configs

    DATABASES = database_configs(databases_dict={
        'unsharded_databases': [
            {
                'name': 'default',
                'environment_variable': 'DATABASE_URL',
                'default_database_url': 'postgres://sharding:sharding@localhost/sharding'
            }
        ],
        'sharded_databases': [
            {
                'name': 'app_shard_001',
                'environment_variable': 'SHARD_001_DATABASE_URL',
                'default_database_url': 'postgres://sharding:sharding@localhost/sharding_001',
                'replicas': [
                    {
                        'name': 'app_shard_001_replica_001',
                        'environment_variable': 'REPLICA_001_DATABASE_URL',
                        'default_database_url': 'postgres://sharding:sharding@localhost/sharding_replica_001'
                    },
                    {
                        'name': 'app_shard_001_replica_002',
                        'environment_variable': 'REPLICA_002_DATABASE_URL',
                        'default_database_url': 'postgres://sharding:sharding@localhost/sharding_replica_002'
                    },
                ]
            },
            {
                'name': 'app_shard_002',
                'environment_variable': 'SHARD_002_DATABASE_URL',
                'default_database_url': 'mysql://sharding:sharding@localhost/sharding_002'
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
        TEST_RUNNER='django_nose.NoseTestSuiteRunner',
        NOSE_ARGS=['--with-coverage', '--cover-package=django_sharding,django_sharding_library', '--cover-html', '--cover-html-dir={}'.format(os.getenv('CIRCLE_TEST_REPORTS', '.')), '--with-xunit', '--xunit-file={}/nosetests.xml'.format(os.getenv('CIRCLE_TEST_REPORTS', '.'))]
    )

    try:
        import django
        setup = django.setup
    except AttributeError:
        pass
    else:
        setup()

except ImportError:
    import traceback
    traceback.print_exc()
    raise ImportError("To fix this error, run: pip install -r requirements-test.txt")


def run_tests(*test_args):
    if not test_args:
        test_args = ['tests']

    # Run tests
    TestRunner = get_runner(settings)
    test_runner = TestRunner()

    test_runner.run_tests(test_args)
    sys.exit(0)


if __name__ == '__main__':
    run_tests(*sys.argv[1:])
