from abc import ABCMeta, abstractmethod
from django.http import JsonResponse
from functools import partial, wraps
from json import dumps, loads
from re import sub, findall
from ..utils import clean_my_obj


def input_parser(f):

    @wraps(f)
    def wrapper(self, **params):
        config = dumps(self.config)

        for k, v in params.items():
            config = config.replace('{{%{0}%}}'.format(k), v)

        config = sub('\"\{\%\s*((\d+\s*[-+\*/]?\s*)+)\%\}\"',
                     partial(lambda m: str(eval(m.group(1)))), config)

        config = sub('\"\{\%(\s*((\d+\s*[-+\*/]?\s*)+)|\w+)\%\}\"',
                     'null', config)

        self.config = loads(config)
        return f(self, **params)
    return wrapper


class AbstractPlugin(metaclass=ABCMeta):

    def __init__(self, config, contexts, **kwargs):
        self.config = config
        self.contexts = contexts

        self.columns_by_index = {}
        for context in self.contexts:
            self.columns_by_index[context.name] = tuple(
                    (p['alias'] and p['alias'] or p['name'], p['type'])
                    for p in context.clmn_properties if not p['rejected'])

        self.qs = []
        for find in findall('\{\%\w+\%\}', dumps(self.config)):
            self.qs.append((find[2:-2], None, None))

    @abstractmethod
    def input(self, **params):
        raise NotImplementedError('This is an abstract method. '
                                  "You can't do anything with it.")

    @abstractmethod
    def output(self, data, **params):
        raise NotImplementedError('This is an abstract method. '
                                  "You can't do anything with it.")


class Plugin(AbstractPlugin):

    def __init__(self, config, contexts, **kwargs):
        super().__init__(config, contexts, **kwargs)

    @input_parser
    def input(self, **params):
        if self.config and not params:
            return {'query': {'match_all': {}}}
        if not self.config:
            return {'query': {'match_all': {}}}
        return self.config

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
