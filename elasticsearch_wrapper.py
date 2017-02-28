from elasticsearch import Elasticsearch
from elasticsearch import exceptions as ElasticExceptions
from threading import Thread
from uuid import uuid4

from django.conf import settings

from .tools import Singleton
from .tools import Promise
from .tools import FuncThread


PDF_BASE_DIR = settings.PDF_DATA_BASE_DIR


class ElasticConnexion(metaclass=Singleton):

    ES = Elasticsearch([{'host': settings.ES_VAR["HOST"]}])

    def __init__(self, *args, **kwargs):

        self.ES.cluster.health(wait_for_status='yellow', request_timeout=60)

    def __switch_aliases(self, index, name):

        def callback(index, name):
            body = {'actions': []}
            if self.ES.indices.exists_alias(name=name):
                obj = self.ES.indices.get_alias(name=name)
                for k, v in obj.items():
                    body['actions'].append({'remove': {'index': k, 'alias': name}})

            self.ES.indices.put_alias(index=index, name=name)
            body['actions'].append({'add': {'index': index, 'alias': name}})

            self.ES.indices.update_aliases(body=body)

        thread = Thread(target=callback, args=(index, name))
        thread.start()

    def __push_mapping(self, index, doc_type, body):

        params = {'index': index, 'doc_type': doc_type, 'body': body}
        self.ES.indices.put_mapping(**params)

    def __push_document(self, index, doc_type, collections, pipeline=None):
        p = Promise()
        
        def callback(index, doc_type, collections, pipeline):
            for document in collections:
                params = {'body': document, 'doc_type': doc_type,
                          'id': str(uuid4())[0:7], 'index': index}
                if pipeline is not None:
                    params.update({'pipeline': pipeline})

                self.ES.index(**params)

            p.resolve(True)

        thread = Thread(target=callback, args=(index, doc_type, collections, pipeline))
        thread.start()

        return p

    def create_or_replace_index(self, index, name, doc_type, body, collections=None, pipeline=None):

        try:
            self.ES.indices.create(index=index, ignore=400)
        except:
            return
        else:
            self.__push_mapping(index, doc_type, body)
            if collections is not None:
                self.__push_document(index, doc_type, collections, pipeline=pipeline)
            else: 
            	# TODO
                pass
            self.__switch_aliases(index, name)

    def push_pipeline_if_not_exists(self, id):

        body = {"description": "Pdf",
                "processors": [{
                    "attachment": {
                        "field": "data",
                        "ignore_missing": True,
                        "indexed_chars": -1,
                        "properties": [
                            "content",
                            "title", 
                            "author",
                            "keywords",
                            "date",
                            "content_type",
                            "content_length",
                            "language"]}}]}

        try:
            self.ES.ingest.get_pipeline(id=id)
        except ElasticExceptions.NotFoundError as err:
            self.ES.ingest.put_pipeline(id=id, body=body)

