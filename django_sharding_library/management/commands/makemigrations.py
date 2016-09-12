import os
from django.core.management.commands.makemigrations import Command as MakeMigrationCommand

from django_sharding_library.exceptions import InvalidMigrationException


class Command(MakeMigrationCommand):
    def handle(self, *args, **options):
        os.environ["DJANGO_SHARDING__MAKEMIGRATIONS"] = "True"
        return_val = super(Command, self).handle(*args, **options)
        del os.environ["DJANGO_SHARDING__MAKEMIGRATIONS"]
        return return_val
