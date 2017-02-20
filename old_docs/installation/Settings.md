# Settings

### Installation

To install the package, use pypi:

```
pip install django-sharding
```

and Add the package to your installed apps:

```python
INSTALLED_APPS=[
    ...,
    "django_sharding",
],
```

### Using The Default Configuration

Refer to the configuration section (link) of the ReadMe for additional information.

Add the following to your settings file:

```python
# Most applications will not need additional routers but if you need your own then
# remember that order does matter. Read up on them here (link).
DATABASE_ROUTERS=['django_sharding_library.router.ShardedRouter'],

```

Add your databases to you settings file in the following format based on, and using, dj-database (link).
This structure supports unsharded sets of databases as well as replicates. This setting uses a single shard group,
more advanced structures are possible and checkout the other section of the docs for more information (link):

```python
DATABASES = database_configs(databases_dict={
    'unsharded_databases': [
        {
            'name': 'default',
            'environment_variable': 'DATABASE_URL',
            'default_database_url': 'postgres://user:pw@localhost/sharding'
        }
    ],
    'sharded_databases': [
        {
            'name': 'app_shard_001',
            'environment_variable': 'SHARD_001_DATABASE_URL',
            'default_database_url': 'postgres://user:pw@localhost/sharding_001',
            'replicas': [
                {
                    'name': 'app_shard_001_replica_001',
                    'environment_variable': 'REPLICA_001_DATABASE_URL',
                    'default_database_url': 'postgres://u:pw@localhost/app_1_replica_1'
                },
                {
                    'name': 'app_shard_001_replica_002',
                    'environment_variable': 'REPLICA_002_DATABASE_URL',
                    'default_database_url': 'postgres://u:pw@localhost/app_1_replica_2'
                },
            ]
        },
        {
            'name': 'app_shard_002',
            'environment_variable': 'SHARD_002_DATABASE_URL',
            'default_database_url': 'mysql://user:pw@localhost/sharding_002'
        },
    ]
})
```

### Additional Settings

There are several settings you can set that are not covered by the simple setup instructions. That may be because you want to use a different set of components than the default or wish to integrate your own with the library.

For each of the shard groups you can specify the read strategy for choosing a database to read from (from the primary and its replicates) as well as the strategy used to assign shards for this shard group.

For example, if we sharded users using the `user_shard_group`, we could choose to override the defaults for that shard group by including something like the following in the settings file:

```python
DJANGO_FRAGMENTS_SHARD_SETTINGS = {
    'user_shard_group': {
        'BUCKETING_STRATEGY': SomeCoolStrategy(
            shard_group='user_shard_group', databases=DATABASES
        ),
        'ROUTING_STRATEGY': ReadOnlyFromPrimaryDatabases(databases=DATABASES),
    }
}
```

Additionally, if you add a shard field on a model to store the shard for that object, the package will automate the process of retreiving and saving the shard on model save. You can skip automatically saving the shard to the User model in this example by adding this setting:

```python
DJANGO_FRAGMENTS_SHARD_SETTINGS = {
    'user_shard_group': {
        'SKIP_ADD_SHARDED_SIGNAL': True,
    }
}
```
