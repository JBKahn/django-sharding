# Sharding Functions

A sharding function is a function that is used to choose a shard for a group of objects. This is composed of two core functionts that decide how to pick a shard in the case where we haven't previously chosen one and how to retrieve a previously chosen shard. This is split into the two functions `pick_shard` and `get_shard`. There are times when those two functions do the same thing, but in many cases the choice to pick a shard is non-deterministic and so you'll need to read from a stored value in `get_shard`.

Note: This library does support Functional Sharding, which allows you to have multiple groups of shards or `sharding_group`s. This would allow you to store all of the objects of type A on one set of shards and all of the items of type B on another set of shards. However, the author does not suggest having multiple sharding functions and splitting data for one related item across multiple shards. Doing so prevents you from doing database joins on those items and typically the desire to split data in this way suggests that the whole system should be split. It is much easier and simpler to store all related data on a single shard.

An interface for a sharding strategy looks as follows:

```python
class BaseBucketingStrategy(object):
    def __init__(self, shard_group='default'):
        self.shard_group = shard_group

    def get_shards(self, databases):
        return [
            name for( name, config) in databases
            if (
                config.get('SHARD_GROUP') == self.shard_group and
                not config.get('PRIMARY')
            )
        ]

    def pick_shard(self, model_sharded_by):
        """
        Returns the shard for the model which has not previously been bucketed
        into a shard.
        """
        raise NotImplemented

    def get_shard(self, model_sharded_by):
        """
        Returns the shard for a model which has already been assigned a shard.
        """
        raise NotImplemented
```

There are multiple ways to impliment the above code and I will provide, as an example, the functions that are shipped with this packages. There are two types of strategies that you may wish to use. The first kind, deterministic functions, will always return the same bucket and storage of the chosen shard is optional. The second kind, non-deterministic functions, require the shard to be stored as there is no way to derive the shard that belongs to a group of objects

#### Deterministic Functions

I have not shipped this package with any truely deterministic functions as all the ones that I've implimented either use randomness, order or depend on the number of shards in the system as the time that the shard is picked. This is not highly reccomended andis a considerably harder method but could still be implimented. For example, if the number of shards were never going to change, you could do something like this:

```python
class ModBucketingStrategy(BaseBucketingStrategy):
    """
    A shard selection strategy that assigns shards based on the mod of the
    models pk.
    """
    def __init__(self, shard_group, databases):
        super(RoundRobinBucketingStrategy, self).__init__(shard_group)
        self.shards = self.get_shards(databases)
        self.shards.sort()

    def pick_shard(self, model_sharded_by):
        return self.shards[hash(str(model_sharded_by.pk)) % len(self.shards)]

    def get_shard(self, model_sharded_by):
        return self.pick_shard(model_sharded_by)
```

#### Non-deterministic Functions

##### Random Bucketing Strategy

As the name says, this method chooses a random shard and ends up storing it on the model in question.

```python
class RandomBucketingStrategy(BaseShardedModelBucketingStrategy):
    """
    A shard selection strategy that assigns shards randomly.
    This is non-deterministic and this strategy assumes the shard is saved to
    the model.
    """
    def __init__(self, shard_group, databases):
        super(RoundRobinBucketingStrategy, self).__init__(shard_group)
        self.shards = self.get_shards(databases)

    def pick_shard(self, model_sharded_by):
        return choice(self.shards)

    def get_shard(self, model_sharded_by):
        return model_sharded_by.shard
```

##### Round-Robin Bucketing Strategy

This uses a round-robin approach to choose a shard in order to maintain a balance across the system so that the proportion of new instances is even across the shards:

```python
class RoundRobinBucketingStrategy(BaseShardedModelBucketingStrategy):
    def __init__(self, shard_group, databases):
        super(RoundRobinBucketingStrategy, self).__init__(shard_group)
        shards = self.get_shards(databases)
        max_index = max(0, len(shards) - 1)
        starting_index = randint(0, max_index)
        shards = shards[starting_index:] + shards[:starting_index]
        self._shards_cycle = cycle(shards)

    def pick_shard(self, model_sharded_by):
        return self._shards_cycle.next()

    def get_shard(self, model_sharded_by):
        return model_sharded_by.shard
```

Since this is initialized at app initialization time, it begins the cycle at a random index, otherwise the first shard would always be imbalanced. 

##### Mod Bucketing Strategy

This works the same way as the non-deterministic strategy but allows you to add shards by storing them on the model.

```python
class ModBucketingStrategy(BaseBucketingStrategy):
    """
    A shard selection strategy that assigns shards based on the mod of the
    models pk.
    """
    def __init__(self, shard_group, databases):
        super(RoundRobinBucketingStrategy, self).__init__(shard_group)
        self.shards = self.get_shards(databases)

    def pick_shard(self, model_sharded_by):
        return self.shards[hash(str(model_sharded_by.pk)) % len(self.shards)]

    def get_shard(self, model_sharded_by):
        return model_sharded_by.shard
```