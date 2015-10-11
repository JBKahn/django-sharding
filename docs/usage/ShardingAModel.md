# Sharding A Model

#### Defining The Model

Once you've chosen how you'd like to shard your model, which was covered in the earlier sections of this guide, it's very easy to shard a model across a shard group. You need to define your model like this:


```python
from django.db import models

from django_sharding_library.decorators import model_config
from django_sharding_library.fields import TableShardedIDField
from django_sharding_library.models import TableStrategyModel


class ShardedCoolGuyModelIDs(TableStrategyModel):
    pass


@model_config(shard_group='default')
class CoolGuyShardedModel(models.Model):
    id = TableShardedIDField(primary_key=True, source_table=ShardedCoolGuyModelIDs)
    cool_guy_string = models.CharField(max_length=120)
    user_pk = models.PositiveIntegerField()

    def get_shard(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.get(pk=self.user_pk).shard
```

The above example illustrates the id generation strategy of using an unsharded table to generate unique IDs for each instance of the sharded model. The three important steps in defining a sharded model are:

1. The model requires the use the decorator with a given `shard_group` to tell Django that the model is sharded.
2. The model requires a shard-aware primary field, even if it's going to use a simple `AutoIDField`.
3. The model needs a `get_shard` function to instruct how to get a shard given an instance.

#### Accessing Data on Sharded Models

When you're not re-saving an instance of the model you've retreived, you need to tell Django which database to read from and which to save on. This is done by using the `using` command:

```python
# You can use the method on the model or another one to get the shard
shard = 'some_database'
CoolGuyShardedModel.objects.using(shard).filer(some_field='some_value')
```

Once you've defined your model, we can move onto how to run migrations.
