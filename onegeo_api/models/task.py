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


from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import Http404
from django.utils import timezone
import uuid


MODEL = 'onegeo_api'


class Task(models.Model):

    class Meta(object):
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    PATHNAME = '/tasks/{task}'

    DESCRIPTION_CHOICES = (
        ('0', 'Unkown'),
        ('1', 'Data source analyzing'),
        ('2', 'Indexing'))

    alias = models.ForeignKey(
        to='Alias', verbose_name='Nickname', on_delete=models.CASCADE)

    celery_id = models.UUIDField(
        verbose_name='UUID', default=uuid.uuid4, editable=False)

    description = models.CharField(
        verbose_name='Description',
        choices=DESCRIPTION_CHOICES, max_length=1, default='0')

    start_date = models.DateTimeField(
        verbose_name='Start', auto_now_add=True)

    stop_date = models.DateTimeField(
        verbose_name='Stop', null=True, blank=True)

    success = models.NullBooleanField(verbose_name='Success')

    user = models.ForeignKey(to=User, verbose_name='User')

    @property
    def location(self):
        return self.PATHNAME.format(task=self.pk)

    @location.setter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not change it.')

    @location.deleter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not delete it.')

    def detail_renderer(self):

        elapsed_time = self.stop_date \
            and (self.stop_date - self.start_date) \
            or (timezone.now() - self.start_date)

        Model = apps.get_model(MODEL, self.alias.model_name)
        target = Model.objects.get(alias=self.alias)

        return {
            'action': self.get_description_display(),
            'dates': {
                'start': self.start_date,
                'end': self.stop_date},
            'elapsed_time': float('{0:.2f}'.format(elapsed_time.total_seconds())),
            'id': self.pk,
            'location': self.location,
            'status': {
                None: 'Running',
                False: 'Failed',
                True: 'Done'}.get(self.success),
            'target': target.location}

    @classmethod
    def list_renderer(cls, defaults):
        return [t.detail_renderer() for t in
                cls.objects.filter(**defaults).order_by('-start_date')]

    @classmethod
    def get_with_permission(cls, defaults, user):
        try:
            instance = cls.objects.get(**defaults)
        except cls.DoesNotExist:
            raise Http404()
        if instance.user and instance.user != user:
            raise PermissionDenied()
        return instance
