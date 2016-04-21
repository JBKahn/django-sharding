from itertools import cycle
from random import choice, randint

from django.utils.six import next, viewitems


class BaseRoutingStrategy(object):
    """
    A base strategy for picking which database to read from when there are read
    replicas in the system. In order to extend this strategy, you must define a
    `pick_read_db` function which returns the name of the DB to read from,
    given a primary DB.
    If there are no read replicas defined, all strategies should always return the
    primary.
    """
    def __init__(self, databases):
        self.primary_replica_mapping = self.get_primary_replica_mapping(databases)

    def get_primary_replica_mapping(self, databases):
        """
        Creates a dictionary that maps a primary drive name to all the names of
        it's replication databases. This can be used in the strategies.
        """
        mapping = {}
        for name, config in databases.items():
            primary = config.get('PRIMARY', None)
            if not primary:
                continue
            if primary not in mapping:
                mapping[primary] = []
            if primary != name:
                mapping[primary].append(name)
        return mapping

    def pick_read_db(self, primary_db_name):
        """
        Given the name of a primary, pick the name of the database to read
        from which may be a replica or the primary itself.
        """
        raise NotImplemented


class PrimaryOnlyRoutingStrategy(BaseRoutingStrategy):
    """
    A strategy which will always read from the primary, unless overridden,
    regardless of replicas defined.
    """
    def pick_read_db(self, primary_db_name):
        return primary_db_name


class RoundRobinRoutingStrategy(BaseRoutingStrategy):
    """
    A strategy which will cycle through the read replicas and primary, in a
    round-robin fashion when choosing which database to read from.
    """
    def __init__(self, databases):
        super(RoundRobinRoutingStrategy, self).__init__(databases)
        self.read_cycles = {}

        for primary, replicas in viewitems(self.primary_replica_mapping):
            self.read_cycles[primary] = cycle(replicas + [primary])

    def pick_read_db(self, primary_db_name):
        return next(self.read_cycles[primary_db_name])


class RandomRoutingStrategy(BaseRoutingStrategy):
    """
    A strategy which will choose a random read replicas, or the primary,
    when choosing which database to read from.
    """
    def pick_read_db(self, primary_db_name):
        return choice(self.primary_replica_mapping[primary_db_name])


class RatioRoutingStrategy(BaseRoutingStrategy):
    def pick_read_db(self, primary_db_name):
        """
        Read from primary half the time and random replicas the other half.
        """
        if randint(0, 1):
            return primary_db_name
        return choice(self.primary_replica_mapping[primary_db_name])
