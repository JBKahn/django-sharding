from django.conf import settings
from django.test import TestCase

from django_sharding_library.sharding_functions import RoundRobinBucketingStrategy


class RoundRobinBucketingStrategyTestCase(TestCase):

    def test_picking_is_cyclic(self):
        class FakeUser():
            username = None

        expected_cycle = ['app_shard_001', 'app_shard_002']

        sut = RoundRobinBucketingStrategy(shard_group='default', databases=settings.DATABASES)
        resulting_shards = [sut.pick_shard(FakeUser()) for i in xrange(100)]

        self.assertEqual(len(set([resulting_shards[i] for i in xrange(0, 100, 2)])), 1)
        self.assertEqual(len(set([resulting_shards[i] for i in xrange(1, 100, 2)])), 1)

        resulting_cycled_shard = resulting_shards[:2]
        resulting_cycled_shard.sort()

        self.assertEqual(resulting_cycled_shard, expected_cycle)

    def test_shard_saved_to_user_when_used_with_model_and_signal(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username='username', password='pwassword', email='test@example.com')
        self.assertIsNotNone(user.shard)

    def test_shard_retrieve_shard_from_user_when_used_with_model_and_signal(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username='username', password='pwassword', email='test@example.com')
        sut = RoundRobinBucketingStrategy(shard_group='default', databases=settings.DATABASES)

        self.assertEqual(user.shard, sut.get_shard(user))
        self.assertIsNotNone(user.shard)

    def test_user_round_robin_when_used_with_model_and_signal(self):
        from django.contrib.auth import get_user_model
        user_one_shard = get_user_model().objects.create_user(username='username', password='pwassword', email='test@example.com').shard
        user_two_shard = get_user_model().objects.create_user(username='username1', password='pwassword', email='test1@example.com').shard
        user_three_shard = get_user_model().objects.create_user(username='username2', password='pwassword', email='test2@example.com').shard
        user_four_shard = get_user_model().objects.create_user(username='username3', password='pwassword', email='test3@example.com').shard

        self.assertIsNotNone(user_one_shard)
        self.assertIsNotNone(user_two_shard)
        self.assertEqual(user_one_shard, user_three_shard)
        self.assertEqual(user_two_shard, user_four_shard)
