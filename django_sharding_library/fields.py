from django.apps import apps
from django.conf import settings
from django.db.models import AutoField, CharField, ForeignKey, BigIntegerField, OneToOneField

from django_sharding_library.constants import Backends
from django_sharding_library.utils import create_postgres_global_sequence, create_postgres_shard_id_function, get_next_sharded_id

try:
    from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper
except ImportError:
    from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper as PostgresDatabaseWrapper

try:
    from django.db.models import BigAutoField
except ImportError:
    from django.utils.translation import ugettext_lazy as _

    class BigAutoField(AutoField):
        description = _("Big (8 byte) integer")

        def db_type(self, connection):
            if connection.settings_dict['ENGINE'] in Backends.MYSQL:
                return 'serial'
            if connection.settings_dict['ENGINE'] in Backends.POSTGRES:
                return 'bigserial'
            return super(BigAutoField, self).db_type(connection)

        def rel_db_type(self, connection):
            return BigIntegerField().db_type(connection=connection)


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
    An autoincrimenting field which takes a `source_table_name` as an argument in
    order to generate unqiue ids for the sharded model.  i.e. `app.model_name`.
    """
    def __init__(self, *args, **kwargs):
        from django_sharding_library.id_generation_strategies import TableStrategy
        kwargs['strategy'] = TableStrategy(backing_model_name=kwargs['source_table_name'])
        setattr(self, 'source_table_name', kwargs['source_table_name'])
        del kwargs['source_table_name']
        return super(TableShardedIDField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(TableShardedIDField, self).deconstruct()
        kwargs['source_table_name'] = getattr(self, 'source_table_name')
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

            app_config_app_label = getattr(settings, 'DJANGO_SHARDING_SETTINGS', {}).get('APP_CONFIG_APP', 'django_sharding')
            bucketer = apps.get_app_config(app_config_app_label).get_bucketer(shard_group)
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


class BasePostgresShardGeneratedIDField(object):

    def __init__(self, *args, **kwargs):

        if not hasattr(settings, 'SHARD_EPOCH'):
            raise ValueError("PostgresShardGeneratedIDField requires a SHARD_EPOCH to be defined in your settings file.")

        return super(BasePostgresShardGeneratedIDField, self).__init__(*args, **kwargs)

    @staticmethod
    def migration_receiver(*args, **kwargs):
        sequence_name = "global_id_sequence"
        db_alias = kwargs.get('using')
        if not db_alias:
            raise EnvironmentError("A pre-migration receiver did not receive a database alias. "
                                   "Perhaps your app is not registered correctly?")
        if settings.DATABASES[db_alias]['ENGINE'] in Backends.POSTGRES:
            shard_id = settings.DATABASES[db_alias].get('SHARD_ID', 0)
            create_postgres_global_sequence(sequence_name, db_alias, True)
            create_postgres_shard_id_function(sequence_name, db_alias, shard_id)


class PostgresShardGeneratedIDAutoField(BasePostgresShardGeneratedIDField, BigAutoField):
    """
    A field that uses a Postgres stored procedure to return an ID generated on the database.
    """
    def db_type(self, connection, *args, **kwargs):
        if connection.vendor == PostgresDatabaseWrapper.vendor:
            return "bigint DEFAULT next_sharded_id()"
        else:
            return super(PostgresShardGeneratedIDAutoField, self).db_type(connection)


class PostgresShardGeneratedIDField(BasePostgresShardGeneratedIDField, BigIntegerField):
    """
    A field that uses a Postgres stored procedure to return an ID generated on the database.

    Generates them prior to save with a seperate call to the DB.
    """

    def get_shard_from_id(self, instance_id):
        group = getattr(self, 'django_sharding__shard_group', None)
        shard_id_to_find = int(bin(instance_id)[-23:-10], 2)  # We know where the shard id is stored in the PK's bits.

        # We can check the shard id from the PK against the shard ID in the databases config
        for alias, db_settings in settings.DATABASES.items():
            if db_settings["SHARD_GROUP"] == group and db_settings["SHARD_ID"] == shard_id_to_find:
                return alias

        return None  # Return None if we could not determine the shard so we can fall through to the next shard grab attempt

    def get_pk_value_on_save(self, instance):
        return self.generate_id(instance)

    def pre_save(self, model_instance, add):
        if getattr(model_instance, self.attname, None) is not None:
            return super(PostgresShardGeneratedIDField, self).pre_save(model_instance, add)
        value = self.generate_id(model_instance)
        setattr(model_instance, self.attname, value)
        return value

    @staticmethod
    def generate_id(instance):
        shard = instance._state.db or instance.get_shard()
        return get_next_sharded_id(shard)


class PostgresShardForeignKey(ForeignKey):
    def db_type(self, connection):
        # The database column type of a ForeignKey is the column type
        # of the field to which it points. An exception is if the ForeignKey
        # points to an AutoField/PositiveIntegerField/PositiveSmallIntegerField,
        # in which case the column type is simply that of an IntegerField.
        # If the database needs similar types for key fields however, the only
        # thing we can do is making AutoField an IntegerField.
        rel_field = self.target_field
        if rel_field.get_internal_type() == "BigIntegerField":
            return BigIntegerField().db_type(connection=connection)
        return super(PostgresShardForeignKey, self).db_type(connection)


class PostgresShardOneToOne(OneToOneField):
    def db_type(self, connection):
        # The database column type of a ForeignKey is the column type
        # of the field to which it points. An exception is if the ForeignKey
        # points to an AutoField/PositiveIntegerField/PositiveSmallIntegerField,
        # in which case the column type is simply that of an IntegerField.
        # If the database needs similar types for key fields however, the only
        # thing we can do is making AutoField an IntegerField.
        rel_field = self.target_field
        if rel_field.get_internal_type() == "BigIntegerField":
            return BigIntegerField().db_type(connection=connection)
        return super(PostgresShardOneToOne, self).db_type(connection)
