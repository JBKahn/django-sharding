# ID Generation

In order to shard your database, one of the first decisions to makee is how you assign identifiers to the sharded objects. While it is not required, it is highly reccomended that you choose a unique identifier. The main reason here being that you may want to either move data across shards later or that you may choose to analyze data across various shards for analytics and you will have to differentiate those objects before moving them to another server.

This repository is initially shipping with two strategies but you may impliment your own. The base requirement at the moment is that you define a class like this:

```python
class BaseIDGenerationStrategy(object):
    """
    A strategy for Generating unique identifiers for the sharded models.
    """
    def get_next_id(self, database=None):
        """
        A function which returns a new unique identifier.
        """
        raise NotImplemented
```

In the above example, it takes an optional database. However you will find that you can choose to provide additional arguments later on when you make use of the generator. The only real requirements is that it be a class with a `get_next_id` function.

The two included in the package are:

1. Use an autoincriment field to mimic the way a default table handles the operation
2. Assign each item a UUID with the shard name appended to the end.

##### The Autoincriment Method

This strategy uses a non-sharded table in order to generate unqiue identifiers. The package currently includes a backend for both PostgresQL and MySQL which uses either a bigserial or serial field, respectively. That allows the generation of up to 9223372036854775807 items which is probably enough for most applications that don't need to consider a dedicated sharding system.

Note: The MySQL implimentation uses a single row to accomplish this task while Postgres currently uses n rows until 9.5 is released and upsert can be used.

##### The UUID Method

While the odds of a UUID collision are very low, it is still possible and so we append the database shard name as a way to garuntee that they remain unique. The only drawback to this method is that the items cannot be moved across shards. However, it is the recomendation of the author that you refrain from shard rebalancing and instead focus on maintaining lots of shards rather than worry about balancing few large ones.

##### Pintrest

They recently wrote a [lovely article](https://engineering.pinterest.com/blog/sharding-pinterest-how-we-scaled-our-mysql-fleet) about their sharding strategy. They use a 64 bit ID that works like so:

```python
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
```
By using the above method to reference items, you need not choose an explicit ID generation method and instead the `local_id` can simply by an autoincrimenting field on that table.

That field would look something like this:

```python
class ShardedLocalIDField(ShardedIDFieldMixin, AutoField):
    def __init__(self, *args, **kwargs):
        kwargs['strategy'] = None
        return super(ShardedLocalIDField, self).__init__(*args, **kwargs)

    def get_pk_value_on_save(self, instance):
        return super(AutoField, self).get_pk_value_on_save(instance)
```

While I have not inlcuded all of the code required to use this type of sharding strategy, this may be accomplished using this library. 