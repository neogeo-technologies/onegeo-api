# from django.conf import settings
from elasticsearch import exceptions as ElasticExceptions
from elasticsearch import Elasticsearch
from threading import Thread
from uuid import uuid4
import json


class Singleton(type):

    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            cls.__instances[cls] = super().__call__(*args, **kwargs)
        return cls.__instances[cls]


class ElasticWrapper(metaclass=Singleton):

    def __init__(self):

        # self.conn = Elasticsearch([{'host': settings.ES_VAR['HOST']}])
        # self.conn.cluster.health(wait_for_status='yellow', request_timeout=60)
        # self.conn = None
        self.conn = Elasticsearch()

    def format_md_mapping(self, mapping):

        m = mapping['properties']['properties'].copy()
        # m['properties']['uri'] = mapping['properties']['uri']
        m['properties']['href'] = {
            'include_in_all': False,
            'index': 'not_analyzed',
            'store': False,
            'type': 'keyword'}

        return {'metadata-fr': m}

    def get_analyzer(self, name):
        return "standard"
        # return self._es_analysis['analyzer'].get(name)

    def get_token_filters(self, analyzer):
        return "model_french_stop"
        # return self._es_analysis['analyzer'][analyzer]['filter']

    def get_filter(self, name):
        return "model_asciifolding"
        # return self._es_analysis['filter'].get(name)

    def update_es_settings(self, idx_profile):
        analysis = {'analysis': {'analyzer': {}, 'filter': {}}}

        for elt in idx_profile.onegeo.iter_properties():
            print(elt)
            if not elt.column_type == 'text':
                continue
            # p.analyzer = p.analyzer or config.default_analyzer
            elt.analyzer = elt.analyzer or "standard"

            if elt.analyzer not in analysis['analysis']['analyzer'].keys():
                analysis['analysis']['analyzer'][elt.analyzer] = \
                    self.get_analyzer(elt.analyzer)

            for token in self.get_token_filters(analyzer=elt.analyzer):
                if self.get_filter(token) and \
                        token not in analysis['analysis']['filter'].keys():
                    analysis['analysis']['filter'][token] = \
                        self.get_filter(token)

        return idx_profile, analysis

    def create_index(self, index, body):

        if self.conn.indices.exists(index):
            # logging.info('Re-creating Elastic index {0}'.format(index))
            self.conn.indices.delete(index=index)
        else:
            # logging.info('Creating Elastic index {0}'.format(index))
            self.conn.indices.create(index=index, body=body)

    def push_collection(self,index, doc_type, collections, step=100):

        def send_bulk(_index, _type, _body, _count):
            self.conn.bulk(index=_index, doc_type=_type, body=_body)
            # logging.info('{0} documents sent'.format(_count))

        # logging.info(
        #     'Pushing Feature collection data to Elastic index {0}'.format(index))

        body, count = '', 1
        x=1
        for x, document in enumerate(collections, 1):
            header = {
                'index': {
                    '_index': index, '_type': doc_type, '_id': str(uuid4())[:7]}}
            body += \
                '{0}\n{1}\n'.format(json.dumps(header), json.dumps(document))

            if count < step:
                count += 1
                continue
            send_bulk(index, doc_type, body, x)
            body, count = '', 1

        send_bulk(index, doc_type, body, x)




    def create_pipeline_if_not_exists(self, id):

        body = {'description': 'Pdf',
                'processors': [{
                    'attachment': {
                        'field': 'raw_data',
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

        self.conn.ingest.put_pipeline(id=id, body=body)

    def create_or_replace_index(self, index, name, doc_type, body,
                                collections=None, pipeline=None,
                                succeed=None, failed=None, error=None):

        def rebuild(index, name, doc_type, collections, pipeline,
                    succeed=None, failed=None, error=error):

            self.push_document(index, name, doc_type, collections, pipeline,
                               succeed=succeed, failed=failed, error=error)

        try:
            self.conn.indices.create(index=index, body=body)
        except Exception as err:
            raise err

        if collections:
            rebuild(index, name, doc_type, collections, pipeline,
                    succeed=succeed, failed=failed, error=error)
        else:
            raise Exception('TODO')

    def delete_index(self, index):

        self.conn.indices.delete(index=index)

    def delete_index_by_alias(self, name):

        indices = self.get_indices_by_alias(name)
        for index in iter(indices):
            self.delete_index(index)

    def push_document(self, index, name, doc_type, collections, pipeline,
                      succeed=None, failed=None, error=None):

        def target(index, name, doc_type, collections, pipeline,
                   succeed=None, failed=None, error=None):

            count = 0
            for document in collections:
                params = {'body': document, 'doc_type': doc_type,
                          'id': str(uuid4())[0:7], 'index': index}

                if pipeline is not None:
                    params.update({'pipeline': pipeline})
                try:
                    self.conn.index(**params)
                except ElasticExceptions.SerializationError as err:
                    error(str(err))
                    continue
                except ElasticExceptions.TransportError as err:
                    continue
                except Exception as err:
                    self.delete_index(index)
                    return failed(str(err))
                else:
                    count += 1
            else:
                self.switch_aliases(index, name)

                if count == 0:
                    msg = 'Aucun document à indexer. '
                if count == 1:
                    msg = '1 document a été indexé avec succès. '
                if count > 1:
                    msg = '{0} documents ont été indexés avec succès. '.format(count)

                return succeed(msg)

        thread = Thread(target=target,
                        args=(index, name, doc_type, collections, pipeline),
                        kwargs={'succeed': succeed, 'failed': failed, 'error': error})
        thread.start()

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
        except ElasticExceptions.RequestError as err:
            raise ValueError(str(err))

    def search(self, index, body):
        try:
            return self.conn.search(index=index, body=body)
        except Exception as err:
            # TODO: gérer les exceptions
            raise Exception(str(err))


elastic_conn = ElasticWrapper()
