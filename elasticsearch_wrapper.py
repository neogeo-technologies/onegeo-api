from elasticsearch import Elasticsearch
from elasticsearch import exceptions as ElasticExceptions
from threading import Thread
from uuid import uuid4

from django.conf import settings

from .tools import Singleton


class ElasticWrapper(metaclass=Singleton):

    def __init__(self):
        self.conn = Elasticsearch([{'host': settings.ES_VAR['HOST']}])
        self.conn.cluster.health(wait_for_status='yellow', request_timeout=60)

    def is_a_task_running(self):
        response = self.conn.tasks.list(actions='indices:*')
        if not response['nodes']:
            return False
        return True

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
                                collections=None, pipeline=None,
                                succeed=None, failed=None):

        def rebuild(index, name, doc_type,
                    collections, pipeline,
                    succeed=None, failed=None):
            self.push_document(index, name, doc_type, collections, pipeline,
                               succeed=succeed, failed=failed)

        try:
            self.conn.indices.create(index=index, body=body)
        except:
            raise
        else:
            if collections:
                rebuild(index, name, doc_type,
                        collections, pipeline,
                        succeed=succeed, failed=failed)
            else:
                raise Exception('TODO')

    def delete_index(self, index):
        self.conn.indices.delete(index=index)

    def delete_index_by_alias(self, name):
        indices = self.get_indices_by_alias(name)
        for index in iter(indices):
            self.delete_index(index)

    def push_document(self, index, name, doc_type,
                      collections, pipeline,
                      succeed=None, failed=None):

        def target(index, name, doc_type, collections, pipeline, succeed=None, failed=None):

            for document in collections:
                params = {'body': document, 'doc_type': doc_type,
                          'id': str(uuid4())[0:7], 'index': index}
                if pipeline is not None:
                    params.update({'pipeline': pipeline})

                try:
                    self.conn.index(**params)
                except ElasticExceptions.SerializationError:
                    continue
                except Exception as err:
                    self.delete_index(index)
                    return failed(err)

            self.switch_aliases(index, name)
            return succeed()

        thread = Thread(target=target,
                        args=(index, name, doc_type,collections, pipeline),
                        kwargs={'succeed': succeed, 'failed': failed})

        thread.start()

    def switch_aliases(self, index, name):
        """Permute l'alias vers le nouvel index. """

        body = {'actions': []}

        indices = self.get_indices_by_alias(name)
        for old_index in iter(indices):

            prev_aliases = self.get_aliases_by_index(old_index)
            for prev_alias in prev_aliases:

                if prev_alias != name:
                    body['actions'].append({'add': {
                                                'index': index,
                                                'alias': prev_alias}})

            body['actions'].append({'remove': {
                                        'index': old_index,
                                        'alias': name}})

        self.conn.indices.put_alias(index=index, name=name)
        body['actions'].append({'add': {
                                    'index': index,
                                    'alias': name}})

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
        except ElasticExceptions.RequestError as err:
            raise ValueError(str(err))

    def search(self, index, body):
        return self.conn.search(index=index, body=body)


elastic_conn = ElasticWrapper()