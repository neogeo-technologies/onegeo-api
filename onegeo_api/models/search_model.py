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


from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from onegeo_api.extensions import DEFAULT_QUERY_DSL
from onegeo_api.models.abstracts import AbstractModelProfile
import re


class SearchModel(AbstractModelProfile):

    class Extras(object):
        fields = ('indexes', 'location', 'name', 'query_dsl', 'service_url')

    class Meta(object):
        verbose_name = 'Search Model'
        verbose_name_plural = 'Search Models'

    PATHNAME = '/services/{service}'

    query_dsl = JSONField(
        verbose_name='Query DSL', blank=True, null=True)

    user = models.ForeignKey(
        to=User, verbose_name='User', blank=True, null=True)

    indexes = models.ManyToManyField(
        to='IndexProfile', verbose_name='Indexation profiles')

    @property
    def location(self):
        return self.PATHNAME.format(service=self.alias.handle)

    @location.setter
    def location(self, value):
        try:
            self.nickname = re.search('^{}$'.format(
                self.PATHNAME.format(service='(\w+)/?')), value).group(1)
        except AttributeError:
            raise AttributeError("'Location' attibute is malformed.")

    @location.deleter
    def location(self):
        raise AttributeError('Attibute is locked, you can not delete it.')

    def detail_renderer(self, include=False, cascading=False, **kwargs):
        opts = {'include': cascading and include, 'cascading': cascading}
        return {
            'query_dsl': self.query_dsl,
            'indexes': [
                m.detail_renderer(**opts) if include else m.location
                for m in self.indexes.all()],
            'location': self.location,
            'name': self.name,
            'service_url': 'http://{0}{1}'.format(
                get_current_site(None),
                reverse('onegeo_api:seamod_detail_search',
                        kwargs={'nickname': self.alias.handle}))}

    @classmethod
    def list_renderer(cls, user, **opts):
        return [
            search_model.detail_renderer(**opts)
            for search_model in cls.objects.filter(user=user)]

    def save(self, *args, **kwargs):

        if not self.name:
            raise ValidationError(
                'Some of the input paramaters needed are missing.')

        if not self.query_dsl:
            self.query_dsl = DEFAULT_QUERY_DSL

        super().save(*args, **kwargs)
