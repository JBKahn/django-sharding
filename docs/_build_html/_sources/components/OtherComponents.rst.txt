.. Other Components:

================
Other Components
================

A quick run through of some of the other components shipped with the library.

Decorators
----------

Model Configuration Decorator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the decorators provided is used to label where a model will be stored,
wether it be on a single shard or across many. This decorator also does some
validation that the model is set up correctly.

It does the following:
1) Validates that the primary key is shard aware by checking that it included
the sharded mixin.

2) That the model is being stored on only primary databases.

3) That any postgres specific fields are being used on postgres databases.

4) Provides a hook for some extra magic (always be careful when using magic) to
remove most cases of the `using` param from lookups where the params are enough
to determine which shard to use.


Shard Storage Decorator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A decorator used to mark which models store the shard and which shard group to
use:

::

  def shard_storage_config(shard_group='default', shared_field='shard'):
      def configure(cls):
          setattr(cls, 'django_sharding__shard_group', shard_group)
          setattr(cls, 'django_sharding__shard_field', shared_field)
          setattr(cls, 'django_sharding__stores_shard', True)
          return cls
      return configure


Fields
------

Note: all fields given must remove the custom kwargs from their kwargs before
calling `__init__` on `super` and replace them after calling `deconstruct` on
`super` in order to prevent these arguments from being based on to the
migration and subsequently the database.


Sharded ID Fields
-----------------

This package ships with the mixin required to create you own sharded ID fields
as well as a few basic ones.

The Sharded ID Field Mixin
^^^^^^^^^^^^^^^^^^^^^^^^^^

::

  class ShardedIDFieldMixin(object):
      """
      A field which takes an id generator class instance as an
      argument and uses the generator to assign each new object
      a unique id.
      """
      def __init__(self, *args, **kwargs):
          # Remove the strategy from the kwargs so that it doesn't
          # get passed to Django.
          setattr(self, 'strategy', kwargs['strategy'])
          del kwargs['strategy']
          return super(ShardedIDFieldMixin, self).__init__(
              *args, **kwargs
          )

      def deconstruct(self):
          name, path, args, kwargs = super(
              ShardedIDFieldMixin, self
          ).deconstruct()

          # Add the strategy from the kwargs so that it does get
          # passed to our model.
          kwargs['strategy'] = getattr(self, 'strategy')
          return name, path, args, kwargs

      def get_pk_value_on_save(self, instance):
          if not instance.pk:
              return self.strategy.get_next_id()
          return instance.pk


UUID4 Sharded ID Field
^^^^^^^^^^^^^^^^^^^^^^

This is an exmaple using the above mixin to generate a uuid and
use that uuid in combination with the shard to generate a unique
ID.

::

  class ShardedUUID4Field(ShardedIDFieldMixin, CharField):
      def __init__(self, *args, **kwargs):
          from app.shardng_strategies import UUIDStrategy
          kwargs['strategy'] = UUIDStrategy()
          return super(ShardedUUID4Field, self).__init__(
              *args, **kwargs
          )

      def get_pk_value_on_save(self, instance):
          shard = instance.get_shard()
          return self.strategy.get_next_id(shard)


Sharded Storage Field
---------------------

The most common use case is to store the shard on one of the
models. Included in this package is a mixin that helps do that.


Storing The Shard On The Same Object: Shard Storage CharField
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For example, in this case we will be storing the shard in a
`CharField` but we could have used another type of field.

The field takes the `shard_group` as a key word argument and sets
the field up to makes use of a signal to save the shard (which we
will go into later).

::

  class ShardStorageFieldMixin(object):
      """
      A mixin for a field used to store a shard for in
      an instance or parent of an instance.
      """
      def __init__(self, *args, **kwargs):
          setattr(
              self, 'django_sharding__stores_shard', True
          )
          setattr(
              self,
              'django_sharding__shard_group',
              kwargs['shard_group']
          )
          del kwargs['shard_group']
          return super(ShardStorageFieldMixin, self).__init__(
              *args, **kwargs
          )

      def deconstruct(self):
          name, path, args, kwargs = super(
              ShardStorageFieldMixin, self
          ).deconstruct()
          kwargs['shard_group'] = getattr(
              self, 'django_sharding__shard_group'
          )
          return name, path, args, kwargs


  class ShardLocalStorageFieldMixin(ShardStorageFieldMixin):
      """
      The ShardLocalStorageFieldMixin is used for when the shard
      is stored on the model that is being sharded by.
      i.e. Storing the shard on the User model and sharding by
      the User.
      """
      def __init__(self, *args, **kwargs):
          setattr(self, 'django_sharding__use_signal', True)
          return super(
              ShardLocalStorageFieldMixin, self
          ).__init__(*args, **kwargs)

      def deconstruct(self):
          return super(
              ShardLocalStorageFieldMixin, self
          ).deconstruct()


  class ShardStorageCharField(ShardLocalStorageFieldMixin, CharField):
      """
      A simple char field that stores a shard and uses a signal
      to generate the shard using a pre_save signal.
      """
      pass


Storing The Shard On Another Model Shard Foreign Key Storage Field
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As an example, say we have a webapp that serves all TD banks and
we wish to store all the branches within a district under the same
shard.

We could store the shard on the district but perhaps we don't
usually touch the district or need to check it and would rather
store the shard on the branch itself but still shard by district.

One solution is to use a unqiue `shard_key` field on another table
to store the shards and create a foreign key to that table. That
implimentation has been included in this library.

We will use the method `pre_save` to store the shard. Notice once
again that we are loading the strategy from the AppConfig, which
we will go through soon.


::

  class ShardFKStorageFieldMixin(ShardStorageFieldMixin):
      """
      A mixin for a field used to store a foreign key to another
      table which stores the shard, usually a table which inherits
      from the ShardStorageModel.
      """
      def __init__(self, *args, **kwargs):
          setattr(self, 'django_sharding__stores_shard', True)
          model_class = kwargs.get('to', args and args[0])
          if type(model_class) == str:
              app_label = model_class.split('.')[0]
              app = apps.get_app_config(app_label)
              model_class = app.get_model(
                  model_class[len(app_label) + 1:]
              )
          setattr(
              self,
              'django_sharding__shard_storage_table',
              model_class
          )
          return super(
              ShardFKStorageFieldMixin, self
          ).__init__(*args, **kwargs)

      def pre_save(self, model_instance, add):
          result = super(
              ShardFKStorageFieldMixin, self
          ).pre_save(model_instance, ad)
          self.save_shard(model_instance)
          return result

      def save_shard(self, model_instance):
          shard_key = model_instance.get_shard_key()
          if not getattr(model_instance, self.name):
              storage_table = getattr(
                  self, 'django_sharding__shard_storage_table'
              )
              shard_group = getattr(
                  self, 'django_sharding__shard_group'
              )

              sharding_app = apps.get_app_config('django_sharding')
              bucketer = sharding_app.get_bucketer(shard_group)
              shard = bucketer.pick_shard(model_instance)
              shard_object, _ = storage_table.objects.get_or_create(
                  shard_key=shard_key
              )
              if not shard_object.shard:
                  shard_object.shard = shard
                  shard_object.save()
              setattr(model_instance, self.name, shard_object)


  class ShardFKStorageField(ShardFKStorageFieldMixin, ForeignKey):
      """
      A simple char field that stores a shard and uses a signal
      to generate the shard using a pre_save signal.
      """
      pass


Models
------

Several models are included to help with sharding your applications.

Shard By Mixin
^^^^^^^^^^^^^^

A mixin which add a field to shard by to a model. This also flags
the model to use the included signal (unless the settings is set
to off) to save the shard automatically to this field.

::

  def _get_primary_shards():
      """
      Returns the names of databases which make up the shards
      and have no primary.
      """
      return [
          database_name for (database_name, db_settings) in
          settings.DATABASES.items()
          if not db_settings.get('PRIMARY', None) and
          db_settings.get('SHARD_GROUP', None)
      ]

  class ShardedByMixin(models.Model):
      django_sharding__shard_field = 'shard'
      django_sharding__stores_shard = True

      SHARD_CHOICES = ((i, i) for i in _get_primary_shards())

      shard = models.CharField(
          max_length=120, blank=True,
          null=True, choices=SHARD_CHOICES
      )

      class Meta:
          abstract = True


Table Strategy Model
^^^^^^^^^^^^^^^^^^^^

Before when we talked about the `TableShardedIDField` for using
an auto-incriment field to generate unique IDs for items, we
required a table to store that information as an argument to
that field. Such a table is included to inherit from:

::

  class TableStrategyModel(models.Model):
      id = BigAutoField(primary_key=True)
      stub = models.NullBooleanField(
          null=True, default=True, unique=True
      )

      class Meta:
          abstract = True



Shard Storage Mixin
^^^^^^^^^^^^^^^^^^^

Before when we talked about the `ShardForeignKeyStorageField`, we
discussed needing a table to store the shard that uses a
`shard_key` as a primary key on that table to ensure the
`shard_key` will only ever be assigned a single shard.

Here's an included version of that table to inherit from:

::

  class ShardStorageModel(models.Model):
      SHARD_CHOICES = ((i, i) for i in _get_primary_shards())

      shard = models.CharField(
          max_length=120, choices=SHARD_CHOICES
      )
      shard_key = models.CharField(
          primary_key=True, max_length=120
      )

      class Meta:
          abstract = True


Signals
-------

We include one signal in the library which uses the attributes
added by the other components in order to save shards to models
when they are created.

The `magic` part which automatically runs this is in the app
config which is the last component we'll discuss.


::

  def save_shard_handler(sender, instance, **kwargs):
      sharding_app = apps.get_app_config('django_sharding')
      bucketer = sharding_app.get_bucketer(sender.shard_group)

      conditional_name = 'django_sharding__stores_shard'
      shard_fields = list(filter(
          lambda field: getattr(field, conditional_name, False),
          sender._meta.fields
      ))

      location_name = 'django_sharding__shard_field'
      if len(shard_fields) != 1:
          shard_field_name = getattr(sender, location_name, None)
          shard_fields = list(filter(
              lambda field: field.name == shard_field_name,
              sender._meta.fields
          ))

      if not any(shard_fields):
          return

      if len(shard_fields) > 1:
          raise Exception(
              'The model {} has multuple fields '
              'for shard storage: {}'.format(
                  sender, shard_fields
              )
          )
      shard_field = shard_fields[0]
      if not getattr(instance, shard_field.name, None):
          shard = bucketer.pick_shard(instance)
          setattr(instance, shard_field.name, shard)


The App Config
--------------

In order to automate the magic for most users, there is an
included app configuration in the `django_shard` app. We'll go
through it in steps.

First it grabs the shard information and initializes the
strategies chosen by the user. This is done through the settings
which we'll go through in the installation step.


::

  shard_settings = getattr(
      settings, 'DJANGO_SHARDING_SETTINGS', {}
  )
  shard_groups = [
      settings.DATABASES[db_settings]['SHARD_GROUP']
      for db_settings in settings.DATABASES
  ]
  shard_groups = set(
      filter(lambda group: group is not None, shard_groups)
  )
  self.bucketers = {}
  self.routing_strategies = {}
  for shard_group in shard_groups:
      group_settings = shard_settings.get(shard_group, {})
      self.bucketers[shard_group] = group_settings.get(
          'BUCKETING_STRATEGY',
          RoundRobinBucketingStrategy(
              shard_group=shard_group, databases=settings.DATABASES
          )
      )
      self.routing_strategies[shard_group] = group_settings.get(
          'ROUTING_STRATEGY',
          PrimaryOnlyRoutingStrategy(databases=settings.DATABASES)
      )


Then, once the strategies are known for each of the shard groups,
the models that each shard group are sharded on are examined.

When a sharded model is found, it is assumed that the developer
wanted the signal to be added to automatically save the shard to
the item of the items you're sharding by. For example, a User with
a shard field will automatically have the shard saved to the user
unless set to not do so.

::

  for model in apps.get_models():
      shard_group = getattr(
          model, 'django_sharding__shard_group', None
      )
      stores_shard = getattr(
          model, 'django_sharding__stores_shard', False
      )

      if stores_shard and shard_group:
          shard_field = getattr(
              model, 'django_sharding__shard_field', None
          )
          if not shard_field:
              raise Exception(
                  'The model {} must have a `shard_field` '
                  'attribute'.format(model)
              )
      else:
          shard_fields = filter(
              lambda field: getattr(
                  field, 'django_sharding__stores_shard', False
              ),
              model._meta.fields
          )
          if not any(shard_fields):
              continue

          if len(shard_fields) > 1:
              raise Exception(
                  'The model {} has multuple fields for shard '
                  'storage: {}'.format(
                      model, shard_fields)
                  )
          shard_field = shard_fields[0]
          shard_group = getattr(
              shard_field, 'django_sharding__shard_group', None
          )

          if not shard_group:
              raise Exception(
                  'The model {} with the shard field must have '
                  'a `shard_group` attribute'.format(model)
              )

          if not getattr(
              shard_field, 'django_sharding__use_signal', False
          ):
              continue

      group_settings = shard_settings.get(shard_group, {})
      if group_settings.get('SKIP_ADD_SHARDED_SIGNAL', False):
          continue

      receiver(
          models.signals.pre_save, sender=model
      )(save_shard_handler)


In order to later retrieve these strategies, two functions are
added to the app configuration so that any other code can
access them:

::

  class ShardingConfig(AppConfig):
      name = 'django_sharding'

      def ready(self):
          pass  # The above code went in here.

      def get_routing_strategy(self, shard_group):
          return self.routing_strategies[shard_group]

      def get_bucketer(self, shard_group):
          return self.bucketers[shard_group]
