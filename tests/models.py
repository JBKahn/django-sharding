from django.contrib.auth.models import AbstractUser
from django.db import models
from django_sharding_library.decorators import model_config
from django_sharding_library.fields import TableShardedIDField, ShardForeignKeyStorageField
from django_sharding_library.models import ShardedByMixin, ShardStorageModel, TableStrategyModel


# A model for use with a sharded model to generate pk's using
# an autoincrement field on the backing TableStrategyModel.
# This one is initialized but used in no strategy.
class ShardedModelIDs(TableStrategyModel):
    pass


# An implimentation of the extension of a the Django user to add
# the mixin provided in order to save the shard on the user.
class User(AbstractUser, ShardedByMixin):
    shard_group = 'default'
    django_sharding__shard_group = 'default'


# A model for use with a sharded model to generate pk's using
# an autoincrement field on the backing TableStrategyModel.
# This one is initialized for use with TestModel and is stored
# on `app_shard_001`.


@model_config(database='app_shard_001')
class ShardedTestModelIDs(TableStrategyModel):
    pass


# An example of a sharded model which uses the `TableStrategy` to
# generate uuid's for its instances.


@model_config(shard_group='default')
class TestModel(models.Model):
    id = TableShardedIDField(primary_key=True, source_table=ShardedTestModelIDs)
    random_string = models.CharField(max_length=120)
    user_pk = models.PositiveIntegerField()

    def get_shard(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.get(pk=self.user_pk).shard


@model_config(database='default')
class UnshardedTestModel(models.Model):
    id = TableShardedIDField(primary_key=True, source_table=ShardedTestModelIDs)
    random_string = models.CharField(max_length=120)
    user_pk = models.PositiveIntegerField()

    def get_shard(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.get(pk=self.user_pk).shard


class ShardStorageTable(ShardStorageModel):
    pass


class ShardedByForiegnKeyModel(models.Model):
    shard = ShardForeignKeyStorageField(ShardStorageTable, shard_group='default')
    random_string = models.CharField(max_length=120)
    test = models.ForeignKey(UnshardedTestModel)

    def get_shard_key(self):
        return self.test.user_pk
