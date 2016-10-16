class DjangoShardingException(Exception):
    pass


class ShardedModelInitializationException(DjangoShardingException):
    pass


class InvalidMigrationException(DjangoShardingException):
    pass


class InvalidShowMigrationsException(DjangoShardingException):
    pass


class NonExistentDatabaseException(DjangoShardingException):
    pass
