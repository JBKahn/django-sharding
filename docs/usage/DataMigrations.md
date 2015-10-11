# Creating Data Migrations

There are two additional requirements to all data migrations used with the package. Firstly, that you need to specify what model the migration commands will be acting on. The second is a result of the previous requirement, which is that you only run data migrations on a specific model and a specific database or a shard group. For example, you cannot create Data on both the `default` database and `deafult` `shard_group`. In that case, you'd need to seperate it into two migrations.

The way to pass this information is to pass a `model_name` in as a hint. The format is to pass it in as a string of `<app_name>.<model_name>`, for example `auth.User`. Here's an example Data Migration:

```python
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def do_the_stuff(apps, schema_editor):
    User = apps.get_model("auth", "User")
    # Do things.


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '__first__'),
    ]

    operations = [
        migrations.RunPython(
            do_the_stuff, hints={'model_name': settings.AUTH_USER_MODEL}
        ),
    ]
```

By using the included router, the router will look at the hint to decide which groups of databases should run the migration.

# TODO: It is probably possible to just make you seperate them into diffferent RunPython functions, but I've yet to test that.