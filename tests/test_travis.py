import os

from django.conf import settings
from django.test import TransactionTestCase

from django_sharding_library.constants import Backends


class TravisTestCase(TransactionTestCase):

    def test_travis_uses_non_sqlite_databases(self):
        TRAVISCI = os.environ.get('TRAVIS')

        if TRAVISCI:
            self.assertIn(settings.DATABASES['default']['ENGINE'], Backends.POSTGRES)
            self.assertIn(settings.DATABASES['app_shard_001']['ENGINE'], Backends.MYSQL)
            self.assertIn(settings.DATABASES['app_shard_002']['ENGINE'], Backends.POSTGRES)
            self.assertIn(settings.DATABASES['app_shard_001_replica_001']['ENGINE'], Backends.POSTGRES)
            self.assertIn(settings.DATABASES['app_shard_001_replica_002']['ENGINE'], Backends.POSTGRES)
        else:
            self.assertIn(settings.DATABASES['default']['ENGINE'], Backends.SQLITE)
            self.assertIn(settings.DATABASES['app_shard_001']['ENGINE'], Backends.SQLITE)
            self.assertIn(settings.DATABASES['app_shard_002']['ENGINE'], Backends.SQLITE)
            self.assertIn(settings.DATABASES['app_shard_001_replica_001']['ENGINE'], Backends.SQLITE)
            self.assertIn(settings.DATABASES['app_shard_001_replica_002']['ENGINE'], Backends.SQLITE)
