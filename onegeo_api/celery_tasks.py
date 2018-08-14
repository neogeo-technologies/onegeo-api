# Copyright (c) 2017-2018 Neogeo-Technologies.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from celery.decorators import task
# from celery.signals import after_task_publish
from celery.signals import before_task_publish
from celery.signals import task_failure
from celery.signals import task_postrun
# from celery.signals import task_prerun
from celery.signals import task_rejected
from celery.signals import task_revoked
from celery.signals import task_success
from celery.signals import task_unknown
from celery.task.control import revoke
from celery.utils.log import get_task_logger
from django.apps import apps
from django.contrib.auth.models import User
from django.utils import timezone
from onegeo_api.elastic import elastic_conn
from onegeo_api.models.analysis import get_complete_analysis
from uuid import UUID


logger = get_task_logger(__name__)


Alias = apps.get_model(app_label='onegeo_api', model_name='Alias')
Resource = apps.get_model(app_label='onegeo_api', model_name='Resource')
Source = apps.get_model(app_label='onegeo_api', model_name='Source')
Task = apps.get_model(app_label='onegeo_api', model_name='Task')
IndexProfile = apps.get_model(app_label='onegeo_api', model_name='IndexProfile')


@before_task_publish.connect
def on_beforehand(headers=None, body=None, sender=None, **kwargs):
    """Create a model-task entry and kill all celery-tasks from same sender."""
    uuid = headers['id']
    alias = Alias.objects.get(pk=body[1]['alias'])
    user = User.objects.get(pk=body[1]['user'])
    resource_ns = body[1]['resource_ns']

    details = None

    if sender == 'indexing':
        details = {'index': body[1]['index']}
    else:
        details = None

    related_tasks = Task.asynchronous.filter(
        alias=alias, task_name=sender, user=user,
        stop_date__isnull=True, success__isnull=True)

    if len(related_tasks) > 0:
        for related_task in related_tasks:
            revoke(related_task.uuid, terminate=True)
    # then
    Task.asynchronous.create(
        uuid=UUID(uuid), alias=alias, details=details,
        task_name=sender, user=user, resource_ns=resource_ns)


# @task_prerun.connect
# def on_task_prerun(**kwargs):
#     pass


@task_revoked.connect
def on_task_revoked(task_id=None, sender=None, request=None, **kwargs):
    task = Task.logged.get(uuid=UUID(request.id))
    if sender.__qualname__ == 'indexing':
        index = task.details.get('index')
        if index:
            elastic_conn.delete_index(index)

    task.success = False
    task.details = {'reason': 'revoked'}
    task.stop_date = timezone.now()
    task.save()


@task_rejected.connect
def on_task_rejected(task_id=None, sender=None, request=None, **kwargs):
    task = Task.logged.get(uuid=UUID(request.id))
    if sender.__qualname__ == 'indexing':
        elastic_conn.delete_index(task.details.get('index'))

    task.success = False
    task.details = {'reason': 'rejected'}
    task.stop_date = timezone.now()
    task.save()


@task_unknown.connect
def on_task_unknown(task_id=None, sender=None, request=None, **kwargs):
    task = Task.logged.get(uuid=UUID(request.id))
    if sender.__qualname__ == 'indexing':
        elastic_conn.delete_index(task.details.get('index'))

    task.success = False
    task.details = {'reason': 'unknown'}
    task.stop_date = timezone.now()
    task.save()


@task_failure.connect
def on_task_failure(task_id=None, sender=None, exception=None, **kwargs):

    if exception.__class__.__qualname__ == 'ElasticError':
        details = exception.description
    else:
        details = exception.__str__()

    Task.logged.filter(uuid=UUID(task_id)).update(
        success=False, details={'reason': 'error', 'details': details})


@task_success.connect
def on_task_success(sender=None, **kwargs):
    Task.logged.filter(uuid=UUID(sender.request.id)).update(
        success=True, details=kwargs.get('result'))


@task_postrun.connect
def on_task_postrun(task_id=None, **kwargs):
    if task_id:
        task = Task.logged.get(uuid=UUID(task_id))
        task.stop_date = timezone.now()
        task.save()


# @after_task_publish.connect
# def afterwards(**kwargs):
#     pass


@task(name='data_source_analyzing', ignore_result=False)
def data_source_analyzing(alias=None, source=None, user=None, resource_ns=None):
    source = Source.objects.get(pk=source)

    for item in source.onegeo.get_resources():
        title = getattr(item, 'title', 'FeatureType (Nameless)')
        Resource.objects.create(**{
            'columns': item.columns, 'source': source,
            'title': title, 'typename': item.name, 'user': source.user})


@task(name='indexing', ignore_result=False)
def indexing(alias=None, index_profile=None, index=None,
             user=None, resource_ns=None, force_update=False):

    user = User.objects.get(pk=user)
    index_profile = IndexProfile.objects.get(pk=index_profile)

    columns_mapping = {}
    analyzers = []
    for col in iter(index_profile.columns):

        name = col.pop('name')
        alias = col.get('alias')
        rejected = col.get('rejected')
        if not rejected:
            columns_mapping[name] = alias or name

        analyzer = col.get('analyzer')
        search_analyzer = col.get('search_analyzer')
        searchable = col.get('searchable')
        weight = col.get('weight')
        occurs = col.get('occurs')
        pattern = col.get('pattern')
        column_type = col.get('type')

        index_profile.onegeo.update_property(name, 'alias', alias)
        index_profile.onegeo.update_property(name, 'type', column_type)
        index_profile.onegeo.update_property(name, 'pattern', pattern)
        index_profile.onegeo.update_property(name, 'occurs', occurs)
        index_profile.onegeo.update_property(name, 'rejected', rejected)
        index_profile.onegeo.update_property(name, 'searchable', searchable)
        index_profile.onegeo.update_property(name, 'weight', weight)

        if analyzer and analyzer not in analyzers:
            analyzers.append(analyzer)
        index_profile.onegeo.update_property(name, 'analyzer', analyzer)

        if search_analyzer and search_analyzer not in analyzers:
            analyzers.append(search_analyzer)
        index_profile.onegeo.update_property(name, 'search_analyzer', search_analyzer)

    mappings = index_profile.onegeo.generate_elastic_mapping()

    body = {
        'mappings': {
            index: mappings.get('foo')},
        'settings': {
            'codec': 'best_compression',
            'number_of_replicas': 0,
            'analysis': get_complete_analysis(analyzer=analyzers, user=user)}}

    if index_profile.onegeo.resource.source.protocol == 'pdf':
        pipeline = elastic_conn.create_pipeline()
    else:
        pipeline = False

    created, reindexed, failed = elastic_conn.create_or_reindex(
        index=index, body=body, alias=index_profile.uuid,
        collection=index_profile.onegeo.get_collection(),
        columns_mapping=columns_mapping, update=force_update,
        pipeline=pipeline)

    res = {}
    if created:
        res['created'] = len(created)  # {'count': len(created), 'ids': created}
    if reindexed:
        res['reindexed'] = len(reindexed)  # {'count': len(reindexed), 'ids': reindexed}
    if failed:
        res['failed'] = {'count': len(failed), 'details': failed}
    return res
