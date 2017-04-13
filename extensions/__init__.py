from abc import ABCMeta, abstractmethod
from functools import partial
from json import dumps, loads
from re import sub


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

    @abstractmethod
    def output(self, *args, **kwargs):
        raise NotImplementedError('This is an abstract method. '
                                  "You can't do anything with it.")

