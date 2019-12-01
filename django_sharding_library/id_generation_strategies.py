import uuid

from django.apps import apps
from django.db import connections, transaction
from django.utils.deconstruct import deconstructible


class BaseIDGenerationStrategy(object):
    """
    A strategy for Generating unique identifiers for the sharded models.
    """
    def get_next_id(self, database=None):
        """
        A function which takes no arguments and returns a new unique identifier.
        """
        raise NotImplementedError


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
