from django.core.management import call_command
from django.test import TestCase
from mock import patch


@patch('django_sharding_library.management.command.create_postgres_sequences.create_postgres_global_sequence')
@patch('django_sharding_library.management.command.create_postgres_sequences.create_postgres_shard_id_function')
@patch('django_sharding_library.management.command.create_postgres_sequences.verify_postres_id_field_setup_correctly')
class MigrationCommandTestCase(TestCase):

    def test_defauls_migrates_all_primary_dbs(self, mock_verify, mock_create_func, mock_create_sequence):
        call_command('create_postgres_sequences')
        pass
