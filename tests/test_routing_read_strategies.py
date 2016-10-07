from django.conf import settings
from django.test import TestCase

from django_sharding_library.routing_read_strategies import RoundRobinRoutingStrategy, PrimaryOnlyRoutingStrategy


class RoundRobinBucketingStrategyTestCase(TestCase):

    def test_is_cyclic(self):
        sut = RoundRobinRoutingStrategy(settings.DATABASES)
        expected_cycled_shards = ['app_shard_001_replica_001', 'app_shard_001_replica_002', 'app_shard_001']
        expected_cycled_shards.sort()

        resulting_shards = [sut.pick_read_db('app_shard_001') for i in xrange(150)]

        self.assertEqual(len(set([resulting_shards[i] for i in xrange(0, 150, 3)])), 1)
        self.assertEqual(len(set([resulting_shards[i] for i in xrange(1, 150, 3)])), 1)
        self.assertEqual(len(set([resulting_shards[i] for i in xrange(2, 150, 3)])), 1)

        resulting_cycled_shard = resulting_shards[:3]
        resulting_cycled_shard.sort()

        self.assertEqual(expected_cycled_shards, resulting_cycled_shard)


class MasterOnlyRoutingStrategyTestCase(TestCase):

    def test_is_always_primary(self):
        sut = PrimaryOnlyRoutingStrategy(settings.DATABASES)
        expected_shards = ['app_shard_001'] * 150

        resulting_shards = [sut.pick_read_db('app_shard_001') for i in xrange(150)]
        self.assertEqual(expected_shards, resulting_shards)


class RandomRoutingStrategyTestCase(TestCase):

    def test_no_exception_raised(self):
        sut = RoundRobinRoutingStrategy(settings.DATABASES)
        [sut.pick_read_db('app_shard_001') for i in xrange(150)]
