from django.apps import apps
from django.db.models import AutoField, CharField, ForeignKey

from django_sharding_library.constants import Backends


class BigAutoField(AutoField):
    """
    An autoincrimenting field which can store an integer from 1 to
    9223372036854775807.
    """
    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == Backends.MYSQL:
            return 'serial'
        if connection.settings_dict['ENGINE'] == Backends.POSTGRES:
            return 'bigserial'
        return super(BigAutoField, self).db_type(connection)


class ShardedIDFieldMixin(object):
    """
    An autoincrimenting field which takes an id generator class instance
    as an argument and uses the generator to assign each new object a unique
    id.
    Note: This currently must be the primary key of the model and although this
    may be updated in the future, it should not hinder the app to use other
    candidates as unique fields.
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


class ShardedUUID4Field(ShardedIDFieldMixin, CharField):
    def __init__(self, *args, **kwargs):
        from django_sharding_library.id_generation_strategies import UUIDStrategy
        kwargs['strategy'] = UUIDStrategy()
        return super(ShardedUUID4Field, self).__init__(*args, **kwargs)

    def get_pk_value_on_save(self, instance):
        return self.strategy.get_next_id(instance.get_shard())


class ShardStorageFieldMixin(object):
    """
    A mixin for a field used to store a shard for in an instance or parent of an instance.
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
    The ShardLocalStorageFieldMixin is used for when the shard is stored on the model that
    is being sharded by. i.e. Storing the shard on the User model and sharding by the User.
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

    def deconstruct(self):
        name, path, args, kwargs = super(ShardForeignKeyStorageFieldMixin, self).deconstruct()
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        self.save_shard(model_instance)
        return super(ShardForeignKeyStorageFieldMixin, self).pre_save(model_instance, add)

    def save_shard(self, model_instance):
        shard_key = model_instance.get_shard_key()
        if not getattr(model_instance, self.name):
            shard_storage_table = getattr(self, 'django_sharding__shard_storage_table')
            shard_group = getattr(self, 'django_sharding__shard_group')

            bucketer = apps.get_app_config('django_sharding').get_bucketer(shard_group)
            shard = bucketer.pick_shard(model_instance)
            shard_object, _ = shard_storage_table.objects.get_or_create(shard_key=shard_key)
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
