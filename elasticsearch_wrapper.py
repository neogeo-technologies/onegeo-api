import asyncio
from elasticsearch import Elasticsearch
from elasticsearch import exceptions as ElasticExceptions
from threading import Thread
from uuid import uuid4

from django.conf import settings

from .tools import Singleton


import json

PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


class ElasticWrapper(metaclass=Singleton):

    def __init__(self):
        self.conn = Elasticsearch([{'host': settings.ES_VAR['HOST']}])
        self.conn.cluster.health(wait_for_status='yellow', request_timeout=60)

    def create_pipeline_if_not_exists(self, id):

        body = {'description': 'Pdf',
                'processors': [{
                    'attachment': {
                        'field': 'data',
                        'ignore_missing': True,
                        'indexed_chars': -1,
                        'properties': [
                            'content',
                            'title',
                            'author',
                            'keywords',
                            'date',
                            'content_type',
                            'content_length',
                            'language']}}]}

        # try:
        #     self.conn.ingest.get_pipeline(id=id)
        # except ElasticExceptions.NotFoundError as err:
        self.conn.ingest.put_pipeline(id=id, body=body)

    def create_or_replace_index(self, index, name, doc_type, body,
                                collections=None, pipeline=None):

        def reindex(index, name):

                indices = self.get_indices_by_alias(name)
                if len(indices) < 1:
                    self.delete_index(index)
                    raise Exception('Hop hop hop.')
                if len(indices) > 1:
                    raise Exception('Hop hop hop.')
                old = indices[0]

                self.reindex(old, index)
                self.switch_aliases(index, name)

        def rebuild(index, name, doc_type, collections, pipeline):
            self.push_document(index, name, doc_type, collections, pipeline)

        try:
            self.conn.indices.create(index=index, body=body)
        except:
            raise
        else:
            if collections:
                rebuild(index, name, doc_type, collections, pipeline)
            else:
                reindex(index, name)

    def delete_index(self, index):
        self.conn.indices.delete(index=index)

    def delete_index_by_alias(self, name):
        indices = self.get_indices_by_alias(name)
        for index in iter(indices):
            self.delete_index(index)

    def push_document(self, index, name, doc_type, collections, pipeline):
              
        def callback(index, name, doc_type, collections, pipeline):

            for document in collections:
                params = {'body': document, 'doc_type': doc_type,
                          'id': str(uuid4())[0:7], 'index': index}
                if pipeline is not None:
                    params.update({'pipeline': pipeline})

                self.conn.index(**params)

            self.switch_aliases(index, name)

        thread = Thread(target=callback, args=(index, name, doc_type, collections, pipeline))
        thread.start()

    # def push_mapping(self, index, doc_type, body):

    #     params = {'index': index, 'doc_type': doc_type, 'body': body}
    #     self.conn.indices.put_mapping(**params)

    # def push_settings(self, index, body):

    #     self.conn.indices.put_settings(body=body, index=index)

    def reindex(self, source, dest):

        body = {'source': {'index': source}, 'dest': {'index': dest}}
        res = self.conn.reindex(body=body)

    def switch_aliases(self, index, name):
        """Permute l'alias vers le nouvel index. """

        body = {'actions': []}

        indices = self.get_indices_by_alias(name)
        for i in range(len(indices)):
            body['actions'].append(
                            {'remove': {'index': indices[i], 'alias': name}})

        self.conn.indices.put_alias(index=index, name=name)
        body['actions'].append({'add': {'index': index, 'alias': name}})

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

    def update_aliases(self, body):
        self.conn.indices.update_aliases(body=body)


elastic_conn = ElasticWrapper()
