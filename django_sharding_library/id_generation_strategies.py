import uuid

from django.apps import apps
from django.db import connections, transaction
from django.utils.deconstruct import deconstructible

from django_sharding_library.constants import Backends
from django_sharding_library.models import TableStrategyModel


class BaseIDGenerationStrategy(object):
    """
    A strategy for Generating unique identifiers for the sharded models.
    """
    def get_next_id(self, database=None):
        """
        A function which takes no arguments and returns a new unique identifier.
        """
        raise NotImplemented


@deconstructible
class TableStrategy(BaseIDGenerationStrategy):
    """
    Uses an autoincrement field, on a TableStrategyModel model `backing_model`
    to generate unique IDs.
    """
    def __init__(self, backing_model_name):
        self.backing_model_name = backing_model_name

    def get_next_id(self, database=None):
        """
        Returns a new unique integer identifier for an object using an
        auto-incrimenting field in the database.
        """
        app_label = self.backing_model_name.split('.')[0]
        app = apps.get_app_config(app_label)
        backing_model = app.get_model(self.backing_model_name[len(app_label) + 1:])

        if not issubclass(backing_model, TableStrategyModel):
            raise ValueError("Unsupported model used for generating IDs")

        from django.conf import settings
        backing_table_db = getattr(backing_model, 'database', 'default')
        if settings.DATABASES[backing_table_db]['ENGINE'] in Backends.MYSQL:
            with transaction.atomic(backing_table_db):
                cursor = connections[backing_table_db].cursor()
                sql = "REPLACE INTO `{0}` (`stub`) VALUES ({1})".format(
                    backing_model._meta.db_table, True
                )
                cursor.execute(sql)

            if getattr(cursor.cursor.cursor, 'lastrowid', None):
                id = cursor.cursor.cursor.lastrowid
            else:
                id = backing_model.objects.get(stub=True).id
        else:
            with transaction.atomic(backing_table_db):
                id = backing_model.objects.create(stub=None).id
        return id


@deconstructible
class UUIDStrategy(BaseIDGenerationStrategy):
    """
    Uses a uuid and the shard name to generate unique IDs.
    """
    def get_next_id(self, database):
        """
        Generate a cross-shard UUID using a python UUID and the name of the database.
        """
        from django.conf import settings
        assert database in settings.DATABASES
        return '{}-{}'.format(database, uuid.uuid4())
