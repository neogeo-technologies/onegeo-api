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


from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch import exceptions
from functools import wraps
import json
from onegeo_api.exceptions import ElasticError
from onegeo_api.utils import Singleton
from uuid import uuid4


HOSTS = settings.ELASTICSEARCH_HOSTS


def elastic_exceptions_handler(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            qname = e.__class__.__qualname__
            if qname not in exceptions.__all__:
                raise e
            if qname in ('ImproperlyConfigured', 'SerializationError'):
                raise ElasticError(e.__str__())
            raise ElasticError(
                'Elasticsearch returns an error {0}: {1}.'.format(e.status_code, e.error),
                status_code=e.status_code, details=e.info, error=e.error)
    return wrapper


class ElasticWrapper(metaclass=Singleton):

    def __init__(self):
        self.conn = Elasticsearch(hosts=HOSTS)

    @elastic_exceptions_handler
    def create_index(self, index, body):
        self.conn.indices.create(index=index, body=body)

    @elastic_exceptions_handler
    def push_collection(self, index, doc_type, collection, step=10):
        body, count = '', 1
        for document in collection:
            header = {
                'index': {
                    '_index': index, '_type': doc_type, '_id': str(uuid4())}}
            body += '{0}\n{1}\n'.format(
                json.dumps(header), json.dumps(document))

            if count < step:
                count += 1
                continue
            # else:
            self.conn.bulk(index=index, doc_type=doc_type, body=body)
            body, count = '', 1
        self.conn.bulk(index=index, doc_type=doc_type, body=body)

    @elastic_exceptions_handler
    def delete_index(self, index):
        self.conn.indices.delete(index=index)

    @elastic_exceptions_handler
    def switch_aliases(self, index, name):
        body = {'actions': []}
        indices = self.get_indices_by_alias(name)
        for old_index in iter(indices):
            prev_aliases = self.get_aliases_by_index(old_index)
            for prev_alias in prev_aliases:
                if prev_alias != name:
                    body['actions'].append(
                        {'add': {'index': index, 'alias': prev_alias}})
            body['actions'].append(
                {'remove': {'index': old_index, 'alias': name}})

        self.conn.indices.put_alias(index=index, name=name)
        body['actions'].append(
            {'add': {'index': index, 'alias': name}})

        self.update_aliases(body)
        for i in range(len(indices)):
            self.delete_index(indices[i])

    @elastic_exceptions_handler
    def get_indices_by_alias(self, name):
        indices = []
        if self.conn.indices.exists_alias(name=name):
            res = self.conn.indices.get_alias(name=name)
            for index, _ in res.items():
                indices.append(index)
        return indices

    @elastic_exceptions_handler
    def get_aliases_by_index(self, index):
        aliases = []
        if self.conn.indices.exists(index=index):
            res = self.conn.indices.get_alias(index=index)
            for alias, _ in res[index]['aliases'].items():
                aliases.append(alias)
        return aliases

    @elastic_exceptions_handler
    def update_aliases(self, body):
        self.conn.indices.update_aliases(body=body)

    @elastic_exceptions_handler
    def search(self, index='_all', body=None, params={}):
        return self.conn.search(index=index, body=body, params=params)


elastic_conn = ElasticWrapper()
