from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch import exceptions as ElasticExceptions
import json
from onegeo_api.exceptions import ElasticException
from uuid import uuid4


class Singleton(type):

    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            cls.__instances[cls] = super().__call__(*args, **kwargs)
        return cls.__instances[cls]


class ElasticWrapper(metaclass=Singleton):

    def __init__(self):

        self.conn = Elasticsearch([{'host': settings.ES_VAR['HOST']}])
        self.conn.cluster.health(wait_for_status='yellow', request_timeout=60)

    def create_index(self, index, body):
        self.conn.indices.create(index=index, body=body)

    def push_collection(self, index, doc_type, collection, step=100):

        body = ''
        count = 1
        for document in collection:
            header = {
                'index': {
                    '_index': index, '_type': doc_type, '_id': str(uuid4())}}
            body += \
                '{0}\n{1}\n'.format(json.dumps(header), json.dumps(document))

            if count < step:
                count += 1
                continue

            self.conn.bulk(index=index, doc_type=doc_type, body=body)
            body, count = '', 1

        self.conn.bulk(index=index, doc_type=doc_type, body=body)

    def delete_index(self, index):
        self.conn.indices.delete(index=index)

    def switch_aliases(self, index, name):
        """Permute l'alias vers le nouvel index."""
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

    def get_indices_by_alias(self, name):

        indices = []
        if self.conn.indices.exists_alias(name=name):
            res = self.conn.indices.get_alias(name=name)
            for index, _ in res.items():
                indices.append(index)
        return indices

    def get_aliases_by_index(self, index):

        aliases = []
        if self.conn.indices.exists(index=index):
            res = self.conn.indices.get_alias(index=index)
            for alias, _ in res[index]['aliases'].items():
                aliases.append(alias)
        return aliases

    def update_aliases(self, body):
        try:
            self.conn.indices.update_aliases(body=body)
        except ElasticExceptions.RequestError as e:
            raise ValueError(e.__str__())

    def search(self, index='_all', body=None, params={}):
        try:
            return self.conn.search(index=index, body=body, params=params)
        except ElasticExceptions.TransportError as e:
            raise ElasticException(
                'Elasticsearch returns an error {0} ({1})'.format(e.status_code, e.error),
                status_code=e.status_code, details=e.info, error=e.error)


elastic_conn = ElasticWrapper()
