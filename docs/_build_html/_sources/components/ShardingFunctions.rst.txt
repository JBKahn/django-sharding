.. Sharding Functions:

==================
Sharding Functions
==================

A sharding function is a python class that will choose which data belongs on
which database and let us know which database the stored data is on.

This is split into the two functions `pick_shard` and `get_shard` on a plain
python class. The reason this is split into two different functions is that
there are common sharding functions used that are not deterministic. Since the
generator may be non deterministic then both are implemented separately. An
example of this is to round-robin bucket users into their own shards.

An interface for a sharding strategy looks as follows:

::

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
          Returns the shard for the model which has not previously
          been bucketed into a shard.
          """
          raise NotImplemented

      def get_shard(self, model_sharded_by):
          """
          Returns the shard for a model which has already been
          assigned a shard.
          """
          raise NotImplemented


As I mentioned above, there are are both deterministic and non-deterministic
ways of bucketing into shards. As an example below, I will show the ones
included wit the package.


Deterministic Functions
-----------------------

I have not shipped this package with any truly deterministic functions as I've
yet to come across a need and the example below is brittle as it breaks as soon
as you add more shards to the system. Nonetheless, I have included it for
completeness.

::

  class ModBucketingStrategy(BaseBucketingStrategy):
      """
      A shard selection strategy that assigns shards based on the mod
      of the models pk.
      """
      def __init__(self, shard_group, databases):
          super(RoundRobinBucketingStrategy, self).__init__(
              shard_group
          )
          self.shards = self.get_shards(databases)
          self.shards.sort()

      def pick_shard(self, model_sharded_by):
          return self.shards[
              hash(str(model_sharded_by.pk)) % len(self.shards)
          ]

      def get_shard(self, model_sharded_by):
          return self.pick_shard(model_sharded_by)


Non-deterministic Functions
---------------------------

Random Bucketing Strategy
^^^^^^^^^^^^^^^^^^^^^^^^^

As the name says, this method chooses a random shard and ends up storing it on
the model in question.

::

  class RandomBucketingStrategy(BaseShardedModelBucketingStrategy):
      """
      A shard selection strategy that assigns shards randomly.
      This is non-deterministic and this strategy assumes the shard
      is saved to the model.
      """
      def __init__(self, shard_group, databases):
          super(RoundRobinBucketingStrategy, self).__init__(
              shard_group
          )
          self.shards = self.get_shards(databases)

      def pick_shard(self, model_sharded_by):
          return choice(self.shards)

      def get_shard(self, model_sharded_by):
          return model_sharded_by.shard


Round-Robin Bucketing Strategy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This uses a round-robin approach to choose a shard in order to maintain a
balance across the system so that the proportion of new instances is even
across the shards:

::

  class RoundRobinBucketingStrategy(BaseShardedModelBucketingStrategy):
      def __init__(self, shard_group, databases):
          super(RoundRobinBucketingStrategy, self).__init__(
              shard_group
          )

          shards = self.get_shards(databases)
          max_index = max(0, len(shards) - 1)
          starting_index = randint(0, max_index)

          shards = shards[starting_index:] + shards[:starting_index]
          self._shards_cycle = cycle(shards)

      def pick_shard(self, model_sharded_by):
          return next(self._shards_cycle)

      def get_shard(self, model_sharded_by):
          return model_sharded_by.shard


Since this is initialized at app initialization time, it begins the cycle at a
random index, otherwise the first shard would always be imbalanced.

Mod Bucketing Strategy
^^^^^^^^^^^^^^^^^^^^^^

This works the same way as the non-deterministic strategy but allows you to add
shards by storing them on the model.

::

  class ModBucketingStrategy(BaseBucketingStrategy):
      """
      A shard selection strategy that assigns shards based on the mod of the
      models pk.
      """
      def __init__(self, shard_group, databases):
          super(RoundRobinBucketingStrategy, self).__init__(
              shard_group
          )
          self.shards = self.get_shards(databases)

      def pick_shard(self, model_sharded_by):
          return self.shards[
              hash(str(model_sharded_by.pk)) % len(self.shards)
          ]

      def get_shard(self, model_sharded_by):
          return model_sharded_by.shard
