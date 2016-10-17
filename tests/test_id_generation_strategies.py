from random import choice
from uuid import UUID

from django.conf import settings
from django.test import TestCase
from django.utils.six.moves import xrange

from tests.models import ShardedModelIDs
from django_sharding_library.id_generation_strategies import TableStrategy, UUIDStrategy


class TableStrategyIDGenerationTestCase(TestCase):

    def test_returns_unique_values(self):
        sut = TableStrategy('tests.ShardedModelIDs')
        ids = [sut.get_next_id() for i in xrange(100)]
        self.assertEqual(ids, list(set(ids)))

    def test_largest_value_stored_in_db(self):
        sut = TableStrategy('tests.ShardedModelIDs')
        for i in xrange(100):
            id = sut.get_next_id()
            self.assertEqual(ShardedModelIDs.objects.latest('pk').pk, id)
            self.assertFalse(ShardedModelIDs.objects.filter(pk__gt=id).exists())


class UUIDStrategyTestCase(TestCase):

    def test_uuid_strategy_must_be_passed_a_database(self):
        sut = UUIDStrategy()
        with self.assertRaises(AssertionError):
            sut.get_next_id('im not a database')

    def test_returns_value_with_db_name_and_uuid(self):
        sut = UUIDStrategy()
        for i in xrange(100):
            database = choice(list(settings.DATABASES.keys()))
            id = sut.get_next_id(database)
            self.assertTrue(id.startswith(database))
            uuid_value = id[len(database) + 1:]
            self.assertEqual(str(UUID(uuid_value, version=4)), uuid_value)
