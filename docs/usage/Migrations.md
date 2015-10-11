# Creating & Running Model Migrations

In order to make running migrations easier, a new migration command is included with the package when you add `django_sharding` to your `INSTALLED_APPS` list in your settings file. The net effect is that calling `python manage.py migrate` or `python manage.py makemigrations` will work as they did before for all model migrations.

Here's how the old command was wrapped to handle sharding:

```python
from django.conf import settings
from django.core.management.commands.migrate import Command as MigrationCommand

from django_sharding_library.exceptions import InvalidMigrationException


class Command(MigrationCommand):
    def handle(self, *args, **options):
        """
        Wrap the original command and runs migrate on all the databases. When
        a migration is run on a DB it is not supposed to migrate, the router
        detects this and performs no actions on that database. Each database
        tracks its own history of migrations so that you can run them on a
        specific database at a time.
        """

        if not options['database'] or options['database'] == 'all':
            databases = self.get_all_but_replica_dbs()
        elif options['database'] not in self.get_all_but_replica_dbs():
            raise InvalidMigrationException(
                'You must migrate an existing non-primary DB.'
            )
        else:
            databases = [options['database']]

        for database in databases:
            options['database'] = database
            # Writen in green text to stand out from the surrouding headings
            if options['verbosity'] >= 1:
                self.stdout.write(self.style.MIGRATE_SUCCESS(
                    "\nDatabase: {}\n").format(database)
                )
            super(Command, self).handle(*args, **options)

    def get_all_but_replica_dbs(self):
        """
        Return a list of primary databases, used to prevent migrations from
        being run on replication databases.
        """
        return filter(
            lambda db: not settings.DATABASES[db].get('PRIMARY', None),
            settings.DATABASES.keys()
        )

    def add_arguments(self, parser):
        """
        Overrides the existing Database command to accept any primary database as
        well as the keywork `all` which is the new default value.
        """
        super(Command, self).add_arguments(parser)
        parser._option_string_actions['--database'].default = None
        parser._option_string_actions['--database'].help = (
            u'Nominates a database to synchronize. Defaults to all databases.'
        )
        parser._option_string_actions['--database'].choices = (
            ['all'] + self.get_all_but_replica_dbs()
        )
```

By using the included router, it's as simple as calling migrate on all the primary databases in the system and allowing the system to decide which databases to run the migration on. The above changes were made to make the interface more simple than having to specify all the relevant databases.
