# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-11-07 08:59
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Analyzer',
            fields=[
                ('name', models.CharField(max_length=250, primary_key=True, serialize=False, unique=True, verbose_name='Name')),
                ('config', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Config')),
                ('reserved', models.BooleanField(default=False, verbose_name='Reserved')),
            ],
        ),
        migrations.CreateModel(
            name='Context',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, unique=True, verbose_name='Name')),
                ('clmn_properties', django.contrib.postgres.fields.jsonb.JSONField(verbose_name='Columns')),
                ('reindex_frequency', models.CharField(choices=[('daily', 'daily'), ('weekly', 'weekly'), ('monthly', 'monthly')], default='monthly', max_length=250, verbose_name='Reindex_frequency')),
            ],
        ),
        migrations.CreateModel(
            name='Filter',
            fields=[
                ('name', models.CharField(max_length=250, primary_key=True, serialize=False, unique=True, verbose_name='Name')),
                ('config', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Config')),
                ('reserved', models.BooleanField(default=False, verbose_name='Reserved')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('columns', django.contrib.postgres.fields.jsonb.JSONField(verbose_name='Columns')),
            ],
            options={
                'verbose_name': 'Resource',
            },
        ),
        migrations.CreateModel(
            name='SearchModel',
            fields=[
                ('name', models.CharField(max_length=250, primary_key=True, serialize=False, unique=True, verbose_name='Name')),
                ('config', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Config')),
                ('context', models.ManyToManyField(to='onegeo_api.Context')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uri', models.CharField(max_length=2048, unique=True, verbose_name='URI')),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('mode', models.CharField(choices=[('geonet', 'API de recherche GeoNetWork'), ('pdf', 'Répertoire contenant des fichiers PDF'), ('wfs', 'Service OGC:WFS')], default='pdf', max_length=250, verbose_name='Mode')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
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
                ('model_type', models.CharField(choices=[('source', 'source'), ('context', 'context')], max_length=250, verbose_name='Model relation type')),
                ('model_type_id', models.CharField(max_length=250, verbose_name='Id model relation linked')),
                ('description', models.CharField(max_length=250, verbose_name='Description')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Tokenizer',
            fields=[
                ('name', models.CharField(max_length=250, primary_key=True, serialize=False, unique=True, verbose_name='Name')),
                ('config', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Config')),
                ('reserved', models.BooleanField(default=False, verbose_name='Reserved')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='resource',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Source'),
        ),
        migrations.AddField(
            model_name='context',
            name='resources',
            field=models.ManyToManyField(to='onegeo_api.Resource'),
        ),
        migrations.AddField(
            model_name='analyzer',
            name='filter',
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
        migrations.AlterUniqueTogether(
            name='source',
            unique_together=set([('uri', 'user')]),
        ),
    ]
