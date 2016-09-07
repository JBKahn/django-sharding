from django.db import connections, DatabaseError, transaction
from django.conf import settings
from django_sharding_library.sql import postgres_shard_id_function_sql
from django.db.models import signals


def create_postgres_global_sequence(sequence_name, db_alias, reset_sequence=False):
    cursor = connections[db_alias].cursor()
    sid = transaction.savepoint(db_alias)
    create_sequence_if_not_exists_sql = """DO
$$
BEGIN
        CREATE SEQUENCE myseq;
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
