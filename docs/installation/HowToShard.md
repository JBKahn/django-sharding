# Choosing How To Shard

When deciding how to shard, there are several considerations to make that will impact your setup.

### Shard Groups

You can think of shard groups as distinct groups of databases so that you can limit sharded data to a subset of the shards included in your application. For example, you may have six shards in your application and use three for one item and three to store another. The `default` shard group is used when no shard groups are given in the settings file.

While you may use this library however you'd like, the author recommends that you only use the `default` shard group. This is because you will often want to do joins on the data later, when it will not be in the same set of databases, or the data is so split that it probably does not belong in the same application as the other data. In either case, it is simpler and easier to use one shard group over many.

### Storing Shards

Often you'll want to store the shard when you pick one for an instance. For example, if you were to shard your data by user then you'll want to store that shard somewhere. You'll likely want to store it on the user, but perhaps all your users have multiple Group instances and you'd like to store this data on the Group rather than the user, than that is an option too. Both are supported by the library, but you must decide where to store the shard unless your sharding function is deterministic (as discussed earlier in the component section of these docs).

### Sharding Functions

In order to shard your data, you need to decide how to pick those shards. For example, it you were to shard by User then how do you pick a shard given a User? You may choose to inspect the user or to try to balance the load across all the databases. There are multiple ways to do that and several included as discussed in the component section of these docs.

### Will I Use Replicate Databases?

To an app without replicate databases, the read strategy for a router is unimportant. However, if you have replicates then you may want to decide how to use them. You may want to read from them evenly, randomly or using a known ratio as discussed in the components section of the docs. While replicates may be useful, the author feels that you should not use them in your production environment. As discussed by [pinterest](https://engineering.pinterest.com/blog/sharding-pinterest-how-we-scaled-our-mysql-fleet) in their Design Philosophies, you then have to take into account replication lag time as well as other issues. It would be simpler and easier to just include more shards.

### Logical vs Physical Sharding

There are two types of shards you can create, logical shards and physical shards. A logical shard is splitting data into multiple databases on the same physical node. A physical shard is when splitting data across multiple nodes. It is the recommendation of the author that you start using both. The reason is that it's easier to rebalance logical shards across machines that rebalance the data in physical shards. For example, imagine your application were to have two physical shards defined like so:

```python
DATABASES = database_configs(databases_dict={
    'unsharded_databases': [
        {
            'name': 'default',
            'environment_variable': 'DATABASE_URL',
            'default_database_url': 'postgres://user:pwd@localhost/sharding'
        }
    ],
    'sharded_databases': [
        {
            'name': 'app_shard_001',
            'environment_variable': 'SHARD_001_DATABASE_URL',
            'default_database_url': 'postgres://user:pwd@some_host_01/shard_01'
        },
        {
            'name': 'app_shard_002',
            'environment_variable': 'SHARD_002_DATABASE_URL',
            'default_database_url': 'postgres://user:pwd@some_host_02/shard_02'
        },
    ]
})
```

Suppose they were nearing capacity then adding a third would result in a terrible data imbalance. The only way to rebalance them is to move related data to a new shard. That's a difficult task which we'll discuss in the advanced section of this guide.

On the other hand, if you had used two physical nodes with two logical shards each, which you'd define like so:

```python
DATABASES = database_configs(databases_dict={
    'unsharded_databases': [
        {
            'name': 'default',
            'environment_variable': 'DATABASE_URL',
            'default_database_url': 'postgres://user:pwd@localhost/sharding'
        }
    ],
    'sharded_databases': [
        {
            'name': 'app_shard_001',
            'environment_variable': 'SHARD_001_DATABASE_URL',
            'default_database_url': 'postgres://user:pwd@some_host_01/shard_01'
        },
        {
            'name': 'app_shard_002',
            'environment_variable': 'SHARD_002_DATABASE_URL',
            'default_database_url': 'postgres://user:pwd@some_host_01/shard_02'
        },
        {
            'name': 'app_shard_003',
            'environment_variable': 'SHARD_003_DATABASE_URL',
            'default_database_url': 'postgres://user:pwd@some_host_02/shard_03'
        },
        {
            'name': 'app_shard_004',
            'environment_variable': 'SHARD_004_DATABASE_URL',
            'default_database_url': 'postgres://user:pwd@some_host_02/shard_04'
        },
    ]
})
```

Then, as a way to rebalance the data, you could move either `app_shard_003` or `app_shard_002` to `some_host_03`, your new machine. And all you'd have to do is copy over the database and change `'postgres://user:pwd@some_host_02/shard_03'` to `'postgres://user:pwd@some_host_03/shard_03'`. This wouldn't leave you incredibly balanced with only two logical shards per node, so the author suggests at least ten logical shards per node. That way you can easily rebalance data as your data-set grows.

### Many Shards or Few Shards?

The author recommends that you create more shards than you think are necessary. Extra logical shards allow you to much more easily rebalance data across physical nodes in the future. Also, by Storing data on different machines, you increase the number of connections to your databases.
