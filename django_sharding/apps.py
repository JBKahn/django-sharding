from django.apps import AppConfig, apps
from django.conf import settings
from django.db import models
from django.dispatch import receiver

from django_sharding_library.routing_read_strategies import PrimaryOnlyRoutingStrategy
from django_sharding_library.sharding_functions import RoundRobinBucketingStrategy
from django_sharding_library.signals import save_shard_handler


class ShardingConfig(AppConfig):
    name = 'django_sharding'

    def ready(self):
        shard_settings = getattr(settings, 'DJANGO_SHARDING_SETTINGS', {})
        shard_groups = [settings.DATABASES[db_settings]['SHARD_GROUP'] for db_settings in settings.DATABASES]
        shard_groups = set(filter(lambda group: group is not None, shard_groups))
        self.bucketers = {}
        self.routing_strategies = {}
        for shard_group in shard_groups:
            group_settings = shard_settings.get(shard_group, {})
            self.bucketers[shard_group] = group_settings.get(
                'BUCKETING_STRATEGY',
                RoundRobinBucketingStrategy(shard_group=shard_group, databases=settings.DATABASES)
            )
            self.routing_strategies[shard_group] = group_settings.get(
                'ROUTING_STRATEGY',
                PrimaryOnlyRoutingStrategy(databases=settings.DATABASES)
            )

        # Unless otherwise instructed, add the signal to save the shard to the model if it has a shard field.
        for model in apps.get_models():
            if getattr(model, 'django_sharding__stores_shard', False) and getattr(model, 'django_sharding__shard_group', None):
                shard_group = getattr(model, 'django_sharding__shard_group', None)
                shard_field = getattr(model, 'django_sharding__shard_field', None)
                if not shard_field:
                    raise Exception('The model {} must have a `shard_field` attribute'.format(model))
            else:
                shard_fields = list(filter(lambda field: getattr(field, 'django_sharding__stores_shard', False), model._meta.fields))
                if not any(shard_fields):
                    continue

                if len(shard_fields) > 1:
                    raise Exception('The model {} has multuple fields for shard storage: {}'.format(model, shard_fields))
                shard_field = shard_fields[0]
                shard_group = getattr(shard_field, 'django_sharding__shard_group', None)

                if not shard_group:
                    raise Exception('The model {} with the shard field must have a `shard_group` attribute'.format(model))

                if not getattr(shard_field, 'django_sharding__use_signal', False):
                    continue

            group_settings = shard_settings.get(shard_group, {})
            if group_settings.get('SKIP_ADD_SHARDED_SIGNAL', False):
                continue

            receiver(models.signals.pre_save, sender=model)(save_shard_handler)

    def get_routing_strategy(self, shard_group):
        return self.routing_strategies[shard_group]

    def get_bucketer(self, shard_group):
        return self.bucketers[shard_group]
