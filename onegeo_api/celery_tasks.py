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
from uuid import uuid4


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

    related_tasks = Task.asynchronous.filter(
        alias=alias, task_name=sender, user=user,
        stop_date__isnull=True, success__isnull=True)

    if len(related_tasks) > 0:
        revoke([task.uuid for task in related_tasks], terminate=True)
    # then
    Task.asynchronous.create(
        uuid=UUID(uuid), alias=alias,
        task_name=sender, user=user, resource_ns=resource_ns)


# @task_prerun.connect
# def on_task_prerun(**kwargs):
#     pass


@task_revoked.connect
def on_task_revoked(sender=None, request=None, **kwargs):
    Task.logged.filter(uuid=UUID(request.id)).update(
        success=False, details={'reason': 'revoked'})


@task_unknown.connect
def on_task_unknown(sender=None, request=None, **kwargs):
    Task.logged.filter(uuid=UUID(request.id)).update(
        success=False, details={'reason': 'revoked'})


@task_rejected.connect
def on_task_rejected(sender=None, request=None, **kwargs):
    Task.logged.filter(uuid=UUID(request.id)).update(
        success=False, details={'reason': 'revoked'})


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
    Task.logged.filter(uuid=UUID(task_id)).update(stop_date=timezone.now())


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
def indexing(alias=None, index_profile=None,
             user=None, resource_ns=None, force_update=False):

    user = User.objects.get(pk=user)
    index_profile = IndexProfile.objects.get(pk=index_profile)

    columns_mapping = {}
    analyzers = []
    for col in iter(index_profile.columns):
        name = col.pop('name')
        alias = col['alias']
        rejected = col['rejected']
        if not rejected:
            columns_mapping[name] = alias or name

        analyzer = col['analyzer']
        analyzer = col['search_analyzer']
        searchable = col['searchable']
        weight = col['weight']
        occurs = col['occurs']
        pattern = col['pattern']
        column_type = col['type']

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

        if analyzer and analyzer not in analyzers:
            analyzers.append(analyzer)
        index_profile.onegeo.update_property(name, 'search_analyzer', analyzer)

    index = str(uuid4())
    mappings = index_profile.onegeo.generate_elastic_mapping()

    body = {
        'mappings': {
            index: mappings.get('foo')},
        'settings': {
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
        res['created'] = {'count': len(created), 'ids': created}
    if reindexed:
        res['reindexed'] = {'count': len(reindexed), 'ids': reindexed}
    if failed:
        res['failed'] = {'count': len(failed), 'details': failed}
    return res
