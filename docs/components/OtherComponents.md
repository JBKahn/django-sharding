# Other Components

A quick run through of some of the other components shipped with the library.

### Decorators

#### Model Configuration Decorator

Provided in the library is a way to specify that a model is sharded or that a model is stored on a database other than the default database. A sharded model verifies that it's primary key inherits from a base mixin to ensure that the primary key has been chosen carefully and the developer is not accidentally using the deafult primary key field.

```python
def model_config(shard_group=None, database=None):
    """
    A decorator for marking a model as being either sharded or stored on a
    particular database. When sharding, it does some verification to ensure
    that the model is defined correctly.
    """
    def configure(cls):
        if database and shard_group:
            raise ShardedModelIntializationException(
                'A model cannot be both sharded and stored on a particular database.'
            )

        if not database and not shard_group:
            raise ShardedModelIntializationException(
                'The model should be either sharded or stored on a database '
                'in the `model_config` decorator is used.'
            )

        if database:
            if not settings.DATABASES.get(database, {}).get('PRIMARY'):
                raise NonExistantDatabaseException(
                    'Unable to place {} in {} as that is not an existing primary '
                    'database in the system.'.format(cls._meta.model_name, database)
                )
            setattr(cls, 'django_sharding__database', database)

        if shard_group:
            sharded_fields = filter(
                lambda field: issubclass(type(field), ShardedIDFieldMixin),
                cls._meta.fields
            )
            if not sharded_fields:
                raise ShardedModelIntializationException(
                    'All sharded models require a ShardedIDFieldMixin.'
                )

            if not filter(lambda field: field == cls._meta.pk, sharded_fields):
                raise ShardedModelIntializationException(
                    'All sharded models require the ShardedAutoIDField to be the '
                    'primary key. Set primary_key=True on the field.'
                )

            if not callable(getattr(cls, 'get_shard', None)):
                raise ShardedModelIntializationException(
                    'You must define a get_shard method on the sharded model.'
                )

            setattr(cls, 'django_sharding__shard_group', shard_group)
            setattr(cls, 'django_sharding__is_sharded', True)

        return cls
    return configure
```

### Fields

Note: all fields given must remove the custom kwargs from their kwargs before calling `__init__` on `super` and replace them after calling `deconstruct` on `super` in order to prevent these arguments from being based on to the migration and subsequently the database.

#### Sharded ID Fields

This package ships with the mixin required to create you own sharded ID fields as well as a few basic ones.

##### The Sharded ID Field Mixin

```python
class ShardedIDFieldMixin(object):
    """
    A field which takes an id generator class instance as an argument and uses the
    generator to assign each new object a unique id.
    """
    def __init__(self, *args, **kwargs):
        # Remove the strategy from the kwargs so that it doesn't get passed to Django.
        setattr(self, 'strategy', kwargs['strategy'])
        del kwargs['strategy']
        return super(ShardedIDFieldMixin, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(ShardedIDFieldMixin, self).deconstruct()

        # Add the strategy from the kwargs so that it does get passed to our model.
        kwargs['strategy'] = getattr(self, 'strategy')
        return name, path, args, kwargs

    def get_pk_value_on_save(self, instance):
        if not instance.pk:
            return self.strategy.get_next_id()
        return instance.pk
```

##### Table Sharded ID Field

As an example using the above mixin, one of the included fields uses a secondary table to generate unique IDs, as discussed in the ID generation section of this guide. This takes the class of the table as an argument and impliments to strategy shipped with this package:

```python

class TableShardedIDField(ShardedIDFieldMixin, BigAutoField):
    """
    An autoincrimenting field which takes a `source_table` as an argument in
    order to generate unqiue ids for the sharded model.
    """
    def __init__(self, *args, **kwargs):
        from django_sharding_library.id_generation_strategies import TableStrategy
        kwargs['strategy'] = TableStrategy(backing_model=kwargs['source_table'])
        setattr(self, 'source_table', kwargs['source_table'])
        del kwargs['source_table']
        return super(TableShardedIDField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(TableShardedIDField, self).deconstruct()
        kwargs['source_table'] = getattr(self, 'source_table')
        return name, path, args, kwargs
```

#### Sharded Storage Field

Most people will presumably want to store shards somewhere on a model. We have provided several fields to accomplish this goal. In these docs we will go over an example of storing the shard on the object you're storing them on as well as storing them on another object.

##### Storing The Shard On The Same Object: Shard Storage CharField

For example, in this case we will be storing the shard in a `CharField` but as you can see, we could have used another type of field. The field takes the `shard_group` as a key word argument and sets the field up to use a signal to save the shard. Later on we will go over the signal and how to bypass it. For now, note that the signal initiates generating the shard prior to saving.

```python
class ShardStorageFieldMixin(object):
    """
    A mixin for a field used to store a shard for in an instance or parent of
    an instance.
    """
    def __init__(self, *args, **kwargs):
        setattr(self, 'django_sharding__stores_shard', True)
        setattr(self, 'django_sharding__shard_group', kwargs['shard_group'])
        del kwargs['shard_group']
        return super(ShardStorageFieldMixin, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(ShardStorageFieldMixin, self).deconstruct()
        kwargs['shard_group'] = getattr(self, 'django_sharding__shard_group')
        return name, path, args, kwargs


class ShardLocalStorageFieldMixin(ShardStorageFieldMixin):
    """
    The ShardLocalStorageFieldMixin is used for when the shard is stored on the model
    that is being sharded by. i.e. Storing the shard on the User model and sharding by
    the User.
    """
    def __init__(self, *args, **kwargs):
        setattr(self, 'django_sharding__use_signal', True)
        return super(ShardLocalStorageFieldMixin, self).__init__(*args, **kwargs)

    def deconstruct(self):
        return super(ShardLocalStorageFieldMixin, self).deconstruct()


class ShardStorageCharField(ShardLocalStorageFieldMixin, CharField):
    """
    A simple char field that stores a shard and uses a signal to generate
    the shard using a pre_save signal.
    """
    pass
```

##### Storing The Shard On Another Model Shard Foreign Key Storage Field

As an example, say we have a webapp that serves all TD banks and we wish to store all the branches within a district under the same shard. We could store the shard on the district but perhaps we don't usually touch the district or need to check it and would rather store the shard on the branch itself but still shard by district. One solution is to use a unqiue `shard_key` field on another table to store the shards and create a foreign key to that table. That implimentation has been included in this library.

As before, we simply store additional data in `__init__` and then retreive stored args and kwargs in `deconstruct`. In this case, we will make use of the `ForeignKey` field's args as well as the `shard_group` from our previous mixin.

After which, we will create a method on pre_save to store the shard. Notice once again that we are loading the strategy from the AppConfig, which we will go through soon.

```python
class ShardForeignKeyStorageFieldMixin(ShardStorageFieldMixin):
    """
    A mixin for a field used to store a foreign key to another table which
    stores the shard, usually a table which inherits from the ShardStorageModel.
    """
    def __init__(self, *args, **kwargs):
        setattr(self, 'django_sharding__stores_shard', True)
        model_class = kwargs.get('to', args and args[0])
        if type(model_class) == str:
            app_label = model_class.split('.')[0]
            app = apps.get_app_config(app_label)
            model_class = app.get_model(model_class[len(app_label) + 1:])
        setattr(self, 'django_sharding__shard_storage_table', model_class)
        return super(ShardForeignKeyStorageFieldMixin, self).__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        result = super(ShardForeignKeyStorageFieldMixin, self).pre_save(
            model_instance, ad)
        self.save_shard(model_instance)
        return result

    def save_shard(self, model_instance):
        shard_key = model_instance.get_shard_key()
        if not getattr(model_instance, self.name):
            shard_storage_table = getattr(self, 'django_sharding__shard_storage_table')
            shard_group = getattr(self, 'django_sharding__shard_group')

            bucketer = apps.get_app_config('django_sharding').get_bucketer(shard_group)
            shard = bucketer.pick_shard(model_instance)
            shard_object, _ = shard_storage_table.objects.get_or_create(
                shard_key=shard_key
            )
            if not shard_object.shard:
                shard_object.shard = shard
                shard_object.save()
            setattr(model_instance, self.name, shard_object)


class ShardForeignKeyStorageField(ShardForeignKeyStorageFieldMixin, ForeignKey):
    """
    A simple char field that stores a shard and uses a signal to generate
    the shard using a pre_save signal.
    """
    pass
```

### Models

Several models are included to help with sharding your applications.

#### Shard By Mixin

A mixin which add a field to shard by to the model. This also flags the model to use the included signal (unless the settings is set to off) to save the shard automatically to this field.

```python
def _get_primary_shards():
    """
    Returns the names of databases which make up the shards and have no primary.
    """
    return [
        database_name for (database_name, db_settings) in settings.DATABASES.viewitems()
        if not db_settings.get('PRIMARY', None) and db_settings.get('SHARD_GROUP', None)
    ]

class ShardedByMixin(models.Model):
    django_sharding__shard_field = 'shard'
    django_sharding__stores_shard = True

    SHARD_CHOICES = ((i, i) for i in _get_primary_shards())

    shard = models.CharField(
        max_length=120, blank=True, null=True, choices=SHARD_CHOICES
    )

    class Meta:
        abstract = True
```

#### Table Stragey Model

Before when we talked about the `TableShardedIDField` for using an auto-incriment field to generate unique IDs for items, we required a table to store that information as an argument to that field. Sucha table is included to inherit from:

```python
class TableStrategyModel(models.Model):
    id = BigAutoField(primary_key=True)
    stub = models.NullBooleanField(null=True, default=True, unique=True)

    class Meta:
        abstract = True
```

#### Shard Storage Mixin

Before when we talked about the `ShardForeignKeyStorageField`, we discussed needing a table to store those shards in which uses a shard_key as a primary key on that table to ensure the shard_key will only ever be assigned a single shard. Here's an included version of that table to inherit from:

```python
class ShardStorageModel(models.Model):
    SHARD_CHOICES = ((i, i) for i in _get_primary_shards())

    shard = models.CharField(max_length=120, choices=SHARD_CHOICES)
    shard_key = models.CharField(primary_key=True, max_length=120)

    class Meta:
        abstract = True
```

### Signals

We include one signal in the library which uses the attributes added by the other components in order to save shards to models when they are created. The `magic` part which automattically runs this is in the app config which is the last component we'll discuss.

```python
def save_shard_handler(sender, instance, **kwargs):
    bucketer = apps.get_app_config('django_sharding').get_bucketer(sender.shard_group)
    shard_fields = filter(
        lambda field: getattr(field, 'django_sharding__stores_shard', False),
        sender._meta.fields
    )
    if len(shard_fields) != 1:
        shard_field_name = getattr(sender, 'django_sharding__shard_field', None)
        shard_fields = filter(
            lambda field: field.name == shard_field_name,
            sender._meta.fields
        )

    if not any(shard_fields):
        return

    if len(shard_fields) > 1:
        raise Exception(
            'The model {} has multuple fields for shard storage: {}'.format(
                sender, shard_fields
            )
        )
    shard_field = shard_fields[0]
    if not getattr(instance, shard_field.name, None):
        setattr(instance, shard_field.name, bucketer.pick_shard(instance))
```

### The App Config

In order to automate the magic for most users, there is an included app configuration in the `django_shard` app. We'll go through it in steps.

Firstly, it grabs the shard information and initializes the strategies chosen by the user through the settings which we'll go through in the installation step.

```python
shard_settings = getattr(settings, 'DJANGO_FRAGMENTS_SHARD_SETTINGS', {})
shard_groups = [
    settings.DATABASES[db_settings]['SHARD_GROUP'] for db_settings in settings.DATABASES
]
shard_groups = set(filter(lambda group: group is not None, shard_groups))

self.bucketers = {}
self.routing_strategies = {}
for shard_group in shard_groups:
    group_settings = shard_settings.get(shard_group, {})
    self.bucketers[shard_group] = group_settings.get(
        'BUCKETING_STRATEGY',
        RoundRobinBucketingStrategy(shard_group='default', databases=settings.DATABASES)
    )
    self.routing_strategies[shard_group] = group_settings.get(
        'ROUTING_STRATEGY',
        PrimaryOnlyRoutingStrategy(databases=settings.DATABASES)
    )
```

Then, once the strategies are known for each of the shard groups, the models that each shard group are sharded on are examined.

When a sharded model is found, it is assumed that the developer wanted the signal to be added to automatically save the shard to the item of the items you're sharding by. For example, a User with a shard field will automatically have the shard saved to the user unless set to not do so.

```python
        for model in apps.get_models():
            shard_group = getattr(model, 'django_sharding__shard_group', None)
            if getattr(model, 'django_sharding__stores_shard', False) and shard_group:
                shard_field = getattr(model, 'django_sharding__shard_field', None)
                if not shard_field:
                    raise Exception(
                        'The model {} must have a `shard_field` attribute'.format(model)
                    )
            else:
                shard_fields = filter(
                    lambda field: getattr(field, 'django_sharding__stores_shard', False),
                    model._meta.fields
                )
                if not any(shard_fields):
                    continue

                if len(shard_fields) > 1:
                    raise Exception(
                        'The model {} has multuple fields for shard storage: {}'.format(
                            model, shard_fields)
                        )
                shard_field = shard_fields[0]
                shard_group = getattr(shard_field, 'django_sharding__shard_group', None)

                if not shard_group:
                    raise Exception(
                        'The model {} with the shard field must have a `shard_group`'
                        ' attribute'.format(model)
                    )

                if not getattr(shard_field, 'django_sharding__use_signal', False):
                    continue

            group_settings = shard_settings.get(shard_group, {})
            if group_settings.get('SKIP_ADD_SHARDED_SIGNAL', False):
                continue

            receiver(models.signals.pre_save, sender=model)(save_shard_handler)
```

In order to later retreive these strategies, two fuctions are added to the app configuration so that any other code can access them:

```python
class ShardingConfig(AppConfig):
    name = 'django_sharding'

    def ready(self):
        pass  # The above code went in here.

    def get_routing_strategy(self, shard_group):
        return self.routing_strategies[shard_group]

    def get_bucketer(self, shard_group):
        return self.bucketers[shard_group]
```