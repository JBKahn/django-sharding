def pytest_configure():
    from datetime import datetime
    import time

    try:
        import django
        from django.conf import settings
        from django_sharding_library.settings_helpers import database_configs
    except ImportError:
        import traceback
        traceback.print_exc()
        raise ImportError("To fix this error, run: pip install -r requirements-test.txt")

    DATABASES = database_configs(databases_dict={
        'unsharded_databases': [
            {
                'name': 'default',
                'environment_variable': 'DATABASE_URL',
                'default_database_url': 'sqlite://testing123'
            }
        ],
        'sharded_databases': [
            {
                'name': 'app_shard_001',
                'environment_variable': 'SHARD_001_DATABASE_URL',
                'default_database_url': 'sqlite://testing124',
                'replicas': [
                    {
                        'name': 'app_shard_001_replica_001',
                        'environment_variable': 'REPLICA_001_DATABASE_URL',
                        'default_database_url': 'sqlite://testing125'
                    },
                    {
                        'name': 'app_shard_001_replica_002',
                        'environment_variable': 'REPLICA_002_DATABASE_URL',
                        'default_database_url': 'sqlite://testing126'
                    },
                ]
            },
            {
                'name': 'app_shard_002',
                'environment_variable': 'SHARD_002_DATABASE_URL',
                'default_database_url': 'sqlite://testing127'
            },
            {
                'name': 'app_shard_003',
                'shard_group': 'postgres',
                'environment_variable': 'SHARD_003_DATABASE_URL',
                'default_database_url': 'sqlite://testing125'
            },
            {
                'name': 'app_shard_004',
                'shard_group': 'postgres',
                'environment_variable': 'SHARD_004_DATABASE_URL',
                'default_database_url': 'sqlite://testing125'
            },
        ]
    })
    settings.configure(
        DEBUG=True,
        USE_TZ=True,
        DATABASES=DATABASES,
        DATABASE_ROUTERS=['django_sharding_library.router.ShardedRouter'],
        AUTH_USER_MODEL='tests.User',
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
