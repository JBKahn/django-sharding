import django
from django.core.management.base import CommandError
from django.core.management.commands.makemigrations import Command as MakeMigrationsCommand


class Command(MakeMigrationsCommand):
    def handle(self, *app_labels, **options):
        if django.VERSION < (1, 10, 1):
            return super(Command, self).handle(*app_labels, **options)

        elif django.VERSION < (1, 10, 2):
            import sys
            import warnings

            from django.apps import apps
            from django.conf import settings
            from django.db import DEFAULT_DB_ALIAS, connections, router
            from django.db.migrations import Migration
            from django.db.migrations.autodetector import MigrationAutodetector
            from django.db.migrations.loader import MigrationLoader
            from django.db.migrations.questioner import (
                InteractiveMigrationQuestioner,
                NonInteractiveMigrationQuestioner,
            )
            from django.db.migrations.state import ProjectState
            from django.utils.deprecation import RemovedInDjango20Warning
            from django.utils.six import iteritems

            self.verbosity = options['verbosity']
            self.interactive = options['interactive']
            self.dry_run = options['dry_run']
            self.merge = options['merge']
            self.empty = options['empty']
            self.migration_name = options['name']
            self.exit_code = options['exit_code']
            check_changes = options['check_changes']

            if self.exit_code:
                warnings.warn(
                    "The --exit option is deprecated in favor of the --check option.",
                    RemovedInDjango20Warning
                )

            # Make sure the app they asked for exists
            app_labels = set(app_labels)
            bad_app_labels = set()
            for app_label in app_labels:
                try:
                    apps.get_app_config(app_label)
                except LookupError:
                    bad_app_labels.add(app_label)
            if bad_app_labels:
                for app_label in bad_app_labels:
                    self.stderr.write("App '%s' could not be found. Is it in INSTALLED_APPS?" % app_label)
                sys.exit(2)

            # Load the current graph state. Pass in None for the connection so
            # the loader doesn't try to resolve replaced migrations from DB.
            loader = MigrationLoader(None, ignore_no_migrations=True)

            # Raise an error if any migrations are applied before their dependencies.
            consistency_check_labels = set(config.label for config in apps.get_app_configs())
            # Non-default databases are only checked if database routers used.
            aliases_to_check = connections if settings.DATABASE_ROUTERS else [DEFAULT_DB_ALIAS]
            for alias in sorted(aliases_to_check):
                connection = connections[alias]
                if (connection.settings_dict['ENGINE'] != 'django.db.backends.dummy' and
                        # At least one app must be migrated to the database.
                        any(router.allow_migrate(connection.alias, label, hints={"making_migrations": True}) for label in consistency_check_labels)):
                    loader.check_consistent_history(connection)

            # Before anything else, see if there's conflicting apps and drop out
            # hard if there are any and they don't want to merge
            conflicts = loader.detect_conflicts()

            # If app_labels is specified, filter out conflicting migrations for unspecified apps
            if app_labels:
                conflicts = {
                    app_label: conflict for app_label, conflict in iteritems(conflicts)
                    if app_label in app_labels
                }

            if conflicts and not self.merge:
                name_str = "; ".join(
                    "%s in %s" % (", ".join(names), app)
                    for app, names in conflicts.items()
                )
                raise CommandError(
                    "Conflicting migrations detected; multiple leaf nodes in the "
                    "migration graph: (%s).\nTo fix them run "
                    "'python manage.py makemigrations --merge'" % name_str
                )

            # If they want to merge and there's nothing to merge, then politely exit
            if self.merge and not conflicts:
                self.stdout.write("No conflicts detected to merge.")
                return

            # If they want to merge and there is something to merge, then
            # divert into the merge code
            if self.merge and conflicts:
                return self.handle_merge(loader, conflicts)

            if self.interactive:
                questioner = InteractiveMigrationQuestioner(specified_apps=app_labels, dry_run=self.dry_run)
            else:
                questioner = NonInteractiveMigrationQuestioner(specified_apps=app_labels, dry_run=self.dry_run)
            # Set up autodetector
            autodetector = MigrationAutodetector(
                loader.project_state(),
                ProjectState.from_apps(apps),
                questioner,
            )

            # If they want to make an empty migration, make one for each app
            if self.empty:
                if not app_labels:
                    raise CommandError("You must supply at least one app label when using --empty.")
                # Make a fake changes() result we can pass to arrange_for_graph
                changes = {
                    app: [Migration("custom", app)]
                    for app in app_labels
                }
                changes = autodetector.arrange_for_graph(
                    changes=changes,
                    graph=loader.graph,
                    migration_name=self.migration_name,
                )
                self.write_migration_files(changes)
                return

            # Detect changes
            changes = autodetector.changes(
                graph=loader.graph,
                trim_to_apps=app_labels or None,
                convert_apps=app_labels or None,
                migration_name=self.migration_name,
            )

            if not changes:
                # No changes? Tell them.
                if self.verbosity >= 1:
                    if len(app_labels) == 1:
                        self.stdout.write("No changes detected in app '%s'" % app_labels.pop())
                    elif len(app_labels) > 1:
                        self.stdout.write("No changes detected in apps '%s'" % ("', '".join(app_labels)))
                    else:
                        self.stdout.write("No changes detected")

                if self.exit_code:
                    sys.exit(1)
            else:
                self.write_migration_files(changes)
                if check_changes:
                    sys.exit(1)
        else:
            raise CommandError("Command not supported by this version of django_sharding")
