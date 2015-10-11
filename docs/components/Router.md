# The Router

In this library I've included a single router, which uses the previous components. Here we will go through the various elements of the router.

#### Choosing a Database to Read From

The first thing that it checks for is whether or not that database is non-sharded but routed to a database that is not `deafult`. If that is the case, then we know to send you to that database.

On the other hard, if the model is sharded then we attempt to choose a shard for the model if we are provided an instance. In that case, we either have already chosen a shard (for example, we read this previously and are attempting a refresh) or we need to ask the instance how to get it's shard. For now, you can ignore the use of a shard group as that will come up later in the guide.

If neither of these two cases are known, we return `None` lettings Django know that our router has no opinion on what to do.

Note that the `self.get_read_db_routing_strategy` is not included here as that will be adressed in another section.

```python
    def get_shard_for_instance(self, instance):
        return instance._state.db or instance.get_shard()

    def db_for_read(self, model, **hints):
        specific_database = self.get_specific_database_or_none(model)
        if specific_database:
            return specific_database

        if self.get_shard_group_if_sharded_or_none(model):
            instance = hints.get('instance')
            if instance:
                shard = self.get_shard_for_instance(instance)
                shard_group = getattr(model, 'django_sharding__shard_group', None)
                if not shard_group:
                    raise Exception(
                        'Unable to identify the shard_group for a {} model'.format(model)
                    )
                routing_strategy = self.get_read_db_routing_strategy(shard_group)
                return routing_strategy.pick_read_db(shard)
        return None
```

#### Choosing a Database to Write To

This works similarly to reading as we need to identify which database to read from. However, the code is simpler as we never want to read from a replica so always write to the primary database.

```python
    def db_for_write(self, model, **hints):
        specific_database = self.get_specific_database_or_none(model)
        if specific_database:
            return specific_database

        if self.get_shard_group_if_sharded_or_none(model):
            instance = hints.get('instance')
            if instance:
                db = self.get_shard_for_instance(instance)
                db_config = settings.DATABASES[db]
                return db_config.get('PRIMARY', db)
        return None
```

#### Can Items Be Related?

Typically, we can only allow relations between items on the same database as you cannot have a foreign key across a database. As such, we have to check that both objects are stored on the same database.

First we check if it's non-sharded but stored on a single database other than `default`. If they both are, then we only allow the relation is they are stored on the same database. Similarly, the second check looks at the stard status of both items and wether they would be on the same shard or not. If non of these checks are true, then the items are assumed to both be on the default database and the relation is allowed.

```python
    def allow_relation(self, obj1, obj2, **hints):
        """
        Only allow relationships between two items which are both on only one database or
        between sharded items on the same shard.
        """
        specific_database_for_object_one = self.get_specific_database_or_none(obj1)
        specific_database_for_object_two = self.get_specific_database_or_none(obj2)

        if specific_database_for_object_one != specific_database_for_object_two:
            return False
        elif specific_database_for_object_one:
            return True

        shard_group_for_object_one = self.get_shard_group_if_sharded_or_none(obj1)
        shard_group_for_object_two = self.get_shard_group_if_sharded_or_none(obj2)

        if shard_group_for_object_one != shard_group_for_object_two:
            return False
        elif self.shard_group_for_object_one:
            return self.get_shard_for_instance(obj1) == self.get_shard_for_instance(obj2)
        return True
```


#### Can I Be Migrated?

When running your migrations, the app needs to be able to determine which databases require the migration in order to same developers from having to do this work manually.

As such, we restrict migrations to only those which provide the model they are migrating as well as migrations to primary databases. In the event that a model is on a sepcific database or sharded then we also restrict the migration to those sets of databases. By using the module loading system in Django, we can determine the shard status of a model instance in order to make an informed decision.

```python
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if settings.DATABASES[db].get('PRIMARY', None):
            return False
        model_name = model_name or hints.get('model_name')
        if not model_name:
            raise InvalidMigrationException(
                'Model name not provided in migration,'
                'please pass a `model_name` with the hints passed into the migration.'
            )

        # Sometimes, when extending models from another app i.e. the User Model, the app
        # label is the app label of the app where the change is defined but to app with
        # the model is passed in with the model name.
        try:
            app = apps.get_app_config(app_label)
            model = app.get_model(model_name)
        except LookupError:
            app_label = model_name.split('.')[0]
            app = apps.get_app_config(app_label)
            model = app.get_model(model_name[len(app_label) + 1:])

        single_database = self.get_specific_database_or_none(model)
        shard_group = self.get_shard_group_if_sharded_or_none(model)
        if shard_group and single_database:
            raise InvalidMigrationException(
                'Model marked as both sharded and on a single database, '
                'unable to determine where to run migrations for {}.'.format(model_name)
            )
        if single_database:
            return db == single_database
        if shard_group:
            return settings.DATABASES[db]['SHARD_GROUP'] == shard_group
        return db == 'default'
```