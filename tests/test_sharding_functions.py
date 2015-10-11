from mock import Mock

from django.conf import settings
from django.test import TestCase

from django_sharding_library.sharding_functions import (
    BaseBucketingStrategy,
    BaseShardedModelBucketingStrategy,
    RandomBucketingStrategy,
    RoundRobinBucketingStrategy,
    ModBucketingStrategy,
    SavedModBucketingStrategy
)


class BaseBucketingStrategyTestCase(TestCase):

    def test_get_shards(self):
        sut = BaseBucketingStrategy(shard_group='default')
        result = sut.get_shards(settings.DATABASES)
        expected_result = ['app_shard_001', 'app_shard_002']

        self.assertEqual(sorted(result), expected_result)

    def test_pick_shard_method_defined_but_unimplimented(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        sut = BaseBucketingStrategy(shard_group='default')
        with self.assertRaises(NotImplementedError):
            sut.pick_shard(User)

    def test_get_shard_method_defined_but_unimplimented(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        sut = BaseBucketingStrategy(shard_group='default')
        with self.assertRaises(NotImplementedError):
            sut.get_shard(User)


class BaseShardedModelBucketingStrategyTestCase(TestCase):

    def test_get_shard_reads_shard_from_model(self):
        class FakeModel(object):
            django_sharding__shard_field = 'whatever_field'
            whatever_field = 'cool_guy_shard'

        sut = BaseShardedModelBucketingStrategy(shard_group='deault')
        self.assertEqual(sut.get_shard(FakeModel()), 'cool_guy_shard')


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
        user = get_user_model().objects.create_user(
            username='username', password='pwassword', email='test@example.com'
        )
        self.assertIsNotNone(user.shard)

    def test_shard_retrieve_shard_from_user_when_used_with_model_and_signal(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username='username', password='pwassword', email='test@example.com'
        )
        sut = RoundRobinBucketingStrategy(shard_group='default', databases=settings.DATABASES)

        self.assertEqual(user.shard, sut.get_shard(user))
        self.assertIsNotNone(user.shard)

    def test_user_round_robin_when_used_with_model_and_signal(self):
        from django.contrib.auth import get_user_model
        shards = []
        for i in xrange(4):
            username = 'username{}'.format(i)
            email = 'username{}@example.com'.format(i)
            shards.append(
                get_user_model().objects.create_user(
                    username=username, password='pwassword', email=email
                ).shard
            )

        self.assertIsNotNone(shards[0])
        self.assertIsNotNone(shards[1])
        self.assertEqual(shards[0], shards[2])
        self.assertEqual(shards[1], shards[3])


class RandomBucketingStrategyTestCase(TestCase):

    def test_pick_shard_picks_valid_shards(self):
        sut = RandomBucketingStrategy(shard_group='default', databases=settings.DATABASES)

        for i in xrange(100):
            self.assertEqual(
                settings.DATABASES[sut.pick_shard(1)]['SHARD_GROUP'],
                'default'
            )


class ModBucketingStrategyTestCase(TestCase):

    def test_pick_shard_and_get_shard_equals_hash_shard_using_mod_of_pk(self):
        sut = ModBucketingStrategy(shard_group='default', databases=settings.DATABASES)
        self.assertEqual(len(sut.shards), 2)

        class FakeModel(object):
            pk = 0

        model = FakeModel()
        for i in xrange(100):
            model.pk = i
            expected_shard = sut.shards[hash(str(i)) % 2]
            self.assertEqual(sut.get_shard(model), expected_shard)
            self.assertEqual(sut.pick_shard(model), expected_shard)


class SavedModBucketingStrategyTestCase(TestCase):

    def test_pick_shard_equals_hash_shard_using_mod_of_pk_and_get_reads_from_model(self):
        sut = SavedModBucketingStrategy(shard_group='default', databases=settings.DATABASES)
        self.assertEqual(len(sut.shards), 2)

        class FakeModel(object):
            pk = 0
            django_sharding__shard_field = 'whatever_field'
            whatever_field = 'cool_guy_shard'

        model = FakeModel()
        for i in xrange(100):
            model.pk = i
            expected_shard = sut.shards[hash(str(i)) % 2]
            self.assertEqual(sut.pick_shard(model), expected_shard)
            self.assertEqual(sut.get_shard(model), 'cool_guy_shard')
