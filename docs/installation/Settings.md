# Settings

There are several settings you can set that are not covered by the simple setup instructions. That may be because you want to use a different set of componenets than the default or wish to integrate your own with the library.

First you must be sure to add all your databases as mentioned in the ReadMe setup instuctions. All sharded databsaes may specify a `shard_group` and will be considered `default` if it is omitted.

One that's done, for each of the shard groups you can specify the read strategy for choosing a database to read from (from the primary and it's replicates) as well as the strategy used to assign shards for this shard group.

For example, if we sharded users using the `user_shard_group`, we could choose to override the defaults for that shard group by including something like the following in the settings file:

```python
DJANGO_FRAGMENTS_SHARD_SETTINGS = {
    'user_shard_group': {
        'BUCKETING_STRATEGY': SomeCoolStrategy(
            shard_group='user_shard_group', databases=DATABASES
        ),
        'ROUTING_STRATEGY': ReadOnlyFromPrimaryDatabses(databases=DATABASES),
    }
}
```

Additionally, you can also skip automatically saving the shard to the User model in this example by adding this setting:

```python
DJANGO_FRAGMENTS_SHARD_SETTINGS = {
    'user_shard_group': {
        'SKIP_ADD_SHARDED_SIGNAL': True,
    }
}
```