from mock import patch

from django.conf import settings
from django.db.utils import DataError, IntegrityError
from django.test import TestCase

from django_sharding_library.constants import Backends
from django_sharding_library.fields import ShardedIDFieldMixin, ShardLocalStorageFieldMixin, ShardStorageFieldMixin, ShardForeignKeyStorageFieldMixin, ShardForeignKeyStorageField
from django_sharding_library.id_generation_strategies import BaseIDGenerationStrategy
from tests.models import ShardedModelIDs, ShardedTestModelIDs, TestModel, ShardStorageTable


class BigAutoFieldTestCase(TestCase):
    def test_largest_id(self):
        if settings.DATABASES['default']['ENGINE'] == Backends.POSTGRES:
            max_id = 9223372036854775807
        else:
            max_id = 18446744073709551615

        item = ShardedModelIDs.objects.create(id=max_id, stub=None)
        self.assertEqual(item.pk, max_id)
        try:
            ShardedModelIDs.objects.create(id=max_id + 1, stub=None)
        except (DataError, OverflowError, IntegrityError):
            pass
        else:
            raise Exception('Field was able to hold an integer as large as {}.'.format(max_id + 1))


class FakeIDGenerationStrategy(BaseIDGenerationStrategy):
    def __init__(self):
        self.call_count = 0
        self.id = 0

    def get_next_id(self):
        self.call_count += 1
        self.id += 1
        return self.id


class TableShardedIDFieldTestCase(TestCase):
    def test_largest_id(self):
        if settings.DATABASES['app_shard_001']['ENGINE'] == Backends.POSTGRES:
            max_id = 9223372036854775807
        else:
            max_id = 18446744073709551615

        item = TestModel.objects.using('app_shard_001').create(id=max_id, user_pk=1)
        self.assertEqual(item.pk, max_id)
        try:
            TestModel.objects.using('app_shard_001').create(id=max_id + 1, user_pk=1)
        except (DataError, OverflowError, IntegrityError):
            pass
        else:
            raise Exception('Field was able to hold an integer as large as {}.'.format(max_id + 1))

    def test_get_pk_value_on_save_calls_strategy_get_next_id(self):
        for i in xrange(100):
            instance = TestModel.objects.using('app_shard_001').create(user_pk=1)
            self.assertEqual(ShardedTestModelIDs.objects.using('app_shard_001').latest('pk').pk, instance.pk)


class TableShardedIDMixinTestCase(TestCase):
    def test_initialization_makes_id_generation_available(self):
        field = ShardedIDFieldMixin(strategy=FakeIDGenerationStrategy())
        self.assertTrue(hasattr(field.strategy, 'get_next_id'))

    def test_uses_get_next_id_in_get_pk_value_on_save(self):
        class FakeModel(object):
            pk = None

        field = ShardedIDFieldMixin(strategy=FakeIDGenerationStrategy())
        for i in xrange(1, 100):
            self.assertEqual(field.get_pk_value_on_save(FakeModel()), i)
        self.assertEqual(field.strategy.id, 99)
        self.assertEqual(field.strategy.call_count, 99)


class ShardStorageFieldMixinTestCase(TestCase):
    def test_takes_shard_group_and_sets_attributes(self):
        sut = ShardStorageFieldMixin(shard_group='testing')
        self.assertEqual(sut.django_sharding__shard_group, 'testing')
        self.assertEqual(sut.django_sharding__stores_shard, True)
        self.assertFalse(hasattr(sut, 'django_sharding__use_signal'))


class ShardLocalStorageFieldMixinTestCase(TestCase):
    def test_takes_shard_group_and_sets_attributes(self):
        sut = ShardLocalStorageFieldMixin(shard_group='testing')
        self.assertEqual(sut.django_sharding__shard_group, 'testing')
        self.assertEqual(sut.django_sharding__stores_shard, True)
        self.assertEqual(sut.django_sharding__use_signal, True)


class ShardForeignKeyStorageFieldMixinTestCase(TestCase):
    def test_save_shard_works(self):
        initial_count = ShardStorageTable.objects.count()

        class FakeField(ShardForeignKeyStorageFieldMixin):
            def __init__(self, *args, **kwargs):
                self.name = 'shard_field'
                self.django_sharding__shard_storage_table = ShardStorageTable
                self.django_sharding__shard_group = 'default'

        class FakeModel(object):
            def __init__(self, shard_key):
                self.shard_key = shard_key
                self.shard_field = None

            def get_shard_key(self):
                return self.shard_key

        sut = FakeField(to=ShardStorageTable, shard_group='default')
        model = FakeModel('testing_save_shard')
        sut.save_shard(model)

        latest_entry_in_storage_table = ShardStorageTable.objects.latest('pk')
        self.assertEqual(model.shard_field, latest_entry_in_storage_table)
        self.assertEqual(ShardStorageTable.objects.count(), initial_count + 1)
        self.assertTrue(ShardStorageTable.objects.filter(shard_key='testing_save_shard'))
        self.assertTrue(latest_entry_in_storage_table.shard in settings.DATABASES)

    def test_save_shard_works_when_model_specified_by_string(self):
        initial_count = ShardStorageTable.objects.count()

        class FakeField(ShardForeignKeyStorageFieldMixin):
            def __init__(self, *args, **kwargs):
                self.name = 'shard_field'
                self.django_sharding__shard_storage_table = ShardStorageTable
                self.django_sharding__shard_group = 'default'

        class FakeModel(object):
            def __init__(self, shard_key):
                self.shard_key = shard_key
                self.shard_field = None

            def get_shard_key(self):
                return self.shard_key

        sut = FakeField(to='tests.ShardStorageTable', shard_group='default')
        model = FakeModel('testing_save_shard')
        sut.save_shard(model)

        latest_entry_in_storage_table = ShardStorageTable.objects.latest('pk')
        self.assertEqual(model.shard_field, latest_entry_in_storage_table)
        self.assertEqual(ShardStorageTable.objects.count(), initial_count + 1)
        self.assertTrue(ShardStorageTable.objects.filter(shard_key='testing_save_shard'))
        self.assertTrue(latest_entry_in_storage_table.shard in settings.DATABASES)
    def test_save_shard_works(self):
        initial_count = ShardStorageTable.objects.count()

        class FakeField(ShardForeignKeyStorageFieldMixin):
            def __init__(self, *args, **kwargs):
                self.name = 'shard_field'
                self.django_sharding__shard_storage_table = ShardStorageTable
                self.django_sharding__shard_group = 'default'

        class FakeModel(object):
            def __init__(self, shard_key):
                self.shard_key = shard_key
                self.shard_field = None

            def get_shard_key(self):
                return self.shard_key

        sut = FakeField(to=ShardStorageTable, shard_group='default')
        model = FakeModel('testing_save_shard')
        sut.save_shard(model)

        latest_entry_in_storage_table = ShardStorageTable.objects.latest('pk')
        self.assertEqual(model.shard_field, latest_entry_in_storage_table)
        self.assertEqual(ShardStorageTable.objects.count(), initial_count + 1)
        self.assertTrue(ShardStorageTable.objects.filter(shard_key='testing_save_shard'))
        self.assertTrue(latest_entry_in_storage_table.shard in settings.DATABASES)


class ShardForeignKeyStorageFieldTestCase(TestCase):
    def test_pre_save_calls_save_shard(self):
        sut = ShardForeignKeyStorageField(ShardStorageTable, shard_group='default')
        model_instance = object()
        with patch.object(sut, 'save_shard') as mock_save_shard:
            with self.assertRaises(Exception):
                sut.pre_save(model_instance, False)

        mock_save_shard.assert_called_once_with(model_instance)
