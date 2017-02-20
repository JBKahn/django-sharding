# Shard Rebalancing

#### Do I Want This

There are two types of shard rebalancing, logical shard rebalancing and physical shard rebalancing. They are based on physical and logical shards, as discussed in the [Choosing How To Shard](../installation/HowToShard.html) section of the documentation. If you've created lots of logical shards then this is a straight forward task and it does not currently require any code support.
# TODO: Lies. You need to mark a DB as read only. Will Do/add.

Physical shard rebalancing involves moving logical shards from machine to machine. This is really simple to do as you're copying a whole database from one physical node to another then adjusting the URL of the database in the settings file to point to the new machine. In the event that you have not logically sharded your data, then each node contains a single logical shard. As such you are forced to use logical shard rebalancing.

Logical shard rebalancing involves moving a subset of data from one database to another. This is done by freezing a subset of your data from being written to as you copy over all the relevant models. For example, if your application shards by User then you must freeze all writes for the User and copy all thier data over to the new database. After ensuring its integrity, you then switch the User's shard to read from and destroy the original copy of the data.

#### Why Logical Shard Rebalancing Is Difficult

As you can imagine, most applications are fairly complicated and you'd need to do two things in order to ensure a successful rebalancing. The first is that you need to stop the data to be moved from being modified. Therefore it requires that every sharded model, on the shard group being moved, be able to answer the question of whether it should be read-only. The second is that you need to be able to connect every sharded model such that you can not only identify the rows to be copied but in what order they need to be copied so that all foreign key constraints are kept.

Due to the above complexities as well as the issue of how to store and track the read-only data in an effective way across all instances of the app, I have not yet included a way to do this within the library.
