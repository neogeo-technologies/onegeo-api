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
import operator


class Analysis(models.Model):

    class Meta(object):
        verbose_name = 'Analysis document'
        verbose_name_plural = 'Analysis documents'

    name = models.TextField(
        verbose_name='Name', blank=True, null=True, unique=True)

    user = models.ForeignKey(User, verbose_name='User', blank=True, null=True)

    document = JSONField(verbose_name='Document', blank=True, null=True)

    def save(self, *args, **kwargs):
        try:
            self.name = self.get_analyzer()
        except NotImplementedError:
            raise ValidationError('Document analysis is malformed.')
        super().save(*args, **kwargs)

    def get_analyzer(self):
        analyzers = [
            m for m in self.document['analyzer'].keys()
            if 'analyzer' in self.document]
        if len(analyzers) < 0:
            raise NotImplementedError()  # TODO
        if len(analyzers) > 1:
            raise NotImplementedError()  # TODO
        return analyzers.pop()

    @classmethod
    def list_renderer(cls, user):
        return reduce(operator.add, [
            item.detail_renderer() for item in cls.objects.filter(user=user)])


def get_analysis_setting(analyzers):  # TODO finir
    data = {}
    for analyzer in analyzers:
        try:
            instance = Analysis.objects.get(name=analyzer)
        except Analysis.DoesNotExist:
            raise ValidationError('Analyzer does not exixts')
        data.update(instance.document)
    return data
