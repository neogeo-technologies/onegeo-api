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
# from django.http import Http404
from elasticsearch import Elasticsearch
from elasticsearch import exceptions
# from elasticsearch import helpers
from functools import wraps
import gc
import itertools
from onegeo_api.exceptions import ElasticError
from onegeo_api.utils import estimate_size
from onegeo_api.utils import Singleton
import operator
# import json
# from io import StringIO


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
            # if qname == 'NotFoundError':
            #     raise Http404
            if qname in ('ImproperlyConfigured', 'SerializationError'):
                raise ElasticError(e.__str__())
            raise ElasticError(
                'Elasticsearch returns an error {0}: {1}.'.format(e.status_code, e.error),
                status_code=e.status_code, details=e.info, error=e.error)
    return wrapper


class ElasticWrapper(metaclass=Singleton):

    def __init__(self):
        self.conn = Elasticsearch(hosts=HOSTS)

    def create_or_reindex(self, index=None, body=None, alias=None,
                          collection=None, columns_mapping=None,
                          update=None, pipeline=False):

        prev_indices = self.get_indices_by_alias(alias, unique=True)
        if len(prev_indices) > 1:
            raise Exception('TODO')

        self.create_index(index, body)

        created = []
        failed = []
        reindexed = []

        docs = {}
        if len(prev_indices) == 1:
            prev_index = prev_indices[0]
            docs = self.list_documents(index=prev_index)

        if docs:
            actual = [
                (dict(e[0]), list(m[0] for m in e[1]))
                for e in itertools.groupby(
                    docs[prev_index], key=operator.itemgetter(1))]
            try:
                reindexed, _failed, created = \
                    self.reindex_collection(
                        prev_index, index, collection, actual,
                        columns_mapping, update=update, pipeline=pipeline)
            except Exception as e:
                self.delete_index(index)
                raise e
            else:
                failed += _failed
        else:
            try:
                created, _failed = self.index_collection(
                    index, collection, columns_mapping, pipeline=pipeline)
            except Exception as e:
                self.delete_index(index)
                raise e
            else:
                failed += _failed

        self.switch_aliases(index, alias)

        return created, reindexed, failed

    @elastic_exceptions_handler
    def create_index(self, index, body):
        self.conn.indices.create(index=index, body=body)

    @elastic_exceptions_handler
    def reindex_collection(self, prev_index, next_index, collection,
                           actual, columns_mapping, step=1000,
                           chunk_size=10485760, update=False, pipeline=False):

        painless = []
        REPLACE_COLUMN = (
            'ctx._source.properties["{new}"]=ctx._source.properties.remove("{old}");'
            'ctx._source._columns_mapping["{raw}"]="{new}"')
        ADD_COLUMN = (
            'ctx._source.properties["{new}"]=ctx._source._backup.remove("{raw}");'
            'ctx._source._columns_mapping["{raw}"]="{new}"')
        REMOVE_COLUMN = (
            'ctx._source.properties.remove("{old}");'
            'ctx._source._columns_mapping.remove("{raw}")')

        prev_collection = []
        for prev_columns_mapping, prev_docs in actual:

            left = set()
            right = set()
            gc.collect(generation=2)

            prev_collection += prev_docs
            if prev_columns_mapping != columns_mapping:

                left = set(prev_columns_mapping) - set(columns_mapping)
                right = set(columns_mapping) - set(prev_columns_mapping)
                intersect = set.intersection(
                    set(prev_columns_mapping), set(columns_mapping))

                if intersect:
                    for raw in intersect:
                        new = columns_mapping[raw]
                        old = prev_columns_mapping.get(raw)
                        if old and new != old:
                            painless.append(
                                REPLACE_COLUMN.format(
                                    new=new, old=old, raw=raw))
                if left:
                    for raw in left:
                        painless.append(
                            REMOVE_COLUMN.format(
                                old=prev_columns_mapping[raw], raw=raw))
                if right:
                    for raw in right:
                        painless.append(
                            ADD_COLUMN.format(
                                new=columns_mapping[raw], raw=raw))

        to_reindex = []
        created = []
        failed = []

        if update:

            body = []
            body_size = 0
            # count = 0
            for document in collection:
                # count += 1
                # if count > 5000:
                #     break

                md5 = document.get('_md5')
                if md5 in prev_collection:
                    to_reindex.append(md5)
                else:

                    header = {'index': {'_id': md5, '_index': next_index, '_type': next_index}}
                    document['_columns_mapping'] = columns_mapping
                    doc = [header, document]

                    try:
                        doc_size = estimate_size(doc)
                    except RecursionError:
                        failed.append({md5: 'Unable to estimate size.'})
                        continue
                    if doc_size > 104857600:
                        failed.append({md5: 'File size exceed max limit.'})
                        continue

                    x = len(body) / 2
                    reload = x == step
                    one_bullet_left = body_size + doc_size > chunk_size

                    if one_bullet_left or reload:
                        self._bulk(
                            next_index, next_index, body, pipeline,
                            created=lambda z: created.append(z),
                            failed=lambda z: failed.append(z))
                        body, body_size = doc, doc_size
                        continue

                    body += doc
                    body_size += doc_size

            if body:
                self._bulk(
                    next_index, next_index, body, pipeline,
                    created=lambda z: created.append(z),
                    failed=lambda z: failed.append(z))

        else:
            to_reindex = prev_collection

        count = len(to_reindex)
        if count:
            x = 0
            for i in range(0, count - 1, step):
                y = (count > i) and i < step and i or step + i
                body = {
                    'size': len(to_reindex[x:y]),
                    'source': {
                        'index': prev_index,
                        'type': prev_index,
                        'query': {
                            'ids': {
                                'type': prev_index,
                                'values': to_reindex[x:y]}}},
                    'dest': {
                        'index': next_index,
                        'type': next_index,
                        'version_type': 'internal'}}

                if painless:
                    body['script'] = {
                        'source': ';'.join(painless),
                        'lang': 'painless'}

                res = self.conn.reindex(body)
                # TODO parse res
                failed += res.get('failure', [])
                x += step

        return list(to_reindex), failed, created

    # @elastic_exceptions_handler
    # def index_collection(self, index, collection, columns_mapping, pipeline=False):
    #
    #     def _data():
    #         for doc in collection:
    #             total = 0
    #             total += estimate_size(doc)
    #
    #             _id = doc.pop('_md5')
    #             doc['_columns_mapping'] = columns_mapping
    #             yield {
    #                 '_index': index,
    #                 '_id': _id,
    #                 '_op_type': 'index',
    #                 '_type': index,
    #                 'doc': doc,
    #                 'pipeline': pipeline and 'attachment' or None}
    #
    #     return helpers.bulk(
    #         self.conn, _data(),
    #         chunk_size=100, max_chunk_bytes=10 * 1024 * 1024,
    #         raise_on_error=False, raise_on_exception=False,
    #         max_retries=2, initial_backoff=2, stats_only=False,
    #         max_backoff=600, yield_ok=True)

    def _bulk(self, index, doc_type, body, pipeline, created=None, failed=None):
        try:
            res = self.conn.bulk(
                index=index, doc_type=doc_type, body=body,
                pipeline=pipeline and 'attachment' or None)
        except exceptions.SerializationError as e:
            print(e)
            return
        except ValueError as e:
            print(e)
            return
        for item in res.get('items'):
            md5 = item['index']['_id']
            error = item['index'].get('error')
            if error:
                callable(failed) and failed({md5: error})
            else:
                callable(created) and created(md5)

    @elastic_exceptions_handler
    def index_collection(self, index, collection, columns_mapping,
                         pipeline=False, step=100, chunk_size=10485760):
        created = []
        failed = []
        body = []
        body_size = 0
        # count = 0

        for document in collection:
            # count += 1
            # if count > 5000:
            #     break

            md5 = document.pop('_md5')
            header = {'index': {'_id': md5, '_index': index, '_type': index}}
            document['_columns_mapping'] = columns_mapping
            doc = [header, document]

            try:
                doc_size = estimate_size(doc)
            except RecursionError:
                failed.append({md5: 'Unable to estimate size.'})
                continue
            if doc_size > 104857600:
                failed.append({md5: 'File size exceed max limit.'})
                continue

            x = len(body) / 2
            reload = x == step
            one_bullet_left = body_size + doc_size > chunk_size

            if one_bullet_left or reload:
                self._bulk(
                    index, index, body, pipeline,
                    created=lambda z: created.append(z),
                    failed=lambda z: failed.append(z))
                body, body_size = doc, doc_size
                continue

            body += doc
            body_size += doc_size

        # else:
        if body:
            self._bulk(
                index, index, body, pipeline,
                created=lambda z: created.append(z),
                failed=lambda z: failed.append(z))

        return created, failed

    @elastic_exceptions_handler
    def is_index_exists(self, **kwargs):
        return self.conn.indices.exists(**kwargs)

    @elastic_exceptions_handler
    def get_index(self, index='_all', **kwargs):
        kwargs.setdefault('flat_settings', True)
        return self.conn.indices.get(index=index, **kwargs)

    @elastic_exceptions_handler
    def delete_index(self, index, **kwargs):
        self.conn.indices.delete(index=index, **kwargs)

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
    def get_indices_by_alias(self, name, unique=False):
        indices = []
        if self.conn.indices.exists_alias(name=name):
            res = self.conn.indices.get_alias(name=name)
            for index, _ in res.items():
                indices.append(index)
        if unique and len(indices) > 1:
            raise Exception('Index should be unique.')  # TODO
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

    @elastic_exceptions_handler
    def list_documents(self, index, step=1000, **kwargs):

        x = 0
        l = []
        search_after = None
        count = self.conn.count(index=index).get('count')
        for i in range(0, count - 1, step):
            y = (count > i) and i < step and i or step
            body = {
                '_source': '_columns_mapping',
                'query': {'match_all': {}},
                'size': y,
                'sort': {'_id': 'asc'},
                'stored_fields': []}

            if x < 10000:
                body['from'] = x
            else:
                body['search_after'] = [search_after]

            res = self.conn.search(index=index, body=body)
            l += [(
                hit['_index'],
                hit['_id'],
                tuple(sorted([(k, v) for k, v in hit['_source'].get('_columns_mapping', {}).items()]))
                ) for hit in res['hits']['hits']]

            x += step
            search_after = l[-1][1]

        groups = itertools.groupby(
            sorted(l, key=operator.itemgetter(0)), key=operator.itemgetter(0))

        return dict((g[0], [(m[1], m[2]) for m in tuple(g[1])]) for g in groups)

    @elastic_exceptions_handler
    def get_all_documents(self, index, step=1000, **kwargs):
        _source = kwargs.pop('_source', [])

        x = 0
        search_after = None
        count = self.conn.count(index=index).get('count')
        for i in range(0, count - 1, step):
            y = (count > i) and i < step and i or step
            body = {
                '_source': _source,
                'query': {'match_all': {}},
                'size': y,
                'sort': {'_id': 'asc'},
                'stored_fields': []}

            if x < 10000:
                body['from'] = x
            else:
                body['search_after'] = [search_after]

            res = self.conn.search(index=index, body=body)
            yield from res['hits']['hits']
            x += step
            search_after = res['hits']['hits'][-1]['_id']

    def create_pipeline(self, field='_raw'):
        body = {'description': 'Attachment',
                'processors': [{
                    'attachment': {
                        'field': field,
                        'ignore_missing': True,
                        'indexed_chars': -1}}]}
        self.conn.ingest.put_pipeline(id='attachment', body=body)
        return True


elastic_conn = ElasticWrapper()
