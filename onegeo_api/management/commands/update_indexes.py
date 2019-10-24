# Copyright (c) 2017-2019 Neogeo-Technologies.
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


from django.core.management.base import BaseCommand
from django.utils import timezone
from onegeo_api.celery_tasks import indexing
from onegeo_api.models import IndexProfile
from uuid import uuid4


class Command(BaseCommand):

    help = 'Update indexes'

    def handle(self, *args, **kwargs):
        for instance in IndexProfile.objects.all():
            if self.is_index_to_update(instance):
                self.update_index(instance)

    def is_index_to_update(self, instance):
        now = timezone.now()
        return {
            'never': False,
            'daily': True,
            'weekly': now.isoweekday() == 1,
            'monthly': now.day == 1,
            }.get(instance.reindex_frequency, False)

    def update_index(self, instance):
        task_id = uuid4()
        index = uuid4()  # Id of the index for ES
        indexing.apply_async(
            kwargs={'alias': instance.alias.pk,
                    'force_update': True,
                    'index': str(index),
                    'index_profile': instance.pk,
                    'resource_ns': 'index',
                    'user': instance.user.pk},
            task_id=str(task_id))
