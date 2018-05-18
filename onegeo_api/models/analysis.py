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
from django.core.exceptions import ValidationError
from django.db import models
from functools import reduce
from onegeo_api.utils import merge_two_objs


class Analysis(models.Model):

    class Meta(object):
        verbose_name = 'Analysis document'
        verbose_name_plural = 'Analysis documents'

    title = models.TextField(
        verbose_name='Title', blank=True, null=True, unique=True)

    user = models.ForeignKey(
        User, verbose_name='User', blank=True, null=True)

    document = JSONField(verbose_name='Document', blank=True, null=True)

    def clean(self, *args, **kwargs):
        components = self.get_components(
            user=self.user, exclude_pk=[self.pk])
        for component in components.keys():
            key = component[:-1]  # plural to singular
            if key in self.document:
                for val in self.document[key].keys():
                    if val in components[component]:
                        raise ValidationError(
                            "The {0} name '{1}' is already taken.".format(key, val))

    @classmethod
    def get_components(cls, user=None, exclude_pk=None):
        data = {'analyzers': [], 'normalizers': []}
        queryset = cls.objects.filter(user=user)
        if exclude_pk:
            queryset = queryset.exclude(pk__in=exclude_pk)
        for instance in queryset:
            document = instance.document
            for component in data.keys():
                key = component[:-1]  # plural to singular
                if key in document:
                    data[component].extend(list(document[key].keys()))
        return data

    @classmethod
    def get_component_by_name(cls, component, name, user=None):
        for instance in cls.objects.filter(user=user):
            if component in instance.document \
                    and name in instance.document[component]:
                return instance.document
        # else:
        raise cls.DoesNotExist(
            "Analysis component '{0}' as {1} does not exists.".format(
                name, component))


def get_complete_analysis(user=None, **kwargs):
    documents = []
    for component, names in kwargs.items():
        for name in names:
            documents.append(
                Analysis.get_component_by_name(component, name, user=user))
    return reduce(merge_two_objs, documents)
