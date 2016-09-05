from django.core.management import call_command
from django.test import TestCase
from mock import call, patch


mock_create_sequence_path = 'django_sharding_library.management.commands.create_postgres_sequences.create_postgres_global_sequence'
mock_create_func_path = 'django_sharding_library.management.commands.create_postgres_sequences.create_postgres_shard_id_function'
mock_verify_path = 'django_sharding_library.management.commands.create_postgres_sequences.verify_postres_id_field_setup_correctly'


class MigrationCommandTestCase(TestCase):

    def test_defauls_migrates_all_primary_dbs_with_shard_id(self):
        with patch(mock_verify_path, return_value=True) as mock_verify:
            with patch(mock_create_func_path) as mock_create_func:
                with patch(mock_create_sequence_path) as mock_create_sequence:
                    call_command('create_postgres_sequences')

        mock_verify.assert_has_calls(
            [
                call(db_alias='app_shard_001', function_name='next_sharded_id', sequence_name='global_id_sequence'),
                call(db_alias='app_shard_002', function_name='next_sharded_id', sequence_name='global_id_sequence')
            ]
        )

        mock_create_func.assert_has_calls(
            [
                call(db_alias='app_shard_001', sequence_name='global_id_sequence', shard_id=0),
                call(db_alias='app_shard_002', sequence_name='global_id_sequence', shard_id=1)
            ]
        )

        mock_create_sequence.assert_has_calls(
            [
                call(db_alias='app_shard_001', reset_sequence=False, sequence_name='global_id_sequence'),
                call(db_alias='app_shard_002', reset_sequence=False, sequence_name='global_id_sequence')
            ]
        )

    def test_reset_sequences(self):
        with patch(mock_verify_path, return_value=True) as mock_verify:
            with patch(mock_create_func_path) as mock_create_func:
                with patch(mock_create_sequence_path) as mock_create_sequence:
                    call_command('create_postgres_sequences', '--reset-sequence')

        mock_verify.assert_has_calls(
            [
                call(db_alias='app_shard_001', function_name='next_sharded_id', sequence_name='global_id_sequence'),
                call(db_alias='app_shard_002', function_name='next_sharded_id', sequence_name='global_id_sequence')
            ]
        )

        mock_create_func.assert_has_calls(
            [
                call(db_alias='app_shard_001', sequence_name='global_id_sequence', shard_id=0),
                call(db_alias='app_shard_002', sequence_name='global_id_sequence', shard_id=1)
            ]
        )

        mock_create_sequence.assert_has_calls(
            [
                call(db_alias='app_shard_001', reset_sequence=True, sequence_name='global_id_sequence'),
                call(db_alias='app_shard_002', reset_sequence=True, sequence_name='global_id_sequence')
            ]
        )

    def test_specify_database(self):
        with patch(mock_verify_path, return_value=True) as mock_verify:
            with patch(mock_create_func_path) as mock_create_func:
                with patch(mock_create_sequence_path) as mock_create_sequence:
                    call_command('create_postgres_sequences', '--database=app_shard_001')

        mock_verify.assert_has_calls(
            [
                call(db_alias='app_shard_001', function_name='next_sharded_id', sequence_name='global_id_sequence'),
            ]
        )

        mock_create_func.assert_has_calls(
            [
                call(db_alias='app_shard_001', sequence_name='global_id_sequence', shard_id=0),
            ]
        )

        mock_create_sequence.assert_has_calls(
            [
                call(db_alias='app_shard_001', reset_sequence=False, sequence_name='global_id_sequence'),
            ]
        )

    def test_specify_sequence_name(self):
        with patch(mock_verify_path, return_value=True) as mock_verify:
            with patch(mock_create_func_path) as mock_create_func:
                with patch(mock_create_sequence_path) as mock_create_sequence:
                    call_command('create_postgres_sequences', '--sequence-name=test_sequence_name')

        mock_verify.assert_has_calls(
            [
                call(db_alias='app_shard_001', function_name='next_sharded_id', sequence_name='test_sequence_name'),
                call(db_alias='app_shard_002', function_name='next_sharded_id', sequence_name='test_sequence_name')
            ]
        )

        mock_create_func.assert_has_calls(
            [
                call(db_alias='app_shard_001', sequence_name='test_sequence_name', shard_id=0),
                call(db_alias='app_shard_002', sequence_name='test_sequence_name', shard_id=1)
            ]
        )

        mock_create_sequence.assert_has_calls(
            [
                call(db_alias='app_shard_001', reset_sequence=False, sequence_name='test_sequence_name'),
                call(db_alias='app_shard_002', reset_sequence=False, sequence_name='test_sequence_name')
            ]
        )

    def test_dry_run(self):
        with patch(mock_verify_path, return_value=True) as mock_verify:
            with patch(mock_create_func_path) as mock_create_func:
                with patch(mock_create_sequence_path) as mock_create_sequence:
                    call_command('create_postgres_sequences', '--dry-run')

        mock_verify.assert_has_calls(
            [
                call(db_alias='app_shard_001', function_name='next_sharded_id', sequence_name='global_id_sequence'),
                call(db_alias='app_shard_002', function_name='next_sharded_id', sequence_name='global_id_sequence')
            ]
        )

        mock_create_func.assert_has_calls(
            []
        )

        mock_create_sequence.assert_has_calls(
            []
        )
