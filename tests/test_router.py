from mock import call, patch
import unittest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TransactionTestCase

from tests.models import TestModel, ShardedTestModelIDs, PostgresCustomAutoIDModel, PostgresShardUser
from django_sharding_library.exceptions import InvalidMigrationException
from django_sharding_library.router import ShardedRouter
from django_sharding_library.routing_read_strategies import BaseRoutingStrategy
from django_sharding_library.fields import PostgresShardGeneratedIDAutoField
from django_sharding_library.constants import Backends
from django_sharding_library.manager import ShardManager

from django.db.models import Sum, Q


class FakeRoutingStrategy(BaseRoutingStrategy):
    """
    A fake router for testing that will always return
    the `testing` DB rather than an existing database.
    """
    def pick_read_db(self, primary_db_name):
        return 'testing'


class RouterReadTestCase(TransactionTestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
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
        from django.contrib.auth import get_user_model
        self.assertEqual(self.sut.db_for_read(model=get_user_model()), "default")

    def test_router_hints_receives_get_kwargs(self):
        original_id = TestModel.objects.create(user_pk=self.user.pk).id

        lookups_to_find = {'exact_lookups': {'user_pk': self.user.pk}}

        with patch.object(ShardedRouter, 'db_for_write', wraps=self.sut.db_for_write) as write_route_function:
            with patch.object(ShardedRouter, 'db_for_read', wraps=self.sut.db_for_read) as read_route_function:
                result = TestModel.objects.get(user_pk=self.user.pk)

        self.assertEqual(result.id, original_id)
        self.assertEqual(
            [call(TestModel, **lookups_to_find), call(get_user_model())],
            read_route_function.mock_calls
        )
        self.assertEqual(
            [],
            write_route_function.mock_calls
        )

    def test_router_hints_receives_get_kwargs_on_get_or_create__get(self):
        original_id = TestModel.objects.create(user_pk=self.user.pk).id

        lookups_to_find = {'exact_lookups': {'user_pk': self.user.pk}}

        with patch.object(ShardedRouter, 'db_for_write', wraps=self.sut.db_for_write) as write_route_function:
            with patch.object(ShardedRouter, 'db_for_read', wraps=self.sut.db_for_read) as read_route_function:
                result, created = TestModel.objects.get_or_create(user_pk=self.user.pk)

        self.assertEqual(result.id, original_id)
        self.assertFalse(created)
        self.assertEqual(
            [call(get_user_model())],
            read_route_function.mock_calls
        )

        self.assertEqual(
            [
                call(TestModel, **lookups_to_find),
            ],
            write_route_function.mock_calls
        )

    def test_router_hints_receives_get_kwargs_on_get_or_create__create(self):
        lookups_to_find = {'exact_lookups': {'user_pk': self.user.pk}}

        with patch.object(ShardedRouter, 'db_for_write', wraps=self.sut.db_for_write) as write_route_function:
            with patch.object(ShardedRouter, 'db_for_read', wraps=self.sut.db_for_read) as read_route_function:

                _, created = TestModel.objects.get_or_create(user_pk=self.user.pk)

        self.assertTrue(created)
        self.assertEqual(
            [call(get_user_model()), call(get_user_model()), call(get_user_model())],
            read_route_function.mock_calls
        )

        self.assertEqual(
            [
                call(TestModel, **lookups_to_find),
                call(TestModel, **lookups_to_find),
                call(TestModel, instance=write_route_function.mock_calls[2][2]["instance"], **lookups_to_find),  # no way to access that copy of the instance here, the one prior to saving.
                call(ShardedTestModelIDs),
            ],
            write_route_function.mock_calls
        )

    def test_router_hints_receives_get_kwargs_on_update_or_create__get(self):
        original_id = TestModel.objects.create(user_pk=self.user.pk).id

        lookups_to_find = {'exact_lookups': {'user_pk': self.user.pk}}

        with patch.object(ShardedRouter, 'db_for_read', wraps=self.sut.db_for_read) as read_route_function:
            with patch.object(ShardedRouter, 'db_for_write', wraps=self.sut.db_for_write) as write_route_function:

                result, created = TestModel.objects.update_or_create(user_pk=self.user.pk)

        self.assertEqual(result.id, original_id)
        self.assertFalse(created)

        # Django 1.10 dropped a call for each here :)
        import django
        if django.VERSION < (1, 10):
            self.assertEqual(
                [call(get_user_model()), call(get_user_model()), call(get_user_model())],
                read_route_function.mock_calls
            )
            self.assertEqual(
                [call(TestModel, **lookups_to_find), call(TestModel, **lookups_to_find), call(TestModel, **lookups_to_find)],
                write_route_function.mock_calls
            )

        else:
            self.assertEqual(
                [call(get_user_model()), call(get_user_model())],
                read_route_function.mock_calls
            )

            self.assertEqual(
                [call(TestModel, **lookups_to_find), call(TestModel, **lookups_to_find)],
                write_route_function.mock_calls
            )

    def test_router_hints_receives_get_kwargs_on_update_or_create__create(self):
        lookups_to_find = {'exact_lookups': {'user_pk': self.user.pk}}

        with patch.object(ShardedRouter, 'db_for_read', wraps=self.sut.db_for_read) as read_route_function:
            with patch.object(ShardedRouter, 'db_for_write', wraps=self.sut.db_for_write) as write_route_function:

                instance, created = TestModel.objects.update_or_create(user_pk=self.user.pk)

        self.assertTrue(created)
        self.assertEqual(
            [call(get_user_model()), call(get_user_model()), call(get_user_model())],
            read_route_function.mock_calls
        )

        self.assertEqual(
            [
                call(TestModel, **lookups_to_find),
                call(TestModel, **lookups_to_find),
                call(TestModel, instance=write_route_function.mock_calls[2][2]["instance"], **lookups_to_find),  # no way to access that copy of the instance here, the one prior to saving.
                call(ShardedTestModelIDs),
            ],
            write_route_function.mock_calls
        )

    def test_router_hints_receives_filter_kwargs_on_count(self):
        TestModel.objects.create(user_pk=self.user.pk)

        lookups_to_find = {'exact_lookups': {'user_pk': self.user.pk}}

        with patch.object(ShardedRouter, 'db_for_write', wraps=self.sut.db_for_write) as write_route_function:
            with patch.object(ShardedRouter, 'db_for_read', wraps=self.sut.db_for_read) as read_route_function:
                result = TestModel.objects.filter(user_pk=self.user.pk).count()

        self.assertEqual(result, 1)
        self.assertEqual(
            [call(TestModel, **lookups_to_find), call(get_user_model())],
            read_route_function.mock_calls
        )
        self.assertEqual(
            [],
            write_route_function.mock_calls
        )

    def test_router_hints_receives_filter_kwargs_on_exists(self):
        TestModel.objects.create(user_pk=self.user.pk)

        lookups_to_find = {'exact_lookups': {'user_pk': self.user.pk}}

        with patch.object(ShardedRouter, 'db_for_write', wraps=self.sut.db_for_write) as write_route_function:
            with patch.object(ShardedRouter, 'db_for_read', wraps=self.sut.db_for_read) as read_route_function:
                result = TestModel.objects.filter(user_pk=self.user.pk).exists()

        self.assertTrue(result)
        self.assertEqual(
            [call(TestModel, **lookups_to_find), call(get_user_model())],
            read_route_function.mock_calls
        )
        self.assertEqual(
            [],
            write_route_function.mock_calls
        )

    def test_router_hints_receives_filter_kwargs(self):
        TestModel.objects.create(user_pk=self.user.pk)

        lookups_to_find = {'exact_lookups': {'user_pk': self.user.pk}}

        with patch.object(ShardedRouter, 'db_for_write', wraps=self.sut.db_for_write) as write_route_function:
            with patch.object(ShardedRouter, 'db_for_read', wraps=self.sut.db_for_read) as read_route_function:
                list(TestModel.objects.filter(user_pk=self.user.pk))

        self.assertEqual(
            [call(TestModel, **lookups_to_find), call(get_user_model())],
            read_route_function.mock_calls
        )
        self.assertEqual(
            [],
            write_route_function.mock_calls
        )

    def test_router_gets_hints_correctly_with_positional_arguments_like_Q_in_filter(self):
        TestModel.objects.create(user_pk=self.user.pk, random_string="test")

        lookups_to_find = {'exact_lookups': {'user_pk': self.user.pk}}

        with patch.object(ShardedRouter, 'db_for_write', wraps=self.sut.db_for_write) as write_route_function:
            with patch.object(ShardedRouter, 'db_for_read', wraps=self.sut.db_for_read) as read_route_function:
                list(TestModel.objects.filter(Q(random_string="test") | Q(random_string__isnull=True), user_pk=self.user.pk))

        self.assertEqual(
            [call(TestModel, **lookups_to_find), call(get_user_model())],
            read_route_function.mock_calls
        )
        self.assertEqual(
            [],
            write_route_function.mock_calls
        )

    def test_router_gets_hints_correctly_with_positional_arguments_like_Q_in_get(self):
        TestModel.objects.create(user_pk=self.user.pk, random_string="test")

        lookups_to_find = {'exact_lookups': {'user_pk': self.user.pk}}

        with patch.object(ShardedRouter, 'db_for_write', wraps=self.sut.db_for_write) as write_route_function:
            with patch.object(ShardedRouter, 'db_for_read', wraps=self.sut.db_for_read) as read_route_function:
                TestModel.objects.get(Q(random_string="test") | Q(random_string__isnull=True), user_pk=self.user.pk)

        self.assertEqual(
            [call(TestModel, **lookups_to_find), call(get_user_model())],
            read_route_function.mock_calls
        )
        self.assertEqual(
            [],
            write_route_function.mock_calls
        )

    def test_queryset_router_filter_returns_existing_objects(self):
        for i in range(1, 11):
            test_model_obj = TestModel.objects.create(user_pk=self.user.pk, random_string="%s" % i)
            self.assertIn(test_model_obj._state.db, ['app_shard_001', 'app_shard_002'])

        test_models = TestModel.objects.filter(user_pk=self.user.pk)
        self.assertEqual(len(test_models), 10)

        from django.contrib.auth import get_user_model
        new_user = get_user_model().objects.create_user(username='username2', password='pwassword', email='test2@example.com')
        for i in range(1, 21):
            TestModel.objects.create(user_pk=new_user.pk, random_string="%s" % i)

        test_models = TestModel.objects.filter(user_pk=new_user.pk)
        self.assertEqual(len(test_models), 20)

    def test_queryset_router_filter_with_aggregates(self):
        for i in range(1, 11):
            TestModel.objects.create(user_pk=self.user.pk, random_string="%s" % i)
        num_models = TestModel.objects.filter(user_pk=self.user.pk).count()
        self.assertEqual(num_models, 10)

        sum_model_pk = TestModel.objects.filter(user_pk=self.user.pk).aggregate(user_pk_sum=Sum('user_pk'))
        self.assertEqual(sum_model_pk['user_pk_sum'], self.user.pk * 10)


class RouterWriteTestCase(TransactionTestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
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
        from django.contrib.auth import get_user_model
        self.assertEqual(self.sut.db_for_write(model=get_user_model()), "default")

    def test_create_sharded_object_without_using(self):
        instance = TestModel.objects.create(user_pk=self.user.pk)
        self.assertEqual(instance._state.db, self.user.shard)
        self.assertTrue(TestModel.objects.using(self.user.shard).get(id=instance.id))


class RouterAllowRelationTestCase(TransactionTestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model
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
        from django.contrib.auth import get_user_model

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


class RouterForPostgresIDFieldTest(TransactionTestCase):

    def setUp(self):
        self.sut = ShardedRouter()
        self.user = PostgresShardUser.objects.create_user(username='username', password='pwassword', email='test@example.com')

    @unittest.skipIf(settings.DATABASES['default']['ENGINE'] not in Backends.POSTGRES, "Not a postgres backend")
    def test_postgres_sharded_id_can_be_queried_without_using_and_without_sharded_by(self):
        created_model = PostgresCustomAutoIDModel.objects.create(random_string='Test String', user_pk=self.user.id)
        self.assertTrue(getattr(created_model, 'id'))

        self.assertTrue(isinstance(PostgresCustomAutoIDModel._meta.pk, PostgresShardGeneratedIDAutoField))

        self.assertTrue(isinstance(PostgresCustomAutoIDModel.objects, ShardManager))

        instance = PostgresCustomAutoIDModel.objects.get(id=created_model.id)
        self.assertEqual(created_model._state.db, instance._state.db)

        instance = PostgresCustomAutoIDModel.objects.get(pk=created_model.id)
        self.assertEqual(created_model._state.db, instance._state.db)

    @unittest.skipIf(settings.DATABASES['default']['ENGINE'] not in Backends.POSTGRES, "Not a postgres backend")
    def test_shard_extracted_correctly(self):
        created_model = PostgresCustomAutoIDModel.objects.create(random_string='Test String', user_pk=self.user.pk)
        self.assertEqual(self.user.shard, self.sut.get_shard_for_postgres_pk_field(PostgresCustomAutoIDModel, created_model.id))
