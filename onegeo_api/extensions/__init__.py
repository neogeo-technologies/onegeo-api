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


from abc import ABCMeta
from abc import abstractmethod
from django.http import JsonResponse
from json import dumps
from json import loads
import re


DEFAULT_QUERY_DSL = {
    'from': '{%from|0%}',
    'highlight': {
        'fields': {
            'properties.*': {
                'post_tags': ['</strong>'],
                'pre_tags': ['<strong>'],
                'type': 'plain'}}},
    'query': {
        'bool': {
            'should': [{
                'match_all': {}}, {
                'multi_match': {
                    'fields': ['properties.*'],
                    'fuzziness': 'auto',
                    'query': '{%query%}'}}]}},
    'size': '{%size|10%}'}


class AbstractPlugin(metaclass=ABCMeta):

    def __init__(self, query_dsl, index_profiles, **kwargs):
        self.query_dsl = query_dsl
        self.index_profiles = index_profiles

        self.columns_by_index = {}
        for index_profile in self.index_profiles:
            self.columns_by_index[index_profile.name] = tuple(
                (p['alias'] and p['alias'] or p['name'], p['type'])
                for p in index_profile.columns if not p['rejected'])

        self.qs = []
        for found in re.findall('(?<={%).+?(?=%})', dumps(self.query_dsl)):
            kv = tuple(found.split('|'))
            k, v = len(kv) == 2 and (kv[0], kv[1]) or (kv[0], None)
            self.qs.append((k, None, None, v))

    @abstractmethod
    def input(self, **params):
        raise NotImplementedError(
            "This is an abstract method. You can't do anything with it.")

    @abstractmethod
    def output(self, data, **params):
        raise NotImplementedError(
            "This is an abstract method. You can't do anything with it.")


class Plugin(AbstractPlugin):

    def __init__(self, query_dsl, index_profiles, **kwargs):
        super().__init__(query_dsl, index_profiles, **kwargs)

    def input(self, **params):
        self.query_dsl = loads(re.sub(
            '{%.+?%}',
            lambda m: re.sub(
                '{%(\w+)(\|(.+))?%}',
                lambda m: params.get(m.group(1), m.group(3)),
                m.group(0)),
            dumps(self.query_dsl)))
        return self.query_dsl

    def output(self, data, **params):

        results = []
        for hit in data['hits']['hits']:
            d1 = {'id': '_id' in hit and hit['_id'] or None,
                  'score': '_score' in hit and hit['_score'] or None,
                  'index': '_type' in hit and hit['_type'] or None}

            if 'highlight' in hit and hit['highlight']:
                d1['highlight'] = hit['highlight']

            d2 = dict((k, v) for k, v in hit['_source'].items())

            results.append({**d1, **d2})

        response = {'results': results,
                    'total': data['hits']['total']}

        if 'aggregations' in data:
            response['aggregations'] = data['aggregations']

        return JsonResponse(response)


plugin = Plugin
