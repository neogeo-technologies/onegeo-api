from abc import ABCMeta
from abc import abstractmethod
from django.http import JsonResponse
from functools import partial
from functools import wraps
from json import dumps
from json import loads
from re import findall
from re import sub


DEFAULT_QUERY_DSL = {
    'from': '{%from%}',
    'highlight': {
        'fields': {
            'properties.*': {
                'post_tags': ['</strong>'],
                'pre_tags': ['<strong>'],
                'type': 'plain'}}},
    'query': {
        'bool': {
            'must': [{
                'multi_match': {
                    'fields': ['properties.*'],
                    'fuzziness': 'auto',
                    'query': '{%query%}'}}]}},
    'size': '{%size%}'}


def input_parser(f):

    @wraps(f)
    def wrapper(self, **params):
        query_dsl = dumps(self.query_dsl)

        for k, v in params.items():
            query_dsl = query_dsl.replace('{{%{0}%}}'.format(k), v)

        query_dsl = sub(
            '\"\{\%\s*((\d+\s*[-+\*/]?\s*)+)\%\}\"',
            partial(lambda m: str(eval(m.group(1)))), query_dsl)

        query_dsl = sub(
            '\"\{\%(\s*((\d+\s*[-+\*/]?\s*)+)|\w+)\%\}\"', 'null', query_dsl)

        self.query_dsl = loads(query_dsl)

        print(self.query_dsl)

        return f(self, **params)

    return wrapper


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
        for find in findall('\{\%\w+\%\}', dumps(self.query_dsl)):
            self.qs.append((find[2:-2], None, None))

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

    @input_parser
    def input(self, **params):
        if self.query_dsl and not params:
            return DEFAULT_QUERY_DSL
        if not self.query_dsl:
            return DEFAULT_QUERY_DSL
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
