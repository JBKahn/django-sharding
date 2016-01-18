Changelog
=========

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
