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


from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from onegeo_api.models.abstracts import AbstractModelProfile
import onegeo_manager
import re


class IndexProfile(AbstractModelProfile):

    class Extras(object):
        fields = (
            'columns', 'location', 'name', 'resource', 'reindex_frequency')

    class Meta(object):
        verbose_name = 'Indexation Profile'
        verbose_name_plural = 'Indexation Profiles'

    PATHNAME = 'indexes'

    REINDEX_FREQUENCY_CHOICES = (
        ('monthly', 'monthly'),
        ('weekly', 'weekly'),
        ('daily', 'daily'))

    columns = JSONField(verbose_name='Columns', blank=True, null=True)

    reindex_frequency = models.CharField(
        verbose_name='Re-indexation frequency',
        choices=REINDEX_FREQUENCY_CHOICES,
        default=REINDEX_FREQUENCY_CHOICES[0][0],
        max_length=250)

    resource = models.ForeignKey(to='Resource', verbose_name='Resource')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._onegeo = None
        try:
            self._prev_nickname = self.alias.handle
        except Exception:
            self._prev_nickname = None

    @property
    def location(self):
        return '/{0}/{1}'.format(self.PATHNAME, self.alias.handle)

    @location.setter
    def location(self, value):
        try:
            self.nickname = re.search(
                '^/{}/(\w+)/?$'.format(self.PATHNAME), value).group(1)
        except AttributeError:
            raise AttributeError("'Location' attibute is malformed.")

    @location.deleter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not delete it.')

    @property
    def onegeo(self):
        if not self._onegeo:
            self._onegeo = \
                onegeo_manager.IndexProfile('foo', self.resource.onegeo)
        return self._onegeo

    @onegeo.setter
    def onegeo(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not change it.')

    @onegeo.deleter
    def onegeo(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not delete it.')

    def detail_renderer(self, include=False, cascading=False, **kwargs):
        return {
            'columns': self.columns,
            'location': self.location,
            'name': self.name,
            'reindex_frequency': self.reindex_frequency,
            'resource': self.resource.location}

    @classmethod
    def list_renderer(cls, user, **opts):
        return [item.detail_renderer(**opts)
                for item in cls.objects.filter(user=user)]

    def save(self, *args, **kwargs):

        if not self.name or not self.resource:
            raise ValidationError(
                'Some of the input paramaters needed are missing.')

        if not self.columns:
            self.columns = \
                [prop.all() for prop in self.onegeo.iter_properties()]
        # else: # TODO Vérifier si le document est conforme

        return super().save(*args, **kwargs)
