from . import AbstractPlugin
from django.http import JsonResponse


"""
{
    "from": "%from%",
    "size": "%size%",
    "query": {
        "bool": {
            "must": {
                "match": {
                    "attachment.content": {
                        "query": "%txt%",
                        "minimum_should_match": "75%",
                        "fuzziness": "auto"
                    }
                }
            },
            "filter": [],
            "should": {
                "match_phrase": {
                    "attachment.content": {
                        "query": "%txt%",
                        "slop": 6
                    }
                }
            }
        }
    },
    "highlight": {
        "require_field_match": false,
        "fields": {
            "attachment.content": {
                "type": "plain",
                "pre_tags": [
                    "<strong>"
                ],
                "post_tags": [
                    "</strong>"
                ]
            },
            "meta.*": {
                "type": "plain",
                "pre_tags": [
                    "<strong>"
                ],
                "post_tags": [
                    "</strong>"
                ]
            }
        }
    }
}
"""


class Plugin(AbstractPlugin):

    def input(self, config, **params):
        return super().input(config, **params)

    def output(self, data):
        return JsonResponse(data)


plugin = Plugin
