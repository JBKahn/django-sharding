# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_sharding_library.id_generation_strategies
import django.contrib.auth.models
import django_sharding_library.fields
import tests.models
import django.utils.timezone
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(null=True, verbose_name='last login', blank=True)),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, max_length=30, validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')], help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, verbose_name='username')),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='email address', blank=True)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('shard', models.CharField(blank=True, max_length=120, null=True, choices=[(b'app_shard_001', b'app_shard_001'), (b'app_shard_002', b'app_shard_002')])),
                ('groups', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='ShardedByForiegnKeyModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('random_string', models.CharField(max_length=120)),
            ],
        ),
        migrations.CreateModel(
            name='ShardedModelIDs',
            fields=[
                ('id', django_sharding_library.fields.BigAutoField(serialize=False, primary_key=True)),
                ('stub', models.NullBooleanField(default=True, unique=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ShardedTestModelIDs',
            fields=[
                ('id', django_sharding_library.fields.BigAutoField(serialize=False, primary_key=True)),
                ('stub', models.NullBooleanField(default=True, unique=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ShardStorageTable',
            fields=[
                ('shard', models.CharField(max_length=120, choices=[(b'app_shard_001', b'app_shard_001'), (b'app_shard_002', b'app_shard_002')])),
                ('shard_key', models.CharField(max_length=120, serialize=False, primary_key=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TestModel',
            fields=[
                ('id', django_sharding_library.fields.TableShardedIDField(source_table=tests.models.ShardedTestModelIDs, serialize=False, primary_key=True, strategy=django_sharding_library.id_generation_strategies.TableStrategy(backing_model=tests.models.ShardedTestModelIDs))),
                ('random_string', models.CharField(max_length=120)),
                ('user_pk', models.PositiveIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='UnshardedTestModel',
            fields=[
                ('id', django_sharding_library.fields.TableShardedIDField(source_table=tests.models.ShardedTestModelIDs, serialize=False, primary_key=True, strategy=django_sharding_library.id_generation_strategies.TableStrategy(backing_model=tests.models.ShardedTestModelIDs))),
                ('random_string', models.CharField(max_length=120)),
                ('user_pk', models.PositiveIntegerField()),
            ],
        ),
        migrations.AddField(
            model_name='shardedbyforiegnkeymodel',
            name='shard',
            field=django_sharding_library.fields.ShardForeignKeyStorageField(to='tests.ShardStorageTable', shard_group=b'default'),
        ),
        migrations.AddField(
            model_name='shardedbyforiegnkeymodel',
            name='test',
            field=models.ForeignKey(to='tests.UnshardedTestModel'),
        ),
    ]
