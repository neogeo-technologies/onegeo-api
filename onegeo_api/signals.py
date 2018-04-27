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


from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver
from onegeo_api.celery_tasks import create_resources_with_log
from onegeo_api.elastic import elastic_conn
from onegeo_api.models import Analyzer
from onegeo_api.models import Filter
from onegeo_api.models import IndexProfile
from onegeo_api.models import Resource
from onegeo_api.models import SearchModel
from onegeo_api.models import Source
from onegeo_api.models.task import Task
from onegeo_api.models import Tokenizer


@receiver(post_save, sender=IndexProfile)
def update_elastic_alias(sender, instance, **kwargs):
    if kwargs.get('created') is False:
        prev_alias = instance._prev_nickname
        next_alias = instance.nickname
        if prev_alias != next_alias:
            body = {'actions': []}
            for index in elastic_conn.get_indices_by_alias(prev_alias):
                body['actions'].append({'remove': {
                    'index': index, 'alias': prev_alias}})
                body['actions'].append({'add': {
                    'index': index, 'alias': next_alias}})
                elastic_conn.update_aliases(body)


@receiver(post_save, sender=Source)
def create_related_resource(sender, instance, **kwargs):
    if kwargs.get('created') is True:
        task = Task.objects.create(
            user=instance.user, alias=instance.alias, description='1')
        create_resources_with_log.apply_async(
            kwargs={'pk': instance.pk}, task_id=str(task.celery_id))


@receiver(post_delete, sender=IndexProfile)
def delete_elastic_related_index(sender, instance, **kwargs):
    for index in elastic_conn.get_indices_by_alias(instance.alias.handle):
        elastic_conn.delete_index(index)


@receiver(post_delete, sender=IndexProfile)
def remove_index_from_search_model(sender, instance, **kwargs):
    # TODO
    pass


@receiver(post_delete, sender=Analyzer)
@receiver(post_delete, sender=Filter)
@receiver(post_delete, sender=SearchModel)
@receiver(post_delete, sender=Tokenizer)
@receiver(post_delete, sender=Source)
@receiver(post_delete, sender=Resource)
@receiver(post_delete, sender=IndexProfile)
def delete_related_alias(sender, instance, **kwargs):
    if instance.alias:
        instance.alias.delete()
