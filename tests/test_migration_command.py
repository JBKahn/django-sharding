from unittest import skip

from django.core.management import call_command
from django.test import TestCase
from mock import patch

from django_sharding_library.exceptions import InvalidMigrationException


@patch('django.core.management.commands.migrate.Command.handle')
class MigrationCommandTestCase(TestCase):

    def test_defauls_migrates_all_primary_dbs(self, mock_migrate_command):
        call_command('migrate', verbosity=0)
        databases_migrated = [call[1].get('database') for call in mock_migrate_command.call_args_list]
        expected_migrated_databases = ['app_shard_001', 'app_shard_002', 'app_shard_003', 'app_shard_004', 'default']

        self.assertEqual(sorted(databases_migrated), expected_migrated_databases)

    def test_all_option_added_to_databases(self, mock_migrate_command):
        call_command('migrate', database='all', verbosity=0)
        databases_migrated = [call[1].get('database') for call in mock_migrate_command.call_args_list]
        expected_migrated_databases = ['app_shard_001', 'app_shard_002', 'app_shard_003', 'app_shard_004', 'default']

        self.assertEqual(sorted(databases_migrated), expected_migrated_databases)

    def test_migrate_single_db(self, mock_migrate_command):
        call_command('migrate', database='default', verbosity=0)
        databases_migrated = [call[1].get('database') for call in mock_migrate_command.call_args_list]
        expected_migrated_databases = ['default']

        self.assertEqual(sorted(databases_migrated), expected_migrated_databases)

    def test_migrate_replica_raises_exception(self, mock_migrate_command):
        with self.assertRaises(InvalidMigrationException):
            call_command('migrate', database='app_shard_001_replica_001', verbosity=0)

        databases_migrated = []
        expected_migrated_databases = []

        self.assertEqual(databases_migrated, expected_migrated_databases)

    @skip("skipped until fix https://code.djangoproject.com/ticket/26597")
    def test_passes_other_args(self, mock_migrate_command):
        call_command('migrate', database='app_shard_001', fake=True, verbosity=0, app_label='tests', migration_name='0001', noinput=True, fake_initial=True, interactive=False, list=True)

        self.assertTrue(mock_migrate_command.call_args[1].get('fake'))
        self.assertTrue(mock_migrate_command.call_args[1].get('fake_initial'))
        self.assertFalse(mock_migrate_command.call_args[1].get('interactive'))
        self.assertTrue(mock_migrate_command.call_args[1].get('list'))
        self.assertEqual(mock_migrate_command.call_args[1].get('verbosity'), 0)
        self.assertEqual(mock_migrate_command.call_args[1].get('database'), 'app_shard_001')
        self.assertEqual(mock_migrate_command.call_args[1].get('app_label'), 'tests')
        self.assertEqual(mock_migrate_command.call_args[1].get('migration_name'), '0001')
