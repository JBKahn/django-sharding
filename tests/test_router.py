from mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TransactionTestCase, override_settings

from tests.models import TestModel, ShardedTestModelIDs
from django_sharding_library.exceptions import InvalidMigrationException
from django_sharding_library.router import ShardedRouter
from django_sharding_library.routing_read_strategies import BaseRoutingStrategy


class FakeRoutingStrategy(BaseRoutingStrategy):
    """
    A fake router for testing that will always return
    the `testing` DB rather than an existing database.
    """
    def pick_read_db(self, primary_db_name):
        return 'testing'


class RouterReadTestCase(TransactionTestCase):
    databases = '__all__'

    def setUp(self):
        self.sut = ShardedRouter()
        self.user = get_user_model().objects.create_user(username='username', password='pwassword', email='test@example.com')

    def test_sharded_instance_uses_a_routing_read_strategies(self):
        item = TestModel.objects.using('app_shard_002').create(random_string=2, user_pk=self.user.pk)
        hints = {'instance': item}
        with patch.object(self.sut, 'get_read_db_routing_strategy') as mock_get_read_db_routing_strategy:
            mock_get_read_db_routing_strategy.return_value = FakeRoutingStrategy(settings.DATABASES)
            self.assertEqual(self.sut.db_for_read(model=TestModel, **hints), 'testing')

    def test_sharded_instance(self):
        item = TestModel.objects.using('app_shard_002').create(random_string=2, user_pk=self.user.pk)
        hints = {'instance': item}
        self.assertEqual(self.sut.db_for_read(model=TestModel, **hints), 'app_shard_002')

    def test_sharded_model(self):
        self.assertEqual(self.sut.db_for_read(model=TestModel), None)

    def test_specific_database(self):
        self.assertEqual(self.sut.db_for_read(model=ShardedTestModelIDs), 'app_shard_001')

    def test_specific_database_does_not_use_the_routing_read_strategy(self):
        with patch.object(self.sut, 'get_read_db_routing_strategy') as mock_get_read_db_routing_strategy:
            mock_get_read_db_routing_strategy.return_value = FakeRoutingStrategy(settings.DATABASES)
            self.assertEqual(self.sut.db_for_read(model=ShardedTestModelIDs), 'app_shard_001')

    def test_other(self):
        self.assertEqual(self.sut.db_for_read(model=get_user_model()), "default")


class RouterWriteTestCase(TransactionTestCase):
    databases = '__all__'

    def setUp(self):
        self.sut = ShardedRouter()
        self.user = get_user_model().objects.create_user(username='username', password='pwassword', email='test@example.com')

    def test_sharded_instance_does_not_use_a_routing_read_strategies(self):
        item = TestModel.objects.using('app_shard_002').create(random_string=2, user_pk=self.user.pk)
        hints = {'instance': item}
        with patch.object(self.sut, 'get_read_db_routing_strategy') as mock_get_read_db_routing_strategy:
            mock_get_read_db_routing_strategy.return_value = FakeRoutingStrategy(settings.DATABASES)
            self.assertEqual(self.sut.db_for_write(model=TestModel, **hints), 'app_shard_002')

    def test_sharded_instance(self):
        item = TestModel.objects.using('app_shard_002').create(random_string=2, user_pk=self.user.pk)
        hints = {'instance': item}
        self.assertEqual(self.sut.db_for_write(model=TestModel, **hints), 'app_shard_002')

    def test_sharded_model(self):
        self.assertEqual(self.sut.db_for_write(model=TestModel), None)

    def test_specific_database(self):
        self.assertEqual(self.sut.db_for_write(model=ShardedTestModelIDs), 'app_shard_001')

    def test_specific_database_does_not_use_the_routing_read_strategy(self):
        with patch.object(self.sut, 'get_read_db_routing_strategy') as mock_get_read_db_routing_strategy:
            mock_get_read_db_routing_strategy.return_value = FakeRoutingStrategy(settings.DATABASES)
            self.assertEqual(self.sut.db_for_write(model=ShardedTestModelIDs), 'app_shard_001')

    def test_other(self):
        self.assertEqual(self.sut.db_for_write(model=get_user_model()), "default")


class RouterAllowRelationTestCase(TransactionTestCase):
    databases = '__all__'

    def setUp(self):
        self.sut = ShardedRouter()
        self.user = get_user_model().objects.create_user(username='username', password='pwassword', email='test@example.com')

    def test_allow_relation_two_items_on_the_same_non_default_database(self):
        item_one = ShardedTestModelIDs.objects.create(stub=None)
        item_two = ShardedTestModelIDs.objects.create(stub=None)
        self.assertTrue(self.sut.allow_relation(item_one, item_two))

    def test_do_not_allow_relation_of_item_on_specific_database__and_non_sharded_non_specific_database_instances(self):
        item_one = ShardedTestModelIDs.objects.create(stub=None)
        self.assertFalse(self.sut.allow_relation(item_one, self.user))

    def test_do_not_allow_relation_of_sharded_models_on_different_shards(self):
        item_one = TestModel.objects.using('app_shard_002').create(random_string=2, user_pk=self.user.pk)
        item_two = TestModel.objects.using('app_shard_001').create(random_string=2, user_pk=self.user.pk)
        self.assertFalse(self.sut.allow_relation(item_one, item_two))

    def test_allow_relation_of_sharded_models_on_same_shard(self):
        item_one = TestModel.objects.using('app_shard_001').create(random_string=2, user_pk=self.user.pk)
        item_two = TestModel.objects.using('app_shard_001').create(random_string=2, user_pk=self.user.pk)
        self.assertTrue(self.sut.allow_relation(item_one, item_two))

    def test_allow_relation_of_sharded_instance_and_item_on_specific_db(self):
        item_one = TestModel.objects.using('app_shard_001').create(random_string=2, user_pk=self.user.pk)
        item_two = ShardedTestModelIDs.objects.create(stub=None)
        self.assertTrue(self.sut.allow_relation(item_one, item_two))

    def test_do_not_allow_relation_of_sharded_instance_and_item_on_specific_db_when_on_different_dbs(self):
        item_one = TestModel.objects.using('app_shard_002').create(random_string=2, user_pk=self.user.pk)
        item_two = ShardedTestModelIDs.objects.create(stub=None)
        self.assertFalse(self.sut.allow_relation(item_one, item_two))

    def test_do_not_allow_relation_of_sharded_instance_and_non_sharded_non_specific_database_instances(self):
        item_one = TestModel.objects.using('app_shard_001').create(random_string=2, user_pk=self.user.pk)
        self.assertFalse(self.sut.allow_relation(item_one, self.user))

    def test_allow_relation_of_items_on_default_database(self):
        item_one = Group.objects.create(name='test_group')
        self.assertTrue(self.sut.allow_relation(item_one, self.user))


class RouterAllowMigrateTestCase(TransactionTestCase):
    databases = '__all__'

    def setUp(self):
        self.sut = ShardedRouter()

    def assert_allow_migrate(self, app_label, model_name, can_migrate_default, can_migrate_shard, migratable_db=None):
        self.assertEqual(self.sut.allow_migrate(db='default', app_label=app_label, model_name=model_name), can_migrate_default)
        self.assertEqual(
            all([
                self.sut.allow_migrate(db='app_shard_001_replica_001', app_label=app_label, model_name=model_name),
                self.sut.allow_migrate(db='app_shard_001_replica_002', app_label=app_label, model_name=model_name),
            ]),
            False
        )
        self.assertEqual(
            all([
                self.sut.allow_migrate(db='app_shard_001', app_label=app_label, model_name=model_name),
                self.sut.allow_migrate(db='app_shard_002', app_label=app_label, model_name=model_name),
            ]),
            can_migrate_shard
        )
        if migratable_db:
            self.assertTrue(self.sut.allow_migrate(db=migratable_db, app_label=app_label, model_name=model_name))

    def test_model_name_passed_in(self):
        self.assertTrue(self.sut.allow_migrate(db='default', app_label='tests', model_name="User"))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001', app_label='tests', model_name="User"))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_002', app_label='tests', model_name="User"))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_001', app_label='tests', model_name="User"))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_002', app_label='tests', model_name="User"))

    def test_model_passed_in(self):

        hints = {'model': get_user_model()}

        self.assertTrue(self.sut.allow_migrate(db='default', app_label='tests', model_name=None, **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001', app_label='tests', model_name=None, **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_002', app_label='tests', model_name=None, **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_001', app_label='tests', model_name=None, **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_002', app_label='tests', model_name=None, **hints))

    def test_app_passed_in(self):
        self.assertTrue(self.sut.allow_migrate(db='default', app_label='tests'))
        self.assertTrue(self.sut.allow_migrate(db='app_shard_001', app_label='tests'))
        self.assertTrue(self.sut.allow_migrate(db='app_shard_002', app_label='tests'))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_001', app_label='tests'))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_002', app_label='tests'))

    def test_force_migrate_on_databases(self):
        hints = {"force_migrate_on_databases": ["app_shard_001"]}
        self.assertFalse(self.sut.allow_migrate(db='default', app_label='tests', **hints))
        self.assertTrue(self.sut.allow_migrate(db='app_shard_001', app_label='tests', **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_002', app_label='tests', **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_001', app_label='tests', **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_002', app_label='tests', **hints))

    def test_force_migrate_on_databases_ignores_secondary(self):
        hints = {"force_migrate_on_databases": ["app_shard_001_replica_001"]}
        self.assertFalse(self.sut.allow_migrate(db='default', app_label='tests', **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001', app_label='tests', **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_002', app_label='tests', **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_001', app_label='tests', **hints))
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_002', app_label='tests', **hints))

    def test_migrate_replica_will_not_work(self):
        self.assertFalse(self.sut.allow_migrate(db='app_shard_001_replica_001', app_label='tests', model_name='TestModel'))
        self.assertTrue(self.sut.allow_migrate(db='app_shard_001', app_label='tests', model_name='TestModel'))

    def test_migrate_sharded_model_with_specific_database_will_not_work(self):
        sut = ShardedRouter()

        with patch.object(TestModel, "django_sharding__database", 'blah', create=True):
            with patch.object(TestModel, "django_sharding__is_sharded", True, create=True):
                with self.assertRaises(InvalidMigrationException):
                    sut.allow_migrate(db='default', app_label='tests', model_name='TestModel')

        with patch.object(TestModel, "django_sharding__database", 'blah', create=True):
            with patch.object(TestModel, "django_sharding__is_sharded", False, create=True):
                sut.allow_migrate(db='default', app_label='tests', model_name='TestModel')

        with patch.object(TestModel, "django_sharding__database", None, create=True):
            with patch.object(TestModel, "django_sharding__is_sharded", True, create=True):
                sut.allow_migrate(db='default', app_label='tests', model_name='TestModel')

        sut.allow_migrate(db='default', app_label='tests', model_name='TestModel')

    def test_django_model_only_allows_on_default(self):
        self.assert_allow_migrate(
            app_label='auth',
            model_name='Group',
            can_migrate_default=True,
            can_migrate_shard=False
        )

    def test_specific_database_only_on_datbase(self):
        self.assert_allow_migrate(
            app_label='tests',
            model_name='ShardedTestModelIDs',
            can_migrate_default=False,
            can_migrate_shard=False,
            migratable_db='app_shard_001'
        )

    def test_specific_sharded_model_only_on_shards(self):
        self.assert_allow_migrate(
            app_label='tests',
            model_name='TestModel',
            can_migrate_default=False,
            can_migrate_shard=True,
        )

    def test_lookup_fallback_if_migration_directory_not_the_same_as_the_model(self):
        self.assert_allow_migrate(
            app_label='tests',
            model_name='auth.User',
            can_migrate_default=True,
            can_migrate_shard=False,
        )

    @override_settings(DJANGO_SHARDING_SETTINGS={"DELETED_MODELS": {"deleted.Whatever": {"database": "app_shard_002"}}})
    def test_deleted_model_in_settings__specific_database(self):
        self.assertFalse(self.sut.allow_migrate(model_name="deleted.Whatever", db='default', app_label='deleted', **{}))
        self.assertTrue(self.sut.allow_migrate(model_name="deleted.Whatever", db='app_shard_002', app_label='deleted', **{}))

        self.assertFalse(self.sut.allow_migrate(model_name="Whatever", db='default', app_label='deleted', **{}))
        self.assertTrue(self.sut.allow_migrate(model_name="Whatever", db='app_shard_002', app_label='deleted', **{}))

    @override_settings(DJANGO_SHARDING_SETTINGS={"DELETED_MODELS": {"deleted.Whatever": {"shard_group": "default"}}})
    def test_deleted_model_in_settings__shard_group(self):
        self.assertFalse(self.sut.allow_migrate(model_name="deleted.Whatever", db='default', app_label='deleted', **{}))
        self.assertTrue(self.sut.allow_migrate(model_name="deleted.Whatever", db='app_shard_001', app_label='deleted', **{}))
        self.assertTrue(self.sut.allow_migrate(model_name="deleted.Whatever", db='app_shard_002', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="deleted.Whatever", db='app_shard_001_replica_001', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="deleted.Whatever", db='app_shard_001_replica_002', app_label='deleted', **{}))

        self.assertFalse(self.sut.allow_migrate(model_name="Whatever", db='default', app_label='deleted', **{}))
        self.assertTrue(self.sut.allow_migrate(model_name="Whatever", db='app_shard_001', app_label='deleted', **{}))
        self.assertTrue(self.sut.allow_migrate(model_name="Whatever", db='app_shard_002', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="Whatever", db='app_shard_001_replica_001', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="Whatever", db='app_shard_001_replica_002', app_label='deleted', **{}))

    @override_settings(DJANGO_SHARDING_SETTINGS={"DELETED_MODELS": {"deleted.Whatever": None}})
    def test_deleted_model_in_settings__unsharded(self):
        self.assertTrue(self.sut.allow_migrate(model_name="deleted.Whatever", db='default', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="deleted.Whatever", db='app_shard_001', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="deleted.Whatever", db='app_shard_002', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="deleted.Whatever", db='app_shard_001_replica_001', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="deleted.Whatever", db='app_shard_001_replica_002', app_label='deleted', **{}))

        self.assertTrue(self.sut.allow_migrate(model_name="Whatever", db='default', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="Whatever", db='app_shard_001', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="Whatever", db='app_shard_002', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="Whatever", db='app_shard_001_replica_001', app_label='deleted', **{}))
        self.assertFalse(self.sut.allow_migrate(model_name="Whatever", db='app_shard_001_replica_002', app_label='deleted', **{}))
