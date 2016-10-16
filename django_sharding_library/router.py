from django.apps import apps
from django.conf import settings

from django_sharding_library.fields import BasePostgresShardGeneratedIDField
from django_sharding_library.exceptions import DjangoShardingException, InvalidMigrationException
from django_sharding_library.utils import (
    is_model_class_on_database,
    get_database_for_model_instance,
    get_possible_databases_for_model,
)


class ShardedRouter(object):
    """
    A router that is shard-aware and will prevent running migrations on
    the wrong database as well as infer, when possible, which database to
    read or write from.
    """

    def get_shard_for_instance(self, instance):
        return instance._state.db or instance.get_shard()

    def get_shard_for_id_field(self, model, sharded_by_field_id):
        try:
            return model.get_shard_from_id(sharded_by_field_id)
        except Exception:
            # This is overly broad on purpose: we dont know what a user might try to do to get a shard from an ID (our
            # example is a .get(), but someone could do anything) and if it excepts, we want to fall back to the next
            # attempt at grabbing a shard based on other potential filters
            return None

    def get_shard_for_postgres_pk_field(self, model, pk_value):
        group = getattr(model, 'django_sharding__shard_group', None)
        shard_id_to_find = int(bin(pk_value)[-23:-10], 2)  # We know where the shard id is stored in the PK's bits.

        # We can check the shard id from the PK against the shard ID in the databases config
        for alias, db_settings in settings.DATABASES.items():
            if db_settings["SHARD_GROUP"] == group and db_settings["SHARD_ID"] == shard_id_to_find:
                return alias

        return None  # Return None if we could not determine the shard so we can fall through to the next shard grab attempt

    def get_read_db_routing_strategy(self, shard_group):
        app_config_app_label = getattr(settings, 'DJANGO_SHARDING_SETTINGS', {}).get('APP_CONFIG_APP', 'django_sharding')
        return apps.get_app_config(app_config_app_label).get_routing_strategy(shard_group)

    def _get_shard(self, model, **hints):
        shard = None

        model_has_sharded_id_field = getattr(model, 'django_sharding__sharded_by_field', None) is not None

        #####
        #
        # This is setup as multiple IF statements on purpose. If any attempt to get a shard fails, the function that
        # tried to get the shard should return None that way the NEXT possible attempt to grab a shard can be run.
        # In this way, future ways to automatically get the correct shard can be added, and at any point in the logic,
        # and the first one to pick a valid shard will return the valid shard.
        #
        # Always return None if no valid shard was found so the default Django router will use the using() database if
        # these all fail.
        #
        #####
        if hints.get("instance", None):
            shard = get_database_for_model_instance(instance=hints["instance"])
        if shard is None and model_has_sharded_id_field:
            sharded_by_field_id = hints.get('exact_lookups', {}).get(
                getattr(model, 'django_sharding__sharded_by_field'), None
            )
            if sharded_by_field_id:
                shard = self.get_shard_for_id_field(model, sharded_by_field_id)

        is_pk_postgres_generated_id_field = issubclass(type(getattr(model._meta, 'pk')), BasePostgresShardGeneratedIDField)
        lookup_pk = hints.get('exact_lookups', {}).get('pk') or hints.get('exact_lookups', {}).get('id')

        if shard is None and is_pk_postgres_generated_id_field and lookup_pk is not None:
            return self.get_shard_for_postgres_pk_field(model, lookup_pk)

        return shard

    def db_for_read(self, model, **hints):
        possible_databases = get_possible_databases_for_model(model=model)
        if len(possible_databases) == 1:
            return possible_databases[0]

        shard = self._get_shard(model, **hints)
        if shard:
            shard_group = getattr(model, 'django_sharding__shard_group', None)
            if not shard_group:
                raise DjangoShardingException('Unable to identify the shard_group for the {} model'.format(model))
            routing_strategy = self.get_read_db_routing_strategy(shard_group)
            return routing_strategy.pick_read_db(shard)
        return None

    def db_for_write(self, model, **hints):
        possible_databases = get_possible_databases_for_model(model=model)
        if len(possible_databases) == 1:
            return possible_databases[0]

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

        object1_databases = get_possible_databases_for_model(model=obj1._meta.model)
        object2_databases = get_possible_databases_for_model(model=obj2._meta.model)

        if (len(object1_databases) == len(object2_databases) == 1) and (object1_databases == object2_databases):
            return True
        return self.get_shard_for_instance(obj1) == self.get_shard_for_instance(obj2)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if settings.DATABASES[db].get('PRIMARY', None):
            return False

        # Since the API for this function is limiting in a sharded environemnt,
        # we provide an override to specify which databases to run the migrations
        # on.
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

        try:
            return is_model_class_on_database(model=model, database=db)
        except DjangoShardingException as e:
            raise InvalidMigrationException(
                e.args[0]
            )
