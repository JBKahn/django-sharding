Changelog
=========

3.0.0 (April 26th 2018)
------------------

### Official Support for Django 2.0.0 in setup.py

- Support for Django > 2.0.0 and < 3.0.0 in setup.py


2.1.0 (Jan 5th 2018)
------------------

### Official Support for Django 2.0.0

- Support for Django 2.0.0.


2.0.0 (Sep 10th 2017)
------------------

### Small updates

- Unpin `dj-database-url` from a specific minor version to a specific major version.
- Initial support for deleting django models. I'm not going to update the docs just yet
as I don't entirely like this solution...something is better than nothing.
Check the `test_deleted_model_in_settings` tests to see this. The issue is that django
needs to know about a model after you've deleted the class so sharded settings on deleted
models need to be tracked somewhere.


1.2.0 (May 1st 2017)
------------------

### Official Support for Django 1.11

- Support for Django 1.11.


1.1.0 (Mar 19th 2017)
------------------

### A bug fix and settings improvement

- Bugfix so that the `fields.py` file is importable when psycog2 isn't installed.
- Add the ability to set the database name in the settings helper, and override
the one in the url. Makes generating these settings programatically a bit easier.


1.0.0 (Oct 16th 2016)
------------------

### Django 1.10 compatibility and some additional library features!

- Added decorator for shard storage.
- Renamed `PostgresShardGeneratedIDField` to `PostgresShardGeneratedIDAutoField`.
- Added non-autoid `PostgresShardGeneratedIDField` that makes a separate call to
the database prior to saving. Good for statement based replication. Now you can
have more than one of these fields on a model.
- Fix `TableShardedIDField` to take a table name rather than model class so that
it doesn't give errors when reading the migrations file after deleting the table.
- Fix `showmigrations` to use the same database param as `migrate` and act on
all by default.


0.1.0 (Oct 7th 2016)
------------------

### Django 1.10 compatibility and some additional library features!

- Django 1.10 compatibility.
- Added postgres specific ID generator
- Some magic sharded field lookups (if you're so inclined)
- The above fields have the additional functionality to automatically lookup the shard when part of the save/update/filter clauses contain the information required to get the shard
- Alters the way data migrations run as far as which databases are acted upon as well as provides an override, see the docs for more details. This brings the package more inline with Django.


0.0.8 (Apr 20th 2016)
------------------

### A few fixes for compatibility with python3 and using tox for testing

- Tested on pthon 2.7, 3.4 and 3.5


0.0.7 (Jan 18th 2016)
------------------

### Small fix for django migrations

- The shards field is using sorted choices so that the migration is the same regardless of the machine.

0.0.6 (Dec 15th 2015)
------------------

### Small fix of legacy settings name

- `DJANGO_FRAGMENTS_SHARD_SETTINGS` to `DJANGO_SHARDING_SETTINGS`.

0.0.5 (Dec 14th 2015)
------------------

### Small Fix for people wrapping the package

- Allow you to rename the app the config is loaded in through a hiddden setting

0.0.4 (Dec 14th 2015)
------------------

### Small Fix for Django 1.9

- Updated the router to accept the `model` hint in addition to already accepting the `model_name` hint.

0.0.3 (Nov 23rd 2015)
------------------

### Small Fix

- Stop selecting incorrect shard group.

0.0.2 (Oct 11th, 2015)
------------------

### More Tests and Docs

- Added additional tests and updated docs


0.0.1 (Oct 11th, 2015)
------------------

### New Package

- Added initial functionality to support sharded models, read replicas, tables on non-default databases, docs etc...
