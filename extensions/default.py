from . import AbstractPlugin
from django.http import JsonResponse


class Plugin(AbstractPlugin):

    def input(self, config, **params):
        return super().input(config, **params)

    def output(self, data):
        return JsonResponse(data)


plugin = Plugin
