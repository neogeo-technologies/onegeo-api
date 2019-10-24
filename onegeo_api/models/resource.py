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
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.urls import reverse
from onegeo_api.models.abstracts import AbstractModelProfile
import re


class Resource(AbstractModelProfile):

    class Extras(object):
        fields = ('columns', 'location', 'title')

    class Meta(object):
        verbose_name = 'Resource'
        verbose_name_plural = 'Resources'

    columns = JSONField(verbose_name='Columns')

    source = models.ForeignKey(
        to='Source', verbose_name='Source', on_delete=models.CASCADE)

    typename = models.CharField(
        verbose_name='Typename', max_length=100, blank=True, null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._onegeo = None

    @property
    def indexes(self):
        return self.indexprofile_set.all()

    @property
    def location(self):
        return reverse(
            'onegeo_api:resource', kwargs={'source': str(self.source.name),
                                           'name': str(self.name)})

    @location.setter
    def location(self, value):
        try:
            self.nickname = re.search(
                'sources/(?P<name>(\w|-){1,100})/?$', value).group('name')
        except AttributeError:
            raise AttributeError("'Location' attibute is malformed.")

    @location.deleter
    def location(self, *args, **kwargs):
        raise AttributeError('Attribute is locked, you can not delete it.')

    @property
    def onegeo(self, *args, **kwargs):
        if not self._onegeo:
            self._onegeo = \
                self.source.onegeo.get_resources(
                    names=[self.typename], columns=self.columns)[0]
        return self._onegeo

    @onegeo.setter
    def onegeo(self, *args, **kwargs):
        raise AttributeError('Attribute is locked, you can not change it.')

    @onegeo.deleter
    def onegeo(self):
        raise AttributeError('Attribute is locked, you can not delete it.')

    def detail_renderer(self, **kwargs):
        return {
            'columns': self.columns,
            'indexes': [m.location for m in self.indexes],
            'location': self.location,
            'title': self.title,
            'uuid': self.uuid}

    @classmethod
    def list_renderer(cls, name, user, **kwargs):
        model = apps.get_model(app_label='onegeo_api', model_name='Source')
        source = model.get_or_raise(name, user=user)
        return [
            item.detail_renderer(**kwargs)
            for item in cls.objects.filter(source=source).order_by('title')]
