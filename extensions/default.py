from . import AbstractPlugin
from django.http import JsonResponse


"""
{
    "from": "%from%",
    "size": "%size%",
    "query": {
        "multi_match": {
            "fields": [
                "properties.*"
            ],
            "query": "%text%",
            "operator": "or",
            "fuzziness": 0.7
        }
    },
    "highlight": {
        "fields": {
            "properties.*": {
                "type": "plain",
                "pre_tags": [
                    "<strong>"
                ],
                "post_tags": [
                    "</strong>"
                ]
            }
        },
        "require_field_match": false
    },
    "aggregations": {
        "resource": {
            "terms": {
                "size": 999,
                "field": "origin.resource.name"
            }
        },
        "source": {
            "terms": {
                "size": 999,
                "field": "origin.source.name"
            }
        }
    }
}
"""


class Plugin(AbstractPlugin):

    def input(self, config, **params):
        return super().input(config, **params)

    def output(self, data, **params):
        return JsonResponse(super().output(data, **params))


plugin = Plugin
