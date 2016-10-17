from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django_sharding_library.decorators import model_config, shard_storage_config
from django_sharding_library.fields import (
    TableShardedIDField,
    ShardForeignKeyStorageField,
    PostgresShardGeneratedIDAutoField,
    PostgresShardGeneratedIDField
)
from django_sharding_library.models import ShardedByMixin, ShardStorageModel, TableStrategyModel
from django_sharding_library.constants import Backends


# A model for use with a sharded model to generate pk's using
# an autoincrement field on the backing TableStrategyModel.
# This one is initialized but used in no strategy.
class ShardedModelIDs(TableStrategyModel):
    pass


# An implimentation of the extension of a the Django user to add
# the mixin provided in order to save the shard on the user.
@shard_storage_config()
class User(AbstractUser, ShardedByMixin):
    pass


# An implimentation of the extension of a the Django user to add
# the mixin provided in order to save the shard on the user.
@shard_storage_config(shard_group='postgres')
class PostgresShardUser(AbstractUser, ShardedByMixin):
    pass


# A model for use with a sharded model to generate pk's using
# an autoincrement field on the backing TableStrategyModel.
# This one is initialized for use with TestModel and is stored
# on `app_shard_001`.


@model_config(database='app_shard_001')
class ShardedTestModelIDs(TableStrategyModel):
    pass


# An example of a sharded model which uses the `TableStrategy` to
# generate uuid's for its instances.


@model_config(shard_group='default', sharded_by_field='user_pk')
class TestModel(models.Model):
    id = TableShardedIDField(primary_key=True, source_table_name='tests.ShardedTestModelIDs')
    random_string = models.CharField(max_length=120)
    user_pk = models.PositiveIntegerField()

    def get_shard(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.get(pk=self.user_pk).shard

    @staticmethod
    def get_shard_from_id(user_pk):
        from django.contrib.auth import get_user_model
        user = get_user_model()
        return user.objects.get(pk=user_pk).shard


@model_config(database='default')
class UnshardedTestModel(models.Model):
    id = TableShardedIDField(primary_key=True, source_table_name='tests.ShardedTestModelIDs')
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


@model_config(database='app_shard_001')
class PostgresCustomIDModelBackupField(TableStrategyModel):
    pass


@model_config(shard_group="postgres", sharded_by_field="user_pk")
class PostgresCustomAutoIDModel(models.Model):
    if settings.DATABASES['default']['ENGINE'] in Backends.POSTGRES:
        id = PostgresShardGeneratedIDAutoField(primary_key=True)
    else:
        id = TableShardedIDField(primary_key=True, source_table_name='tests.PostgresCustomIDModelBackupField')
    random_string = models.CharField(max_length=120)
    user_pk = models.PositiveIntegerField()

    def get_shard(self):
        return PostgresShardUser.objects.get(pk=self.user_pk).shard

    @staticmethod
    def get_shard_from_id(user_pk):
        return PostgresShardUser.objects.get(pk=user_pk).shard


@model_config(shard_group="postgres")
class PostgresCustomIDModel(models.Model):
    if settings.DATABASES['default']['ENGINE'] in Backends.POSTGRES:
        id = PostgresShardGeneratedIDField(primary_key=True)
        some_field = PostgresShardGeneratedIDField()
    else:
        id = TableShardedIDField(primary_key=True, source_table_name='tests.PostgresCustomIDModelBackupField')
        some_field = models.PositiveIntegerField()
    random_string = models.CharField(max_length=120)
    user_pk = models.PositiveIntegerField()

    def get_shard(self):
        return PostgresShardUser.objects.get(pk=self.user_pk).shard

    @staticmethod
    def get_shard_from_id(user_pk):
        return PostgresShardUser.objects.get(pk=user_pk).shard
