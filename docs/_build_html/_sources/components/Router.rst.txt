.. The Router:

================
The Router
================

In this library I've included a single router, which uses the previous
components. Here we will go through the various elements of the router. This
section is meant to explain how the library works and it will be unlikely for
this to be extended or modified unless something custom is needed.

Note: The utils and helper method's code is not included in this section.


Choosing a Database to Read From
--------------------------------

The router checks for several conditions in the order of:
1) Is this model stored on only one database, if so then return it.
2) If this model sharded and is the instance called in `hints`, if so then
retrieve the shard.
3) If we have retrieved the shard, then use a read strategy, otherwise we return
None since we do not know where to read it from.


::

  def db_for_read(self, model, **hints):
      possible_databases = get_possible_databases_for_model(
          model=model
      )
      if len(possible_databases) == 1:
          return possible_databases[0]

      shard = self._get_shard(model, **hints)
      if shard:
          shard_group = getattr(
              model, 'django_sharding__shard_group', None
          )
          if not shard_group:
              raise DjangoShardingException(
                  'Unable to identify the shard_group for' +
                  'the {} model'.format(model)
              )
          routing_strategy = self.get_read_db_routing_strategy(
              shard_group
          )
          return routing_strategy.pick_read_db(shard)
      return None


Choosing a Database to Write To
--------------------------------

This works similarly to the above, except we only return the primary database
rather than using a read strategy.

::

  def db_for_write(self, model, **hints):
      possible_databases = get_possible_databases_for_model(
          model=model
      )
      if len(possible_databases) == 1:
          return possible_databases[0]

      shard = self._get_shard(model, **hints)

      if shard:
          db_config = settings.DATABASES[shard]
          return db_config.get('PRIMARY', shard)
      return None


Can Items Be Related?
---------------------

We can only allow relations between items on the same database as you cannot
have a foreign key across a database.

The router checks for several conditions in the order of:
1) Are both models stored on only one database and are they the same one, if so
then we can allow that relationship.
2) If the above is not true, are these instances on the same database, as that
is the only way they can be related.

::

  def allow_relation(self, obj1, obj2, **hints):
      """
      Only allow relationships between two items which are
      both on only one database or between sharded items on
      the same shard.
      """

      object1_databases = get_possible_databases_for_model(
          model=obj1._meta.model
      )
      object2_databases = get_possible_databases_for_model(
          model=obj2._meta.model
      )

      if (
          (len(object1_databases) == len(object2_databases) == 1) and
          (object1_databases == object2_databases)
      ):
          return True

      return (
          self.get_shard_for_instance(obj1) ==
          self.get_shard_for_instance(obj2)
      )


Can I Be Migrated?
------------------

When running your migrations, the app needs to be able to determine which
databases require the migration in order to save developers from having to do
this work manually.

As such, we restrict migrations to run only on the primary databases which store
the model. In the case of sharded models, they are stored on many databases and
each one needs to me migrated.

By using the module loading system in Django, we can determine the shard status
of a model instance in order to make an informed decision.


::

  def allow_migrate(self, db, app_label, model_name=None, **hints):
      if settings.DATABASES[db].get('PRIMARY', None):
          return False

      # Since the API for this function is limiting in a sharded
      # environemnt, we provide an override to specify which
      # databases to run the migrations on.
      if hints.get("force_migrate_on_databases", None):
          return db in hints["force_migrate_on_databases"]

      model_name = model_name or hints.get('model_name')
      model = hints.get('model')
      if model:
          model_name = model.__name__

      # Return true if any model in the app is on this database.
      if not model_name:
          app = apps.get_app_config(app_label)
          for model in app.get_models():
              if is_model_class_on_database(model=model, database=db):
                  return True
          return False

      # Sometimes, when extending models from another app the
      # the app's name is contained in the `model_name` param
      # using the `app.model` syntax.
      try:
          app = apps.get_app_config(app_label)
          model = app.get_model(model_name)
      except LookupError:
          app_label = model_name.split('.')[0]
          app = apps.get_app_config(app_label)
          model = app.get_model(model_name[len(app_label) + 1:])

      try:
          return is_model_class_on_database(model=model, database=db)
      except DjangoShardingException as e:
          raise InvalidMigrationException(
              e.args[0]
          )
