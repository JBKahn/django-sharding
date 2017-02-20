# Sharding A Model

### Defining The Shard Key

Based on the earlier sections of the documentation, you need to choose a sharding function, strategy and ID generation strategy.

#### Storing The Shard On The Model With The Shard Key

The first way to do this is to store the shard on the model with the shard key. For simplicity, we'll assume that you want to shard all your data by a key on the User table, although the `ShardedByMixin` could be used on any model. The code would therefore look something like this:

```python
from django.contrib.auth.models import AbstractUser

from django_sharding_library.models import ShardedByMixin


class User(AbstractUser, ShardedByMixin):
    pass
```

Add that custom User to your settings file using the string class path:

```python
AUTH_USER_MODEL = '<app_with_user_model>.User'
```

Now the result is that the User table has a field on it to store the shard and the app configuration is will automatically generate and save the shard to the User model on the first save.

#### Storing The Shard On The a Model Without The Shard Key

Alternatively you may want to store the shard somewhere else. For example, the system primary runs on operations done on branches of a bank and so you could store the shard on the branch but you'd also like all branches of the same bank to be on a single shard. In this situation, you'll want to store the shard on the branch but ensure that no two branches of the same bank are ever on different shards. To do that, you need to use a second table to store the shard and foreign key to that table rather than storing the shard directly.

For example, this code sets up `SomeCoolGuyModel` to store the shard using a foreign key so that all `SomeCoolGuyModel`s that are nested under the same user are on the same shard.

```python
from django.db import models

from django_sharding_library.fields import ShardForeignKeyStorageField
from django_sharding_library.models import ShardStorageModel


class ShardStorageTable(ShardStorageModel):
    """
    A table with a row for the unique sharding key and a value for the shard.
    """
    pass


class SomeCoolGuyModel(models.Model):
    shard = ShardForeignKeyStorageField(ShardStorageTable, shard_group='default')
    some_cool_guy_string = models.CharField(max_length=120)
    test = models.ForeignKey(UnshardedTestModel)

    def get_shard_key(self):
        return self.test.user_pk
```


### Create Your First Sharded Model

#### Defining The Model

Once you've chosen how you'd like to shard your model, it's very easy to shard a model across a shard group. You need to define your model like this:


```python
from django.db import models

from django_sharding_library.decorators import model_config
from django_sharding_library.fields import TableShardedIDField
from django_sharding_library.models import TableStrategyModel


class ShardedCoolGuyModelIDs(TableStrategyModel):
    pass


@model_config(shard_group='default', sharded_by_field='user_pk')
class CoolGuyShardedModel(models.Model):
    id = TableShardedIDField(primary_key=True, source_table_name='app.ShardedCoolGuyModelIDs')
    cool_guy_string = models.CharField(max_length=120)
    user_pk = models.PositiveIntegerField()

    def get_shard(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.get(pk=self.user_pk).shard

    @staticmethod
    def get_shard_from_id(user_pk):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.get(pk=user_pk).shard
```

The above example illustrates the id generation strategy of using an unsharded table to generate unique IDs for each instance of the sharded model. The four important steps in defining a sharded model are:

1. The model requires the use the decorator with a given `shard_group` and `sharded_by_field` to tell Django that the model is sharded and what field it is sharded by.
2. The model requires a shard-aware primary field, even if it's going to use a simple `AutoIDField`.
3. The model needs a `get_shard` function to instruct how to get a shard given an instance.
4. The model needs a `get_shard_from_id` static method that will tell the router which shard to query against. The method must take an argument (which will be the `sharded_by_field` value you are querying against) and return the shard to query.

#### Accessing Data on Sharded Models

When you're not re-saving an instance of the model you've retrieved, you need to tell Django which database to read from and which to save on. This is done by using the `using` command, or by querying with the `shard_by_id` field in the filter(), create(), get(), or get_or_create() methods:

```python
# You can use the method on the model or another one to get the shard
shard = 'some_database'
CoolGuyShardedModel.objects.using(shard).filter(some_field='some_value')
# Or, without the using() statement, if you query against the `sharded_by_field` in your filter()
CoolGuyShardedModel.objects.filter(user_pk=123, some_field='some_value')
```

Once you've defined your model, we can move onto how to run migrations.

### Using the PostgresShardGeneratedIDField

If you would like to use the PostgresShardGeneratedIDField, there are a few subtle differences and caveats that you need to be aware of.

1. If you define a PostgresShardGeneratedIDField, you should not use another shard ID generation strategy with that model. Additionally, the field should be marked as the primary key. An example of a model with a PostgresShardIDField:
```python
@model_config(shard_group='default')
class CoolGuyShardedModel(models.Model):
    id = PostgresShardGeneratedIDField(primary_key=True)
    cool_guy_string = models.CharField(max_length=120)
    user_pk = models.PositiveIntegerField()
```
2. You must define a "SHARD_EPOCH" variable in your Django settings file. This can be any epoch start time you want, but once chosen, should NEVER be changed. Here is an example of what it should look like (which will make your shard epoch Jan 1, 2016):
```python
import time
from datetime import datetime
# other settings go here...
SHARD_EPOCH=int(time.mktime(datetime(2016, 1, 1).timetuple()) * 1000)
```

3. When you are editing your DATABASES settings, the order of the shards MUST be maintained. If you add a new shard, it needs to be added to the end of the list of databases, not to the beginning or middle.
4. There is a maximum number of logical shards supported by this field. You can only have up to 8191 logical shards: if you try to go beyond, you will get duplicate IDs between your shards. Do not try to add more than 8191 shards. If you need more than that, I recommend you choose one of the other ID generation strategies.
