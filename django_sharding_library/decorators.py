from django.conf import settings

from django_sharding_library.exceptions import NonExistentDatabaseException, ShardedModelInitializationException
from django_sharding_library.fields import ShardedIDFieldMixin


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

        if shard_group:
            sharded_fields = filter(lambda field: issubclass(type(field), ShardedIDFieldMixin), cls._meta.fields)
            if not sharded_fields:
                raise ShardedModelInitializationException('All sharded models require a ShardedIDFieldMixin.')

            if not filter(lambda field: field == cls._meta.pk, sharded_fields):
                raise ShardedModelInitializationException('All sharded models require the ShardedAutoIDField to be the primary key. Set primary_key=True on the field.')

            if not callable(getattr(cls, 'get_shard', None)):
                raise ShardedModelInitializationException('You must define a get_shard method on the sharded model.')

            setattr(cls, 'django_sharding__shard_group', shard_group)
            setattr(cls, 'django_sharding__is_sharded', True)

        return cls
    return configure
