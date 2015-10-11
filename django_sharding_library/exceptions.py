class DjangoShardingException(Exception):
    pass


class ShardedModelIntializationException(DjangoShardingException):
    pass


class InvalidMigrationException(DjangoShardingException):
    pass


class NonExistantDatabaseException(DjangoShardingException):
    pass
