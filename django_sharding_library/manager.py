from django.db import transaction, router, IntegrityError
from django.db.models.manager import Manager
from django.db.models.query import QuerySet


class ShardQuerySet(QuerySet):
    """
    Stores the lookups to pass to the router as a hint
    """
    def __init__(self, model=None, *args, **kwargs):
        super(ShardQuerySet, self).__init__(model=model, *args, **kwargs)
        self._exact_lookups = {}

    def _clone(self, **kwargs):
        clone = super(ShardQuerySet, self)._clone(**kwargs)
        clone._exact_lookups = self._exact_lookups.copy()
        return clone

    def _filter_or_exclude(self, *args, **kwargs):
        """
        Update our lookups when we get a filter or an exclude (we only care about filter, but its a
        shared function in the ORM)
        :return:
        """
        clone = super(ShardQuerySet, self)._filter_or_exclude(*args, **kwargs)
        if getattr(clone, '_exact_lookups', None) is None:
            clone._exact_lookups = {}
        clone._exact_lookups.update(dict([(k, v) for k, v in kwargs.items() if '__' not in k]))
        return clone

    @property
    def db(self):
        if self._db:
            return self._db

        if self._for_write:
            return router.db_for_write(self.model, exact_lookups=self._exact_lookups,
                                       instance=getattr(self, '_instance', None))
        return router.db_for_read(self.model, exact_lookups=self._exact_lookups)

    def create(self, **kwargs):
        """
        Not sure if this is necessary anymore, it was in 1.4. Grabs the instance before its too late to pass it to the
        router as a hint.
        """
        obj = self.model(**kwargs)
        self._for_write = True
        self._instance = obj
        obj.save(force_insert=True, using=self.db)
        return obj


class ShardManager(Manager):

    def get_query_set(self, key=None):
        # Should check to make sure the there is a good kwarg here

        # assert key is not None, 'You must filter on %s before expanding a QuerySet on %s models.' % (
        #     shards.key, self.model.__name__)

        return ShardQuerySet(model=self.model)

    @staticmethod
    def _wrap(func_name):
        def wrapped(self, **kwargs):
            # Should check for good kwarg here as well, need to grab it off the model but not sure where/how to define
            # that. Will ask author later

            # self.get_query_set(key=int(key))
            return getattr(self.get_query_set(), func_name)(**kwargs)

        wrapped.__name__ = func_name
        return wrapped

    filter = _wrap('filter')
    get = _wrap('get')
    create = _wrap('create')
    get_or_create = _wrap('get_or_create')