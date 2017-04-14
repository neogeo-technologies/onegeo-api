from abc import ABCMeta
from functools import partial, wraps
from json import dumps, loads
from re import sub


def format_elasticsearch_response(f):

    @wraps(f)
    def wrapper(self, data, **params):

        results = []
        for hit in data['hits']['hits']:
            results.append({
                'id': '_id' in hit and hit['_id'] or None,
                'score': '_score' in hit and hit['_score'] or None,
                'context': '_type' in hit and hit['_type'] or None,
                'content': '_source' in hit and hit['_source'] or None})

        response = {'results': results}

        return f(self, response, **params)

    return wrapper


class AbstractPlugin(metaclass=ABCMeta):

    def input(self, config, **params):

        if not config:
            return {'query': {'match_all': {}}}

        str_json = dumps(config)

        for k, v in params.items():
            str_json = str_json.replace('%{0}%'.format(k), v)

        def evaluate(match):
            return str(eval(match.group(1)))

        str_json = sub(
                '\"\%\s*((\d+\s*[-+]?\s*)+)\%\"', partial(evaluate), str_json)

        return loads(str_json)

    @format_elasticsearch_response
    def output(self, data, **params):
        return data
