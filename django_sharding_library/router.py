import inspect

from django.apps import apps
from django.conf import settings

from django_sharding_library.exceptions import InvalidMigrationException


class ShardedRouter(object):
    """
    A router that is shard-aware and will prevent running migrations on
    the wrong database as well as infer, when possible, which database to
    read or write from.
    """
    def get_shard_group_if_sharded_or_none(self, model):
        if getattr(model, 'django_sharding__is_sharded', False):
            return getattr(model, 'django_sharding__shard_group', None)
        return None

    def get_specific_database_or_none(self, model):
        return getattr(model, 'django_sharding__database', None)

    def get_shard_for_instance(self, instance):
        return instance._state.db or instance.get_shard()

    def get_shard_for_id_field(self, model, sharded_by_field_id):
        return model.get_shard_from_id(sharded_by_field_id)

    def get_read_db_routing_strategy(self, shard_group):
        app_config_app_label = getattr(settings, 'DJANGO_SHARDING_SETTINGS', {}).get('APP_CONFIG_APP', 'django_sharding')
        return apps.get_app_config(app_config_app_label).get_routing_strategy(shard_group)

    def _get_shard(self, model, **hints):
        if self.get_shard_group_if_sharded_or_none(model):
            shard = None
            instance = hints.get('instance')
            shard_field_id = hints.get('exact_lookups', {}).get(
                getattr(model, 'django_sharding__sharded_by_field', None), None)

            if not shard_field_id and instance:
                shard_field_id = getattr(instance, getattr(model, 'django_sharding__sharded_by_field', None), None)

            if instance:
                shard = self.get_shard_for_instance(instance)
            if not shard and shard_field_id:
                try:
                    shard = self.get_shard_for_id_field(model, shard_field_id)
                except:
                    shard = self.get_shard_for_id_field(model, shard_field_id)

            return shard
        return None

    def db_for_read(self, model, **hints):
        specific_database = self.get_specific_database_or_none(model)
        if specific_database:
            return specific_database

        shard = self._get_shard(model, **hints)
        if shard:
            # TODO: remove the second, should not use the shard_group attribute anywhere anymore
            shard_group = getattr(model, 'django_sharding__shard_group', getattr(model, 'shard_group', None))
            if not shard_group:
                raise Exception('Unable to identify the shard_group for the {} model'.format(model))
            routing_strategy = self.get_read_db_routing_strategy(shard_group)
            return routing_strategy.pick_read_db(shard)
        return None

    def db_for_write(self, model, **hints):
        specific_database = self.get_specific_database_or_none(model)
        if specific_database:
            return specific_database

        shard = self._get_shard(model, **hints)

        if shard:
            db_config = settings.DATABASES[shard]
            return db_config.get('PRIMARY', shard)
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Only allow relationships between two items which are both on only one database or
        between sharded items on the same shard.
        """
        if self.get_specific_database_or_none(obj1) != self.get_specific_database_or_none(obj2):
            return False
        elif self.get_specific_database_or_none(obj1):
            return True
        if self.get_shard_group_if_sharded_or_none(type(obj1)) != self.get_shard_group_if_sharded_or_none(type(obj2)):
            return False
        elif self.get_shard_group_if_sharded_or_none(type(obj1)):
            return self.get_shard_for_instance(obj1) == self.get_shard_for_instance(obj2)
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if settings.DATABASES[db].get('PRIMARY', None):
            return False
        model_name = model_name or hints.get('model_name')
        model = hints.get('model')
        if model:
            model_name = model.__name__

        # New versions of Django use the router to make migrations with no hints.....
        making_migrations = any(['django/core/management/commands/makemigrations.py' in i[1] for i in inspect.stack()])
        if making_migrations:
            return True

        if not model_name:
            raise InvalidMigrationException(
                'Model name not provided in migration, please pass a `model_name` or `model` with the hints passed into the migration.'
            )

        # Sometimes, when extending models from another app i.e. the User Model, the app label
        # is the app label of the app where the change is defined but to app with the model is
        # passed in with the model name.
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
                'Model marked as both sharded and on a single database, unable to determine where to run migrations for {}.'.format(model_name)
            )
        if single_database:
            return db == single_database
        if shard_group:
            return settings.DATABASES[db]['SHARD_GROUP'] == shard_group
        return db == 'default'
