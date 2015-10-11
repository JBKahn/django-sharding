# Replication Lag Time

#### Why This Is Difficult

As mentioned earlier in the documentation, when using replication drives you may get stale data if you read from one of these drives before the data has propogated from the primary drive. This is a difficult problem to solve due to the way routing works in Django.

For example, the following call:
```python
CoolGuyModel.objects.using('some_database').create(user_id=1, some_cool_guy_string="123")
```

Will result in the router recieving the information that we want to create an instance of `CoolGuyModel`. The router is not given the value of any field or details about the instance. As such, it's really hard to mark something as "dirty" such that it can only be read from the primary database. 

The [Django Multi DB Router](https://github.com/jbalogh/django-multidb-router), which is made to be used for replication database, uses a cookie-based strategy. It adds a cookie every time a user calls a function which modifies data and that entire require reads only from primary database. There are two flaws with this method that prevent it from being included here:

The first is that this does not handle the case of stale data being read in from non-request and non-response sources. For example: Celery Tasks, Management Commands and anything else that writes then reads data (or reads while a user is modifying it) could real stale data.

The second is that a second user requesting the same data will get stale data. This does not invalidate the data but instead works on invalidating just the user who wrote the changes.

As of yet, I have yet to come up with a better way of handling replication lag time.

#### A Possible Implementation

To integrate [Django Multi DB Router](https://github.com/jbalogh/django-multidb-router) version 0.6 (latest at the time of writing this) with this library, you can do the following:

1. pip install the `django-multidb-router` package and add it to your requirements:

`pip install django-multidb-router`

2. Subclass the router I've provided:

```python
from django.conf import settings

from multidb.pinning import this_thread_is_pinned

from django_sharding_library.router import ShardedRouter


class ShardedRouterWithRepliationLagTimeSupport(ShardedRouter):
    """
    A router that is shard-aware and supports replication lag time.
    """

    def get_replica_primary_mapping(self, databases):
        """
        Creates a dictionary that maps a replica drive name to its
        primary database.
        """
        mapping = getattr(self, 'primary_replica_mapping', {})
        if mapping:
            return mapping
        for name, config in databases.items():
            # map primary drives to themselves to make the code simpler
            primary = config.get('PRIMARY', name)
            mapping[name].append(primary)
        setattr(self, 'primary_replica_mapping', mapping)
        return mapping

    def db_for_read(self, model, **hints):
        database = super(ShardedRouterWithRepliationLagTimeSupport, self).db_for_read(
            model, **hints
        )
        if database is not None:
            primary_replica_mapping = self.get_replica_primary_mapping(
                settings.DATABASES
            )
            primary_db = primary_replica_mapping[database]
            return primary_db if this_thread_is_pinned() else database
        return None
```

3. Set that router as your database router in your settings file:

```python
DATABASE_ROUTERS=['<path_to_router>.ShardedRouterWithRepliationLagTimeSupport'],
````

4. Add the middlewear 

```python
MIDDLEWARE_CLASSES = (
    'multidb.middleware.PinningRouterMiddleware',
    # ...more middleware here...
)
```

5. Adjust the replication lag time and the cookie name:

```python
MULTIDB_PINNING_SECONDS = 15
MULTIDB_PINNING_COOKIE = 'multidb_pin_writes'
```

Note: This has not been extensively tested by the author.