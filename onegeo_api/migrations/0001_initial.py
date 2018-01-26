# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-01-26 13:07
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Alias',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('handle', models.CharField(max_length=250, unique=True, verbose_name='Alias')),
                ('model_name', models.CharField(choices=[('Analyzer', 'Analyzer'), ('IndexProfile', 'IndexProfile'), ('Filter', 'Filter'), ('Resource', 'Resource'), ('SearchModel', 'SearchModel'), ('Source', 'Source'), ('Tokenizer', 'Tokenizer'), ('Undefined', 'Undefined')], default='Undefined', max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Analyzer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, unique=True, verbose_name='Name')),
                ('config', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Config')),
                ('reserved', models.BooleanField(default=False, verbose_name='Reserved')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Filter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, unique=True, verbose_name='Name')),
                ('config', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Config')),
                ('reserved', models.BooleanField(default=False, verbose_name='Reserved')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='IndexProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('clmn_properties', django.contrib.postgres.fields.jsonb.JSONField(verbose_name='Columns')),
                ('reindex_frequency', models.CharField(choices=[('daily', 'daily'), ('weekly', 'weekly'), ('monthly', 'monthly')], default='monthly', max_length=250, verbose_name='Reindex_frequency')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': "Profil d'indexation",
            },
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('columns', django.contrib.postgres.fields.jsonb.JSONField(verbose_name='Columns')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias')),
                ('index_profiles', models.ManyToManyField(to='onegeo_api.IndexProfile')),
            ],
            options={
                'verbose_name': 'Resource',
            },
        ),
        migrations.CreateModel(
            name='SearchModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('config', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Config')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias')),
                ('index_profiles', models.ManyToManyField(to='onegeo_api.IndexProfile')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('protocol', models.CharField(choices=[('geonet', 'API de recherche GeoNetWork'), ('pdf', 'Répertoire contenant des fichiers PDF'), ('wfs', 'Service OGC:WFS')], default='pdf', max_length=250, verbose_name='Protocole')),
                ('uri', models.CharField(max_length=2048, verbose_name='URI')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Source',
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateTimeField(auto_now_add=True, verbose_name='Start')),
                ('stop_date', models.DateTimeField(blank=True, null=True, verbose_name='Stop')),
                ('success', models.NullBooleanField(verbose_name='Success')),
                ('description', models.CharField(max_length=250, verbose_name='Description')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Tokenizer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, unique=True, verbose_name='Name')),
                ('config', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Config')),
                ('reserved', models.BooleanField(default=False, verbose_name='Reserved')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='resource',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Source'),
        ),
        migrations.AddField(
            model_name='resource',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='analyzer',
            name='filters',
            field=models.ManyToManyField(to='onegeo_api.Filter'),
        ),
        migrations.AddField(
            model_name='analyzer',
            name='tokenizer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Tokenizer'),
        ),
        migrations.AddField(
            model_name='analyzer',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
