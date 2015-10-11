# [Django Sharding](https://github.com/JBKahn/django-sharding)

Django Sharding is a library and part-framework for sharding Django applications.

It helps you to scale your applications by sharding your data across multiple databases in a consistent way.

[![Circle CI](https://circleci.com/gh/JBKahn/django-sharding.svg?style=svg)](https://circleci.com/gh/JBKahn/django-sharding)
[![PyPI version](https://badge.fury.io/py/django-sharding.svg)](https://badge.fury.io/py/django-sharding)
[![PyPi downloads](https://img.shields.io/pypi/dm/django-sharding.svg)](https://crate.io/packages/django-sharding/)
[![Coverage Status](https://coveralls.io/repos/JBKahn/django-sharding/badge.svg?branch=master&service=github)](https://coveralls.io/github/JBKahn/django-sharding?branch=master)

### What is Sharding?

Sharding is a way of horizontally partitioning your data by storing different rows of the same table in multiple tables across multiple databases. This helps to increase the number of connections to a given resource as well as improves read performance of your application.

### Read The Documentation

For information about how to setup sharding in your application, [read the documentation](http://josephkahn.io/django-sharding/).

### Developer Experience

I wrote this library after working on this problem for [Wave](https://www.waveapps.com) and not being able to find a library that suited our needs. What we were looking for was something that was powerful, extensible and customizable. This library was created for just that purpose and includes at least one implimentation of each part of the pipeline with room to replace any individual components.

### Influences

The package was influenced by my experiences at Wave as well as the help and code of my co-workers.

### Installation

Check out the [installation section](http://josephkahn.io/django-sharding/docs/installation/Settings.html) of the docs for basic package setup.

### Basis Setup & Usage

#### Sharding by User

Select a model to shard by and open up the models.py file. Here we'll use the user model:

```python
from django.contrib.auth.models import AbstractUser

from django_sharding_library.models import ShardedByMixin


class User(AbstractUser, ShardedByMixin):
    pass
```

Add that custom User to your settings file using the string class path:

```python
AUTH_USER_MODEL = '<app_with_user_model>.User'
```

#### Create Your First Sharded Model

Define your new model, eg:

```python
from django.db import models

from django_sharding_library.decorators import model_config
from django_sharding_library.fields import TableShardedIDField
from django_sharding_library.models import TableStrategyModel


@model_config(database='default')
class ShardedCarIDs(TableStrategyModel):
    pass


@model_config(sharded=True)
class Car(models.Model):
    id = TableShardedIDField(primary_key=True, source_table=ShardeCarIDs)
    ignition_type = models.CharField(max_length=120)
    company = models.ForeignKey('companies.Company')

    def get_shard(self):
        return self.company.user.shard
```

### Running migrations

Run them as normal, for example:

```
./managy.py makemigrations <app_name>

# To let django run the migrations in all the right places.
./manage.py migrate <app>

# To specify the database to run it on
./manage.py migrate <app> --database=<database_alias>
```

### Acccessing sharded data

```python
# TODO: Update this with methods.
shard = User.shard
Car.objects.using(shard).get(id=123)
```
