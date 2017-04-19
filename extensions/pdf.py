from . import AbstractPlugin
from ..utils import clean_my_obj
from django.http import JsonResponse


"""
{
    "from": "%from%",
    "size": "%size%",
    "query": {
        "bool": {
            "should": {
                "match_phrase": {
                    "attachment.content": {
                        "slop": 6,
                        "query": "%text%"
                    }
                }
            },
            "filter": [],
            "must": {
                "match": {
                    "attachment.content": {
                        "fuzziness": "auto",
                        "minimum_should_match": "75%",
                        "query": "%text%"
                    }
                }
            }
        }
    },
    "highlight": {
        "fields": {
            "properties.*": {
                "pre_tags": [
                    "<strong>"
                ],
                "post_tags": [
                    "</strong>"
                ],
                "type": "plain"
            },
            "attachment.content": {
                "pre_tags": [
                    "<strong>"
                ],
                "post_tags": [
                    "</strong>"
                ],
                "type": "plain"
            }
        },
        "require_field_match": false
    },
    "_source": [
        "properties",
        "origin"
    ]
}
"""


class Plugin(AbstractPlugin):

    def input(self, config, **params):
        return super().input(config, **params)

    def output(self, data, **params):
        return JsonResponse(clean_my_obj(super().output(data, **params)))


plugin = Plugin
