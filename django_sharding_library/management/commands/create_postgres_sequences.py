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
            '--sequence-name',
            action='store',
            dest='sequence_name',
            default='global_id_sequence',
            help='The name of the sequence to create and verify exists.',
        )
        parser.add_argument(
            '--reset-sequence', action='store_true', dest='reset_sequence', default=False,
            help="Reset the sequence if it exists.",
        )
        parser.add_argument(
            '--dry-run', action='store_true', dest='dry_run', default=False,
            help="Check they exist but make no changes to the database.",
        )

    def get_all_but_replica_dbs(self):
        return sorted(list(filter(
            lambda db: not settings.DATABASES[db].get('PRIMARY', None),
            settings.DATABASES.keys()
        )))

    def handle(self, *args, **options):
        if not options['database'] or options['database'] == 'all':
            databases = self.get_all_but_replica_dbs()
        elif options['database'] not in self.get_all_but_replica_dbs():
            raise CommandError('You must migrate an existing primary DB.')
        else:
            databases = [options['database']]

        has_errors = False

        for database in databases:
            sequence_name = options["sequence_name"]
            try:
                shard_id = settings.DATABASES[database].get('SHARD_ID', None)
                if shard_id is None:
                    continue
                if not options["dry_run"]:
                    create_postgres_global_sequence(sequence_name=sequence_name, db_alias=database, reset_sequence=options["reset_sequence"])
                    create_postgres_shard_id_function(sequence_name=sequence_name, db_alias=database, shard_id=shard_id)
                if not verify_postres_id_field_setup_correctly(sequence_name=sequence_name, db_alias=database, function_name="next_sharded_id"):
                    raise Exception("The sequence could not be found.")
                self.stdout.write(getattr(self.style, "SUCCESS", lambda a: a)("\nDatabase {} with shard id {}:sequence {} is present").format(database, shard_id, sequence_name))
            except Exception as e:
                self.stdout.write(getattr(self.style, "ERROR", lambda a: a)("\nDatabase {}: Error occured: {}").format(database, str(e)))
                has_errors = True

        if has_errors:
            raise CommandError("Some databases do not have the sequence on them.")
