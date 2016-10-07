Changelog
=========

0.1.0 (Oct 7th 2015)
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
