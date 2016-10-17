from django.db import connections, DatabaseError, transaction
from django.conf import settings
from django_sharding_library.sql import postgres_shard_id_function_sql
from django.db.models import signals

from django_sharding_library.exceptions import DjangoShardingException


def create_postgres_global_sequence(sequence_name, db_alias, reset_sequence=False):
    cursor = connections[db_alias].cursor()
    sid = transaction.savepoint(db_alias)
    create_sequence_if_not_exists_sql = """DO
$$
BEGIN
        CREATE SEQUENCE %s;
EXCEPTION WHEN duplicate_table THEN
        -- do nothing, it's already there
END
$$ LANGUAGE plpgsql;"""
    try:
        cursor.execute(create_sequence_if_not_exists_sql % sequence_name)
    except DatabaseError:
        transaction.savepoint_rollback(sid, using=db_alias)
    else:
        transaction.savepoint_commit(sid, using=db_alias)
    if reset_sequence:
        cursor.execute("SELECT setval('%s', 1, false)" % (sequence_name,))
    cursor.close()


def create_postgres_shard_id_function(sequence_name, db_alias, shard_id):
    cursor = connections[db_alias].cursor()
    cursor.execute(postgres_shard_id_function_sql % {'shard_epoch': settings.SHARD_EPOCH,
                                                     'shard_id': shard_id,
                                                     'sequence_name': sequence_name})
    cursor.close()


def verify_postres_id_field_setup_correctly(sequence_name, db_alias, function_name):
    cursor = connections[db_alias].cursor()
    cursor.execute(
        "SELECT count(*) FROM pg_class c WHERE c.relkind = '%s' and c.relname = '%s';" % ('S', sequence_name)
    )

    if cursor.fetchone()[0] == 0:
        cursor.close()
        return False

    cursor.execute(
        "SELECT count(*) from pg_proc p where p.proname = '%s';" % (function_name,)
    )

    if cursor.fetchone()[0] == 0:
        cursor.close()
        return False

    cursor.close()
    return True


def register_migration_signal_for_model_receiver(model, function, dispatch_uid=None):
    signals.pre_migrate.connect(function, sender=model, dispatch_uid=dispatch_uid)


def is_model_class_on_database(model, database):
    specific_database = getattr(model, 'django_sharding__database', None)
    is_sharded = getattr(model, 'django_sharding__is_sharded', False)

    if specific_database and is_sharded:
        raise DjangoShardingException('Model marked as both sharded and on a single database, unable to determine where to run migrations for {}.'.format(model.__class__.__name__))

    if specific_database:
        return getattr(model, 'django_sharding__database') == database

    if is_sharded:
        shard_group = getattr(model, 'django_sharding__shard_group', None)
        if shard_group:
            return settings.DATABASES[database]['SHARD_GROUP'] == shard_group
        raise DjangoShardingException("Unable to determine what database the model is on as the shard group of {} is unknown.".format(model.__class__.__name__))

    return database == "default"


def get_possible_databases_for_model(model):
    return [
        database for database in settings.DATABASES
        if is_model_class_on_database(model=model, database=database)
    ]


def get_database_for_model_instance(instance):
    if instance._state.db:
        return instance._state.db

    model = instance._meta.model
    possible_databases = get_possible_databases_for_model(model=model)
    if len(possible_databases) == 1:
        return possible_databases[0]
    elif len(possible_databases) == 0:
        pass
    else:
        model_has_sharded_id_field = getattr(model, 'django_sharding__sharded_by_field', None) is not None

        if model_has_sharded_id_field:
            sharded_by_field_id = getattr(instance, getattr(model, 'django_sharding__sharded_by_field', 'django_sharding__none'), None)
            if sharded_by_field_id is not None:
                return model.get_shard_from_id(sharded_by_field_id)

        return instance.get_shard()

    raise DjangoShardingException("Unable to deduce datbase for model instance")


def get_next_sharded_id(shard):
    cursor = connections[shard].cursor()
    cursor.execute("SELECT next_sharded_id();")
    generated_id = cursor.fetchone()
    cursor.close()

    return generated_id[0]
