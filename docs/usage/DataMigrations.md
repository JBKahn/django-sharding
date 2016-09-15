# Creating Data Migrations

In order to remain compatible with Django, the way to specify which databases to run the migration on, it will be selected based
on what hints (if any) are passed by `RunPython`.

### case 1: No hints

The following code will execute on each database that has at least one model in the app where the migration is stored.

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
            do_the_stuff, hints={}
        ),
    ]
```

### case 2: `model_name` as a hints

The following code will execute on each database that has the `User` model on it.

The format is to pass it in as a string of `<app_name>.<model_name>`, e.g. `auth.User`.

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


### case 3: `force_migrate_on_databases` as a hints

In order to allow for custom behaviour as there is no way to force `Django` to migrate on
a specific set of databases during `migrate`. It will noop on databases which it *things* do not
need the migration. This is a way around that.

The following code will execute on each database in the `force_migrate_on_databases` list.

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
            do_the_stuff, hints={'force_migrate_on_databases': ["database_001", "database_003"]}
        ),
    ]
```
