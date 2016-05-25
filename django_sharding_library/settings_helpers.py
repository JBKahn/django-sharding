from dj_database_url import config


def database_config(environment_variable, default_database_url, shard_group=None, is_replica_of=None):
    """
    Wraps dj_database_url to provide additional arguments to specify whether a database is a shard
    and if it a replica of another database.
    """
    db_config = config(env=environment_variable, default=default_database_url)
    if not db_config:
        return db_config

    db_config['TEST'] = db_config.get('TEST', {})
    db_config['SHARD_GROUP'] = shard_group

    if is_replica_of:
        db_config['PRIMARY'] = is_replica_of
        db_config['TEST']['MIRROR'] = is_replica_of

    return db_config


def database_configs(databases_dict):
    """
    Takes databases of the form:
    {
        'unsharded_databases': [
            {
                'name': 'DB01',
                'environment_variable': 'ENV',
                'default_database_url': 'postgres:://...'
            }, {
                'name': 'DB02',
               'environment_variable': 'ENV2',
                'default_database_url': 'postgres:://...',
                'replicas': [{
                    'name': 'DB02_S1',
                    'environment_variable': 'ENVS1',
                    'default_database_url': 'postgres:://...'
                }, {
                    'name': 'DB02_S2',
                    'environment_variable': 'ENVS2',
                    'default_database_url': 'postgres:://...'
                }]
            },],
        'sharded_databases': [
            {
                'name': 'SHARD_01',
                'environment_variable': 'ENV3',
                'default_database_url': 'postgres:://...',
                'shard_group': 'default',
                'replicas': [{
                    'name': 'REPLICA_SHARD_01_01',
                    'environment_variable': 'ENVS3',
                    'default_database_url': 'postgres:://...'
                    'shard_group': 'default',
                }, {
                    'name': 'REPLICA_SHARD_01_02',
                    'environment_variable': 'ENVS4',
                    'default_database_url': 'postgres:://...'
                    'shard_group': 'default',
                }]
            }, {
                'name': 'SHARD_02',
                'environment_variable': 'ENV4',
                'default_database_url': 'postgres:://...'
                'shard_group': 'default',
            },
        ]
    }
    """
    configuration = {}
    shard_id_hash = {}  # Keep track of the IDs of the shards currently. Used to help with migrations.
    for (databases, is_sharded) in [(databases_dict.get('unsharded_databases', []), False), (databases_dict.get('sharded_databases', []), True)]:
        for idx, database in enumerate(databases):
            db_config = database_config(
                database['environment_variable'],
                database['default_database_url'],
                shard_group=(is_sharded and database.get('shard_group', 'default')) or None,
                is_replica_of=None
            )
            if db_config:
                configuration[database['name']] = db_config
            for replica in database.get('replicas', []):
                db_config = database_config(
                    replica['environment_variable'],
                    replica['default_database_url'],
                    shard_group=(is_sharded and database.get('shard_group', 'default') or None),
                    is_replica_of=database['name']
                )
                if db_config:
                    configuration[replica['name']] = db_config

            # We assume the numeric shard ID is constant based on the entries in the configuration helper (we assume
            # they wont change order, and that new shards will be appended and not inserted randomly)
            # This is noted in the docs, leaving this comment for whomever may work on this in the future.
            if is_sharded:
                shard_id = shard_id_hash.get(configuration[database['name']]['SHARD_GROUP'], 0)
                configuration[database['name']]['SHARD_ID'] = shard_id
                shard_id_hash[configuration[database['name']]['SHARD_GROUP']] = shard_id + 1

    return configuration
