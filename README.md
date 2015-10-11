# [Django Sharding](https://github.com/JBKahn/django-sharding)

Django Sharding is a library and part-framework for sharding Django applications.

It helps you to scale your applications by sharding your data across multiple databases in a consistent way.

(badges for pypi and travis etc)

### What is Sharding?

Sharding is a way of horizontally partitioning your data by storing different rows of the same table in multiple tables across multiple databases. This helps to increase the number of connections to a given resource as well as improves read performance of your application.

### Developer Experience

I wrote this library after working on this problem for [Wave](https://www.waveapps.com) and not being able to find a library that suited our needs. What we were looking for was something that was powerful, extensible and customizable. This library was created for just that purpose and includes at least one implimentation of each part of the pipeline with room to replace any individual components.

### Influences

The package was influenced by my experiences at Wave as well as the help and code of my co-workers.

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
# Most applications will not need aditional routers but if you need your own then
# remember that order does matter. Read up on them here (link).
DATABASE_ROUTERS=['django_sharding_library.router.ShardedRouter'],

```

Add your databases to you settings file in the following format based on, and using, dj-database (link).
This structure supports unsharded sets of databses as well as replicates. This setting uses a single shard group,
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
                    'default_database_url': 'postgres://user:pw@localhost/shard_replica_001'
                },
                {
                    'name': 'app_shard_001_replica_002',
                    'environment_variable': 'REPLICA_002_DATABASE_URL',
                    'default_database_url': 'postgres://user:pw@localhost/shard_replica_002'
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

### Create Your First Sharded Model

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