from django.conf import settings
from django.apps import apps
from django_sharding_library.constants import Backends
from django.utils.six import iteritems

from django_sharding_library.exceptions import NonExistentDatabaseException, ShardedModelInitializationException
from django_sharding_library.fields import ShardedIDFieldMixin, BasePostgresShardGeneratedIDField
from django_sharding_library.utils import register_migration_signal_for_model_receiver

PRE_MIGRATION_DISPATCH_UID = "PRE_MIGRATE_FOR_MODEL_%s"


def shard_storage_config(shard_group='default', shared_field='shard'):
    def configure(cls):
        setattr(cls, 'django_sharding__shard_group', shard_group)
        setattr(cls, 'django_sharding__shard_field', shared_field)
        setattr(cls, 'django_sharding__stores_shard', True)
        return cls
    return configure


def model_config(shard_group=None, database=None):
    """
    A decorator for marking a model as being either sharded or stored on a
    particular database. When sharding, it does some verification to ensure
    that the model is defined correctly.
    """
    def configure(cls):
        if database and shard_group:
            raise ShardedModelInitializationException('A model cannot be both sharded and stored on a particular database.')

        if not database and not shard_group:
            raise ShardedModelInitializationException('The model should be either sharded or stored on a database in the `model_config` decorator is used.')

        if database:
            if database not in settings.DATABASES or settings.DATABASES[database].get('PRIMARY'):
                raise NonExistentDatabaseException(
                    'Unable to place {} in {} as that is not an existing primary database in the system.'.format(cls._meta.model_name, database)
                )
            setattr(cls, 'django_sharding__database', database)

        postgres_shard_id_fields = list(filter(lambda field: issubclass(type(field), BasePostgresShardGeneratedIDField), cls._meta.fields))
        if postgres_shard_id_fields:
            database_dicts = [settings.DATABASES[database]] if database else [db_settings for db, db_settings in
                                                                              iteritems(settings.DATABASES) if
                                                                              db_settings["SHARD_GROUP"] == shard_group]
            if any([database_dict['ENGINE'] not in Backends.POSTGRES for database_dict in database_dicts]):
                raise ShardedModelInitializationException(
                    'You cannot use a PostgresShardGeneratedIDField on a non-Postgres database.')

            for field in postgres_shard_id_fields:
                register_migration_signal_for_model_receiver(apps.get_app_config(cls._meta.app_label),
                                                             field.migration_receiver,
                                                             dispatch_uid=PRE_MIGRATION_DISPATCH_UID % cls._meta.app_label)

        if shard_group:
            sharded_fields = list(filter(lambda field: issubclass(type(field), ShardedIDFieldMixin), cls._meta.fields))
            if not sharded_fields and not postgres_shard_id_fields:
                raise ShardedModelInitializationException('All sharded models require a ShardedIDFieldMixin or a '
                                                          'PostgresShardGeneratedIDField.')

            if not list(filter(lambda field: field == cls._meta.pk, sharded_fields + postgres_shard_id_fields)):
                raise ShardedModelInitializationException('All sharded models require a ShardedAutoIDField or '
                                                          'PostgresShardGeneratedIDField to be the primary key. Set '
                                                          'primary_key=True on the field.')

            if not callable(getattr(cls, 'get_shard', None)):
                raise ShardedModelInitializationException('You must define a get_shard method on the sharded model.')

            setattr(cls, 'django_sharding__shard_group', shard_group)
            setattr(cls, 'django_sharding__is_sharded', True)

        return cls
    return configure
