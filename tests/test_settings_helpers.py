from dj_database_url import config

from django.test import TestCase

from django_sharding_library.settings_helpers import database_config, database_configs


class DatabaseConfigTestCase(TestCase):

    def setUp(self):
        self.default_database_url = 'postgres://user:pass@localhost/test_db'
        self.dj_database_config = config(env='TEST_ENV_VAR', default=self.default_database_url)

    def test_returns_none_when_no_env_var_and_no_url(self):
        result = database_config(environment_variable='TEST_ENV_VAR', default_database_url=None, shard_group='default')
        expected_result = {}
        self.assertEqual(result, expected_result)

    def test_no_extra_args_equivalent_to_dj_database_with_non_shard_status_added(self):
        result = database_config(environment_variable='TEST_ENV_VAR', default_database_url=self.default_database_url)
        expected_result = {'SHARD_GROUP': None, 'TEST': {}}
        expected_result.update(self.dj_database_config)
        self.assertEqual(result, expected_result)

    def test_adds_sharded_state_to_dict_when_sharded(self):
        result = database_config(environment_variable='TEST_ENV_VAR', default_database_url=self.default_database_url, shard_group='default')
        expected_result = {'SHARD_GROUP': 'default', 'TEST': {}}
        expected_result.update(self.dj_database_config)
        self.assertEqual(result, expected_result)

    def test_adds_replica_state_to_dict(self):
        result = database_config(environment_variable='TEST_ENV_VAR', default_database_url=self.default_database_url, is_replica_of='some_database')
        expected_result = {'PRIMARY': 'some_database', 'SHARD_GROUP': None, 'TEST': {'MIRROR': 'some_database'}}
        expected_result.update(self.dj_database_config)
        self.assertEqual(result, expected_result)

    def test_adds_replica_state_to_dict_also_when_sharded(self):
        result = database_config(environment_variable='TEST_ENV_VAR', default_database_url=self.default_database_url, shard_group='default_set_of_shards', is_replica_of='some_database')
        expected_result = {'PRIMARY': 'some_database', 'SHARD_GROUP': 'default_set_of_shards', 'TEST': {'MIRROR': 'some_database'}}
        expected_result.update(self.dj_database_config)
        self.assertEqual(result, expected_result)


class DatabaseConfigsTestCase(TestCase):

    def setUp(self):
        self.default_database_url = 'postgres://user:pass@localhost/test_db'
        self.dj_database_config = config(env='TEST_ENV_VAR', default=self.default_database_url)

    def test_skips_databases_with_no_envvar_value_or_deafult_url(self):

        simple_config = {
            'unsharded_databases': [
                {
                    'name': 'DB01',
                    'environment_variable': 'ENV',
                    'default_database_url': ''
                }
            ]
        }
        result = database_configs(simple_config)
        expected_result = {}
        self.assertEqual(result, expected_result)

    def test_databases_with_envvar_value_and_no_default_url(self):
        import os
        os.environ['SOME_USELESS_ENV'] = self.default_database_url

        simple_config = {
            'unsharded_databases': [
                {
                    'name': 'DB01',
                    'environment_variable': 'SOME_USELESS_ENV',
                    'default_database_url': ''
                }
            ]
        }
        result = database_configs(simple_config)
        del os.environ['SOME_USELESS_ENV']

        DB01 = {'SHARD_GROUP': None, 'TEST': {}}
        DB01.update(self.dj_database_config)

        self.assertEqual(result, {'DB01': DB01})

    def test_databases_with_default_url_unset_env(self):
        simple_config = {
            'unsharded_databases': [
                {
                    'name': 'DB01',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url
                }
            ]
        }
        result = database_configs(simple_config)

        DB01 = {'SHARD_GROUP': None, 'TEST': {}}
        DB01.update(self.dj_database_config)

        self.assertEqual(result, {'DB01': DB01})

    def test_unsharded_databases_ignore_shard_group(self):
        simple_config = {
            'unsharded_databases': [
                {
                    'name': 'DB01',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url,
                    'shard_group': 'testing'
                }
            ]
        }
        result = database_configs(simple_config)

        DB01 = {'SHARD_GROUP': None, 'TEST': {}}
        DB01.update(self.dj_database_config)

        self.assertEqual(result, {'DB01': DB01})

    def test_sharded_databases_default_shard_group(self):
        simple_config = {
            'sharded_databases': [
                {
                    'name': 'DB01',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url,
                }
            ]
        }
        result = database_configs(simple_config)

        DB01 = {'SHARD_GROUP': 'default', 'TEST': {}, 'SHARD_ID': 0}
        DB01.update(self.dj_database_config)

        self.assertEqual(result, {'DB01': DB01})

    def test_sharded_databases_shard_group(self):
        simple_config = {
            'sharded_databases': [
                {
                    'name': 'DB01',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url,
                    'shard_group': 'testing'
                }
            ]
        }
        result = database_configs(simple_config)

        DB01 = {'SHARD_GROUP': 'testing', 'TEST': {}, 'SHARD_ID': 0}
        DB01.update(self.dj_database_config)

        self.assertEqual(result, {'DB01': DB01})

    def test_sharded_databases_shard_id(self):
        simple_config = {
            'sharded_databases': [
                {
                    'name': 'DB01',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url,
                    'shard_group': 'testing'
                },
                {
                    'name': 'DB02',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url,
                    'shard_group': 'testing'
                },
                {
                    'name': 'DB03',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url,
                    'shard_group': 'default'
                },
                {
                    'name': 'DB04',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url,
                    'shard_group': 'default'
                },
                {
                    'name': 'DB05',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url,
                    'shard_group': 'default'
                }
            ]
        }
        result = database_configs(simple_config)

        DB01 = {'SHARD_GROUP': 'testing', 'TEST': {}, 'SHARD_ID': 0}
        DB02 = {'SHARD_GROUP': 'testing', 'TEST': {}, 'SHARD_ID': 1}
        DB03 = {'SHARD_GROUP': 'default', 'TEST': {}, 'SHARD_ID': 0}
        DB04 = {'SHARD_GROUP': 'default', 'TEST': {}, 'SHARD_ID': 1}
        DB05 = {'SHARD_GROUP': 'default', 'TEST': {}, 'SHARD_ID': 2}
        DB01.update(self.dj_database_config)
        DB02.update(self.dj_database_config)
        DB03.update(self.dj_database_config)
        DB04.update(self.dj_database_config)
        DB05.update(self.dj_database_config)

        self.assertEqual(result['DB01'], DB01)
        self.assertEqual(result['DB02'], DB02)
        self.assertEqual(result['DB03'], DB03)
        self.assertEqual(result['DB04'], DB04)
        self.assertEqual(result['DB05'], DB05)

    def test_unsharded_replica_database(self):
        simple_config = {
            'unsharded_databases': [
                {
                    'name': 'DB01',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url,
                    'replicas': [{
                        'name': 'DB01_replica',
                        'environment_variable': 'SOME_OTHER_USELESS_ENV',
                        'default_database_url': self.default_database_url,
                    }]
                }
            ]
        }
        result = database_configs(simple_config)

        DB01 = {'SHARD_GROUP': None, 'TEST': {}}
        DB01.update(self.dj_database_config)
        DB01_replica = {'SHARD_GROUP': None, 'PRIMARY': 'DB01', 'TEST': {'MIRROR': 'DB01'}}
        DB01_replica.update(self.dj_database_config)

        self.assertEqual(result, {'DB01': DB01, 'DB01_replica': DB01_replica})

    def test_sharded_replica_database(self):
        simple_config = {
            'sharded_databases': [
                {
                    'name': 'DB01',
                    'environment_variable': 'SOME_OTHER_USELESS_ENV',
                    'default_database_url': self.default_database_url,
                    'shard_group': 'testing',
                    'replicas': [{
                        'name': 'DB01_replica',
                        'environment_variable': 'SOME_OTHER_USELESS_ENV',
                        'default_database_url': self.default_database_url,
                    }]
                }
            ]
        }
        result = database_configs(simple_config)

        DB01 = {'SHARD_GROUP': 'testing', 'TEST': {}, 'SHARD_ID': 0}
        DB01.update(self.dj_database_config)
        DB01_replica = {'SHARD_GROUP': 'testing', 'PRIMARY': 'DB01', 'TEST': {'MIRROR': 'DB01'}}
        DB01_replica.update(self.dj_database_config)

        self.assertEqual(result, {'DB01': DB01, 'DB01_replica': DB01_replica})
