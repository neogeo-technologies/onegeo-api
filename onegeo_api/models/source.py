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


from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from onegeo_api.models.abstracts import AbstractModelProfile
import onegeo_manager
import re


class Source(AbstractModelProfile):

    class Extras(object):
        fields = ('location', 'protocol', 'title', 'uri')

    class Meta(object):
        verbose_name = 'Source'
        verbose_name_plural = 'Sources'

    PROTOCOL_CHOICES = onegeo_manager.protocol.all()

    protocol = models.CharField(
        verbose_name='Protocol', max_length=100, choices=PROTOCOL_CHOICES)

    uri = models.CharField(verbose_name='URI', max_length=2048)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._onegeo = None

    @property
    def location(self):
        return reverse(
            'onegeo_api:source', kwargs={'name': str(self.name)})

    @location.setter
    def location(self, value):
        try:
            self.nickname = re.search(
                'sources/(?P<name>(\w|-){1,100})/?$', value).group('name')
        except AttributeError:
            raise AttributeError("'Location' attribute is malformed.")

    @location.deleter
    def location(self, *args, **kwargs):
        raise AttributeError('Attibute is locked, you can not delete it.')

    @property
    def onegeo(self):
        if not self._onegeo:
            self._onegeo = onegeo_manager.Source(self.uri, self.protocol)
        return self._onegeo

    @onegeo.setter
    def onegeo(self, *args, **kwargs):
        raise AttributeError('attribute is locked, you can not change it.')

    @onegeo.deleter
    def onegeo(self, *args, **kwargs):
        raise AttributeError('attribute is locked, you can not delete it.')

    def iter_resources(self):
        instance = apps.get_model(
            app_label='onegeo_api', model_name='Resource')
        return iter(item for item in instance.objects.filter(source=self))

    def detail_renderer(self, **kwargs):
        return {
            'location': self.location,
            'title': self.title,
            'protocol': self.protocol,
            'uuid': self.uuid,
            'uri': self.uri}

    @classmethod
    def list_renderer(cls, user, **opts):
        return [item.detail_renderer(**opts) for item
                in cls.objects.filter(user=user).order_by('title')]

    def save(self, *args, **kwargs):

        if not self.title or not self.protocol or not self.uri:
            raise ValidationError(
                'Some of the input paramaters needed are missing.')

        if self.protocol not in dict(self.PROTOCOL_CHOICES).keys():
            raise ValidationError("'protocol' input parameters is unauthorized.")

        super().save(*args, **kwargs)
