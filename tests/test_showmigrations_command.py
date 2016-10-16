from django.core.management import call_command
from django.test import TestCase
from mock import patch

from django_sharding_library.exceptions import InvalidShowMigrationsException


@patch('django.core.management.commands.showmigrations.Command.handle')
class MigrationCommandTestCase(TestCase):

    def test_defauls_migrates_all_primary_dbs(self, mock_migrate_command):
        call_command('showmigrations', verbosity=0)
        databases_migrated = [call[1].get('database') for call in mock_migrate_command.call_args_list]
        expected_migrated_databases = ['app_shard_001', 'app_shard_002', 'app_shard_003', 'app_shard_004', 'default']

        self.assertEqual(sorted(databases_migrated), expected_migrated_databases)

    def test_all_option_added_to_databases(self, mock_migrate_command):
        call_command('showmigrations', database='all', verbosity=0)
        databases_migrated = [call[1].get('database') for call in mock_migrate_command.call_args_list]
        expected_migrated_databases = ['app_shard_001', 'app_shard_002', 'app_shard_003', 'app_shard_004', 'default']

        self.assertEqual(sorted(databases_migrated), expected_migrated_databases)

    def test_migrate_single_db(self, mock_migrate_command):
        call_command('showmigrations', database='default', verbosity=0)
        databases_migrated = [call[1].get('database') for call in mock_migrate_command.call_args_list]
        expected_migrated_databases = ['default']

        self.assertEqual(sorted(databases_migrated), expected_migrated_databases)

    def test_migrate_replica_raises_exception(self, mock_migrate_command):
        with self.assertRaises(InvalidShowMigrationsException):
            call_command('showmigrations', database='app_shard_001_replica_001', verbosity=0)

        databases_migrated = []
        expected_migrated_databases = []

        self.assertEqual(databases_migrated, expected_migrated_databases)
