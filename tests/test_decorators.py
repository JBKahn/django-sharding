from django.db import models
from django_sharding_library.id_generation_strategies import TableStrategyModel
from django_sharding_library.decorators import model_config
from django_sharding_library.exceptions import NonExistantDatabaseException, ShardedModelIntializationException
from django_sharding_library.fields import TableShardedIDField
from django.test import TestCase


class ModelConfigDecoratorTestCase(TestCase):

    def setUp(self):
        class ShardedDecoratorTestModelIDs(TableStrategyModel):
            pass
        self.id_table = ShardedDecoratorTestModelIDs

    def test_model_cannot_be_both_sharded_and_marked_for_a_specific_db(self):
        with self.assertRaises(ShardedModelIntializationException):
            @model_config(shard_group='default', database='default')
            class TestModelTwo(models.Model):
                id = TableShardedIDField(primary_key=True, source_table=self.id_table)
                random_string = models.CharField(max_length=120)
                user_pk = models.PositiveIntegerField()

                def get_shard(self):
                    pass

    def test_sharded_model_requires_a_get_shard_method(self):
        with self.assertRaises(ShardedModelIntializationException):
            @model_config(shard_group='default')
            class TestModelTwo(models.Model):
                id = TableShardedIDField(primary_key=True, source_table=self.id_table)
                random_string = models.CharField(max_length=120)
                user_pk = models.PositiveIntegerField()

    def test_sharded_id_field_must_be_primary_key(self):
        with self.assertRaises(ShardedModelIntializationException):
            @model_config(shard_group='default')
            class TestModelTwo(models.Model):
                id = TableShardedIDField(source_table=self.id_table)
                random_string = models.CharField(max_length=120)
                user_pk = models.PositiveIntegerField(primary_key=True)

                def get_shard(self):
                    pass

    def test_sharded_model_must_have_sharded_id_fied(self):
        with self.assertRaises(ShardedModelIntializationException):
            @model_config(shard_group='default')
            class TestModelTwo(models.Model):
                random_string = models.CharField(max_length=120)
                user_pk = models.PositiveIntegerField()

                def get_shard(self):
                    from django.contrib.auth import get_user_model
                    return get_user_model().objects.get(pk=self.user_pk).shard

    def test_puts_shard_group_on_the_model_class(self):
        @model_config(shard_group='testing')
        class TestModelThree(models.Model):
            id = TableShardedIDField(source_table=self.id_table, primary_key=True)
            random_string = models.CharField(max_length=120)
            user_pk = models.PositiveIntegerField()

            def get_shard(self):
                from django.contrib.auth import get_user_model
                return get_user_model().objects.get(pk=self.user_pk).shard

        self.assertEqual(getattr(TestModelThree, 'django_sharding__shard_group', None), 'testing')

    def test_cannot_place_database_on_replica_db(self):
        with self.assertRaises(NonExistantDatabaseException):
            @model_config(database='app_shard_001_replica_001')
            class ShardedTestModelIDsTwo(TableStrategyModel):
                pass

    def test_cannot_place_database_on_non_existant_db(self):
        with self.assertRaises(NonExistantDatabaseException):
            @model_config(database='i_do_not_exist')
            class ShardedTestModelIDsTwo(TableStrategyModel):
                pass

    def test_puts_database_name_on_model_stored_on_another_database(self):
        @model_config(database='app_shard_002')
        class ShardedTestModelIDsThree(TableStrategyModel):
            pass

        self.assertEqual(getattr(ShardedTestModelIDsThree, 'django_sharding__database', None), 'app_shard_002')
