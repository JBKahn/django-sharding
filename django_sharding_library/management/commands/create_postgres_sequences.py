from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from django_sharding_library.utils import create_postgres_global_sequence, create_postgres_shard_id_function, verify_postres_id_field_setup_correctly


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            action='store',
            dest='database',
            default=None,
            help='Nominates a database to create the sequence on. Defaults to "all" databases.',
            choices=['all'] + self.get_all_but_replica_dbs(),
        )
        parser.add_argument(
            '-v', '--verbosity', action='store', dest='verbosity', default=1,
            type=int, choices=[0, 1, 2, 3],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output',
        )
        parser.add_argument(
            '--reset-sequence-if-exists', action='store_true', dest='reset_sequence', default=False,
            help="Reset the sequence if it exists.",
        )

    def get_all_but_replica_dbs(self):
        return list(filter(
            lambda db: not settings.DATABASES[db].get('PRIMARY', None),
            settings.DATABASES.keys()
        ))

    def handle(self, *args, **options):
        if not options['database'] or options['database'] == 'all':
            databases = self.get_all_but_replica_dbs()
        elif options['database'] not in self.get_all_but_replica_dbs():
            raise CommandError('You must migrate an existing non-primary DB.')
        else:
            databases = [options['database']]

        for database in databases:
            if options['verbosity'] >= 1:
                try:
                    shard_id = settings.DATABASES[database].get('SHARD_ID', 0)
                    create_postgres_global_sequence(sequence_name="global_id_sequence", db_alias=database, reset_sequence=options["reset_sequence"])
                    create_postgres_shard_id_function(sequence_name="global_id_sequence", db_alias=database, shard_id=shard_id)
                    if not verify_postres_id_field_setup_correctly(sequence_name="global_id_sequence", db_alias=database, function_name="next_sharded_id"):
                        raise Exception("That didn't work.")
                    self.stdout.write(getattr(self.style, "SUCCESS")("\nDatabase: {}\n").format(database))
                except:
                    self.stdout.write(getattr(self.style, "ERROR")("\nDatabase: {}\n").format(database))
