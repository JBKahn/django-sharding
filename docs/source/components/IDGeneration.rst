.. ID Generation:

================
ID Generation
================

When sharding your data there are a few important upfront decisions to make, one
of the most important ones is how identify each of your models. There are several
common strategies and this library allows you to configure this yourself if you
know the strategy you'd like to use.

The reason this becomes important is that once you pick a strategy, those ids
will be used in your foreign keys and it will be difficult to change. There
are a few common strategies, most of which come shipped with the package.

1) Unique shard IDs generated using the time
--------------------------------------------

This strategy uses a 64 bit integer to encode the time the item was created, the
shard it was created on and a counter. It works by creating a counter on each of
the shards. It allows you to store as many unique combinations of time,
shard and counter as can fit in that 64 bit integer, which is 1000 per shard per
millisecond.

i.e. the integer 3863625104385

::

  from datetime import datetime

  id = 3863625104385

  date_created = datetime.fromtimestamp(((id >> 23) + 1476914064192)/ 1000)
  # datetime.datetime(2016, 10, 19, 18, 2, 4, 772000)

  counter = int(bin(id)[-10:], 2)
  # 1st object created

  shard = int(bin(id)[-23:-10], 2)
  # 31st shard


This method supports up to 8192 shards (13 bits) and up to 1024 inserts per
millisecond (10 bits). this should be more than enough for most use cases as
it has been used in places like Instagram where scale is an issue.


Note: While I have only included the Postgres implimentation of this so far, it is not
difficult to adapt this for other databases (PRs welcome!).


2) Use a UUID & shard id combination
------------------------------------

This is a much simpler route and has the benefit of being easier to understand
as each of the ids is just a concatenation or a uuid and a shard's id. The
downside to this approach is that if you ever needed to move a record from one
database to another, there can be uuid collisions (even if those are fairly
unlikely).


3) Use a simple integer
-----------------------

Instead of generating more complicated IDs, if we use a counter or sequence on
the main database to generate the IDs then we can use an integer to have unique
IDs across all the shards as the counter's increment is atomic and thus we have
no issues with collisions. Note: I have not included this implementation in the
package yet.

The included implementation of this uses a table on the main database rather
than a counter to proxy the auto incrementing field's counter. This was included
as this package was created in part to replace an existing system that worked
this way.


Writing Your Own
----------------

When writing your own, you must provide a class with a `get_next_id` method on
it. There are no other specific requirements, as you can also implement the
caller and provide any args needed.

::

  class BaseIDGenerationStrategy(object):
      """
      A strategy for Generating unique identifiers.
      """
      def get_next_id(self, database=None):
          """
          A function which returns a new unique identifier.
          """
          raise NotImplemented


Pinterest
---------

They recently wrote a `lovely article <https://engineering.pinterest.com/blog/sharding-pinterest-how-we-scaled-our-mysql-fleet>`_
about their sharding strategy. They use a 64 bit ID that works like so:


::

  def create_item_id(self, database, model_class, local_id):
      return (
          (self.database_name_to_id_map[database] << 46) |
          (self.model_to_id_map[model_class] << 36) |
          (local_id <<0)
      )

  def get_info_from_item_id(self, item_id):
      database_id = (item_id >> 46) & 0xFFFF
      model_id  = (item_id >> 36) & 0x3FF
      local_id = (item_id >>  0) & 0xFFFFFFFFF
      return (
          self.database_id_to_name_map[database_id],
          model_id_to_class_map[model_id],
          local_id
      )

By using the above method to reference items, you need not choose an explicit ID
generation method and instead the `local_id` can simply by an autoincrementing
field on that table.

That field would look something like this:

::

  class ShardedLocalIDField(ShardedIDFieldMixin, AutoField):
      def __init__(self, *args, **kwargs):
          kwargs['strategy'] = None
          return super(ShardedLocalIDField, self).__init__(*args, **kwargs)

      def get_pk_value_on_save(self, instance):
          return super(AutoField, self).get_pk_value_on_save(instance)


While I have not included all of the code required to use this type of sharding
strategy, this may be accomplished using this library.
