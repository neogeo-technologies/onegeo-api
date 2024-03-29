from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager
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
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='UUID')),
                ('alias_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='Alias name')),
                ('model_name', models.CharField(max_length=100, verbose_name='Model name')),
            ],
        ),
        migrations.CreateModel(
            name='IndexProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(blank=True, null=True, verbose_name='Tilte')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('columns', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Columns')),
                ('reindex_frequency', models.CharField(choices=[('never', 'never'), ('monthly', 'monthly'), ('weekly', 'weekly'), ('daily', 'daily')], default='never', max_length=250, verbose_name='Re-indexation frequency')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias', verbose_name='Alias')),
            ],
            options={
                'verbose_name_plural': 'Indexation Profiles',
                'verbose_name': 'Indexation Profile',
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='UUID')),
                ('resource_ns', models.CharField(max_length=100, verbose_name='Resource Namespace')),
                ('task_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='Task name')),
                ('is_async', models.BooleanField(default=False, verbose_name='Is asynchronous')),
                ('success', models.NullBooleanField(verbose_name='Success')),
                ('start_date', models.DateTimeField(auto_now_add=True, verbose_name='Start')),
                ('stop_date', models.DateTimeField(blank=True, null=True, verbose_name='Stop')),
                ('details', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Details')),
                ('alias', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias', verbose_name='Alias')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name_plural': 'Tasks',
                'verbose_name': 'Task',
            },
            managers=[
                ('logged', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(blank=True, null=True, verbose_name='Tilte')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('protocol', models.CharField(choices=[('pdf', 'PDF Store'), ('json', 'JSON'), ('csw', 'OGC:CSW'), ('wfs', 'OGC:WFS'), ('geojson', 'GeoJSON')], max_length=100, verbose_name='Protocol')),
                ('uri', models.CharField(max_length=2048, verbose_name='URI')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias', verbose_name='Alias')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Sources',
                'verbose_name': 'Source',
            },
        ),
        migrations.CreateModel(
            name='SearchModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(blank=True, null=True, verbose_name='Tilte')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('query_dsl', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Query DSL')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias', verbose_name='Alias')),
                ('indexes', models.ManyToManyField(to='onegeo_api.IndexProfile', verbose_name='Indexation profiles')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name_plural': 'Search Models',
                'verbose_name': 'Search Model',
            },
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(blank=True, null=True, verbose_name='Tilte')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('columns', django.contrib.postgres.fields.jsonb.JSONField(verbose_name='Columns')),
                ('typename', models.CharField(blank=True, max_length=100, null=True, verbose_name='Typename')),
                ('alias', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Alias', verbose_name='Alias')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Source', verbose_name='Source')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Resources',
                'verbose_name': 'Resource',
            },
        ),
        migrations.AddField(
            model_name='indexprofile',
            name='resource',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='onegeo_api.Resource', verbose_name='Resource'),
        ),
        migrations.AddField(
            model_name='indexprofile',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Analysis',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(verbose_name='Title')),
                ('document', django.contrib.postgres.fields.jsonb.JSONField(verbose_name='Document')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name_plural': 'Analysis documents',
                'verbose_name': 'Analysis document',
            },
        ),
    ]