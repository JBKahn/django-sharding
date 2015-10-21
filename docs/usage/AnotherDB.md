# Storing A Model On Another Database

In vanilla Django it's not straight forward to store data on another database. Sometimes when you're not sharding a table, you may want to store it on another database. For example, for performance you may want to store your User table on a secondary database. Doing this with the package is very easy, all you need to do is decorate your model like this:


```python
from django.db import models

from django_sharding_library.decorators import model_config

@model_config(database='secondary_database')
class SomeCoolGuyModel(models.Model):
    cool_guy_string = models.CharField(max_length=120)
```

The `model_config` decorator takes the name of the database and will handle the proper routing for you when combined with the included router and migration command.
