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

        self._hints['exact_lookups'] = self._exact_lookups
        if not self._hints.get('instance') and getattr(self, '_instance', None):
            self._hints['instance'] = getattr(self, '_instance')

        return super(ShardQuerySet, self).db

    def create(self, **kwargs):
        """
        Grabs the instance before its too late to pass it to the router as a hint. Django (as of 1.9) does not keep
        instances around in all cases, such as a create() call.
        """
        self._instance = self.model(**kwargs.copy())
        return super(ShardQuerySet, self).create(**kwargs)

    def get_or_create(self, defaults=None, **kwargs):
        """
        Add the lookups to the _exact_lookups and call super.
        """
        defaults = defaults or {}
        lookup, params = self._extract_model_params(defaults, **kwargs)
        self._exact_lookups = lookup
        return super(ShardQuerySet, self).get_or_create(defaults=defaults, **kwargs)

    def update_or_create(self, defaults=None, **kwargs):
        """
        Add the lookups to the _exact_lookups and call super.
        """
        defaults = defaults or {}
        lookup, params = self._extract_model_params(defaults, **kwargs)
        self._exact_lookups = lookup
        return super(ShardQuerySet, self).update_or_create(defaults=defaults, **kwargs)


class ShardManager(Manager):

    def __init__(self, *args, **kwargs):
        return_value = super(ShardManager, self).__init__(*args, **kwargs)
        self.name = 'shard_manager'
        return return_value

    def get_queryset(self, key=None):
        # todo: (eventually, not necessary now) Should check to make sure the there is a good kwarg OR an instance ->
        # available here
        return ShardQuerySet(model=self.model)

    def _wrap(func_name):
        def wrapped(self, *args, **kwargs):
            return getattr(self.get_queryset(), func_name)(*args, **kwargs)

        wrapped.__name__ = func_name
        return wrapped

    filter = _wrap('filter')
    get = _wrap('get')
    create = _wrap('create')
    get_or_create = _wrap('get_or_create')
    update_or_create = _wrap('update_or_create')
