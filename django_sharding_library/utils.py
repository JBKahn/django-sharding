from django.db import connections, DatabaseError, transaction
from django.conf import settings
from django_sharding_library.sql import postgres_shard_id_function_sql
from django.db.models import signals


def create_postgres_global_sequence(sequence_name, db_alias, reset_sequence=False):
    cursor = connections[db_alias].cursor()
    sid = transaction.savepoint(db_alias)
    try:
        cursor.execute("CREATE SEQUENCE %s;" % sequence_name)
    except DatabaseError:
        transaction.savepoint_rollback(sid, using=db_alias)
        if reset_sequence:
            cursor.execute("SELECT setval('%s', 1, false)" % (sequence_name,))
    else:
        print('Created sequence %s on %s' % (sequence_name, db_alias))
        transaction.savepoint_commit(sid, using=db_alias)
    cursor.close()


def create_postgres_shard_id_function(sequence_name, db_alias, shard_id):
    cursor = connections[db_alias].cursor()
    sid = transaction.savepoint(db_alias)
    try:
        cursor.execute(postgres_shard_id_function_sql,  {'shard_epoch': settings.SHARD_EPOCH,
                                                         'shard_id': shard_id,
                                                         'sequence_name': sequence_name})
    except DatabaseError:
        transaction.savepoint_rollback(sid, using=db_alias)
    else:
        print('Created shard id generator function on %s' % (db_alias, ))
        transaction.savepoint_commit(sid, using=db_alias)
    cursor.close()


def register_migration_signal_for_model_receiver(model, function, dispatch_uid=None):
    signals.pre_migrate.connect(function, sender=model, dispatch_uid=dispatch_uid)


