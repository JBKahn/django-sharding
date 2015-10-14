# Read Strategies

This framework supports the use of read strategies, here's an example of when you might want to use one. If you're using replication databases, you may want to distribute the load across these databases rather than always reading the primary drive by default.

A read strategy looks something like this:

```python
class BaseRoutingStrategy(object):
    """
    A base strategy for picking which database to read from when there are read
    replicas in the system. In order to extend this strategy, you must define a
    `pick_read_db` function which returns the name of the DB to read from,
    given a primary DB.
    If there are no read replicas defined, all strategies should always return the
    primary.
    """
    def __init__(self, databases):
        self.primary_replica_mapping = self.get_primary_replica_mapping(databases)

    def get_primary_replica_mapping(self, databases):
        """
        Creates a dictionary that maps a primary drive name to all the names of
        it's replication databases. This can be used in the strategies.
        """
        mapping = {}
        for name, config in databases.items():
            primary = config.get('PRIMARY', None)
            if not primary:
                continue
            if primary not in mapping:
                mapping[primary] = []
            if primary != name:
                mapping[primary].append(name)
        return mapping

    def pick_read_db(self, primary_db_name):
        """
        Given the name of a primary, pick the name of the database to read
        from which may be a replica or the primary itself.
        """
        raise NotImplemented
```


Here we'll go through some of the included strategies:

##### Primary Only Read Strategy

A strategy that ignores existing replication databases and will always choose the primary database unless instructed otherwise.

```python
class PrimaryOnlyRoutingStrategy(BaseRoutingStrategy):
    """
    A strategy which will always read from the primary, unless overridden,
    regardless of replicas defined.
    """
    def pick_read_db(self, primary_db_name):
        return primary_db_name
```

##### Random Read Strategy

If you don't have an opinion on the load on each device, you may want to simply choose a random one each time.

```python
class RandomRoutingStrategy(BaseRoutingStrategy):
    """
    A strategy which will choose a random read replicas, or the primary,
    when choosing which database to read from.
    """
    def pick_read_db(self, primary_db_name):
        return choice(self.primary_replica_mapping[primary_db_name] + [primary_db_name])
```

##### Round Robin Read Strategy

This is similar to the sharding function in that it should provide a well rounded solution to picking a database and split the load evenly. In order to reduce load imbalance due to the app being restarted, you may want to choose a random DB to start with here as well.

```python
class RoundRobinRoutingStrategy(BaseRoutingStrategy):
    """
    A strategy which will cycle through the read replicas and primary, in a
    round-robin fashion when choosing which database to read from.
    """
    def __init__(self, databases):
        super(RoundRobinRoutingStrategy, self).__init__(databases)
        self.read_cycles = {}

        for primary, replicas in self.primary_replica_mapping.viewitems():
            self.read_cycles[primary] = cycle(replicas + [primary])

    def pick_read_db(self, primary_db_name):
        return self.read_cycles[primary_db_name].next()
```

##### Ratio Routing Strategy

Here I've provided a basic example, but you could choose to split it up across all the databases at any ratio. For example, you may want to read from the primary drive tem percent of the time, replica 1 forty percent of the time and replica 2 fifty percent of the time. Here's the example implementation:

```python
class ExampleRatioRoutingStrategy(BaseRoutingStrategy):
    def pick_read_db(self, primary_db_name):
        num = randint(0, 10):
        if num == 0:
            return primary_db_name
        elif num < 5:
            return self.primary_replica_mapping[primary_db_name][0]
        return self.primary_replica_mapping[primary_db_name][1]
```

##### Note About Using Read Strategies

If you're using one of the above, or a custom read strategy, there are some considerations that are important when choosing them. The system does not currenly have a built-in system to handle replication lag time. For example, if a user updates item A in the primary database then reading from a replication database before that data has propogated will result in the user getting stale data. This is typically handled by reading only from the primary drive during this period, however the system does not currenly include these tools and will need to be written for the project. For more information, check out the section where we discuss replication lag time.
