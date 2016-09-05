from django.conf import settings
from django.core.management.commands.migrate import Command as MigrationCommand

from django_sharding_library.exceptions import InvalidMigrationException


class Command(MigrationCommand):
    def handle(self, *args, **options):
        if not options['database'] or options['database'] == 'all':
            databases = self.get_all_but_replica_dbs()
        elif options['database'] not in self.get_all_but_replica_dbs():
            raise InvalidMigrationException('You must migrate an existing non-primary DB.')
        else:
            databases = [options['database']]

        for database in databases:
            options['database'] = database
            # Writen in green text to stand out from the surrouding headings
            if options['verbosity'] >= 1:
                self.stdout.write(getattr(self.style, "MIGRATE_SUCCESS", getattr(self.style, "SUCCESS", lambda a: a))("\nDatabase: {}\n").format(database))
            super(Command, self).handle(*args, **options)

    def get_all_but_replica_dbs(self):
        return list(filter(
            lambda db: not settings.DATABASES[db].get('PRIMARY', None),
            settings.DATABASES.keys()
        ))

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser._option_string_actions['--database'].default = None
        parser._option_string_actions['--database'].help = u'Nominates a database to synchronize. Defaults to all databases.'
        parser._option_string_actions['--database'].choices = ['all'] + self.get_all_but_replica_dbs()
