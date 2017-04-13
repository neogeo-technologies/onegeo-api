from ..elasticsearch_wrapper import elastic_conn
from . import AbstractPlugin
from django.http import HttpResponse
from neogeo_xml_utils import ObjToXML
from urllib.parse import urlparse, parse_qsl
from datetime import datetime


"""
{
    "size": 0,
    "from": 0,
    "query": {
        "bool": {
            "should": [
                {
                    "multi_match": {
                        "query": "%any%",
                        "operator": "or",
                        "fuzziness": 0.7,
                        "fields": [
                            "data.properties.*"
                        ]
                    }
                }
            ]
        }
    },
    "aggregations": {
        "metadata": {
            "terms": {
                "size": 999,
                "field": "origin.resource.metadata_url"
            }
        }
    }
}
"""


def format_parameter(dct, key, typ):
    try:
        return typ(dct[key])
    except:
        pass


class Plugin(AbstractPlugin):

    FROMTO = (0, 10)
    INDEX = 'geonet'

    def __init__(self):
        super().__init__()

        self._fast = False
        self._type = None

        self._from = self.FROMTO[0]
        self._to = self.FROMTO[1]

        self._summary = {'categories': {'category': []},
                         'createDateYears': {'createDateYear': []},
                         'denominators': {'denominator': []},
                         'formats': {'format': []},
                         'inspireThemes': {'inspireTheme': []},
                         'inspireThemesWithAc': {'inspireThemeWithAc': []},
                         'keywords': {'keyword': []},
                         'licence': {'useLimitation': []},
                         'maintenanceAndUpdateFrequencies': {
                                'maintenanceAndUpdateFrequency': []},
                         'orgNames': {'orgName': []},
                         'resolutions': {'resolution': []},
                         'serviceTypes': {'serviceType': []},
                         'spatialRepresentationTypes': {
                             'spatialRepresentationType': []},
                         'status': {'status': []},
                         'types': {'type': []}}

    def update_summary(self, parent, key, value):
        for d in self._summary[parent][key]:
            if d['@name'] == value:
                # Ugly...
                d['@count'] = int(d['@count'])
                d['@count'] += 1
                d['@count'] = str(d['@count'])
                break
        self._summary[parent][key].append({'@name': value, '@count': '1'})

    def input(self, config, **params):

        if 'fast' in params:
            self.__fast = (params['fast'] == 'true')

        self._type = format_parameter(params, 'type', str) or None

        self._from = format_parameter(params, 'from', int)
        self._to = format_parameter(params, 'to', int)

        if self._from > self._to:
            self._from = self.FROMTO[0]
            self._to = self.FROMTO[1]
        return super().input(config, **params)

    def output(self, data):

        count = 0
        metadata = []

        for i, bucket in enumerate(data['aggregations']['metadata']['buckets']):

            if i < self._from:
                continue
            if i > self._to:
                break
            count += 1

            body = {'_source': ['data'],
                    'query': {
                        'match': {
                            'uuid': dict(parse_qsl(urlparse(
                                                bucket['key']).query))['ID']}}}

            res = elastic_conn.search(index=self.INDEX, body=body)

            if len(res['hits']['hits']) == 0:  # La fiche n'existe pas ?
                continue

            if len(res['hits']['hits']) > 1:  # ce cas ne devrait pas exister !
                raise Exception('TODO')  # TODO

            data = res['hits']['hits'][0]['_source']['data']
            if self.__fast:
                metadata.append({'info': data['info']})
            else:
                metadata.append(data)

            # Puis m-à-j des éléments de <summary> lorsque cela est possible :

            # categories/category
            for val in data['info']['category']:
                if isinstance(val, str):
                    self.update_summary('categories', 'category', val)
                if isinstance(val, dict):
                    pass  # TODO

            # createDateYears/createDateYear
            val = data['info']['createDate']
            date = datetime.strptime(val, "%Y-%m-%dT%H:%M:%S")
            self.update_summary(
                        'createDateYears', 'createDateYear', str(date.year))

            # denominators/denominator
            # TODO

            # formats/format
            # TODO

            # inspireThemes/inspireTheme
            # TODO

            # inspireThemesWithAc/inspireThemeWithAc
            # TODO

            # keywords/keyword
            for val in data['keyword']:
                self.update_summary('keywords', 'keyword', val)

            # licence/useLimitation
            # TODO

            # maintenanceAndUpdateFrequencies/maintenanceAndUpdateFrequency
            # TODO

            # orgNames/orgName
            # TODO

            # resolutions/resolution
            # TODO

            # serviceTypes/serviceType
            # TODO

            # spatialRepresentationTypes/spatialRepresentationType
            # TODO

            # status/status
            # TODO

            # types/type
            # TODO


        self._summary['@count'] = str(count)

        data = {'response': {'@from': str(self._from),
                             '@to': str(self._from + count),
                             'summary': self._summary, 'metadata': metadata}}

        return HttpResponse(ObjToXML(data).tostring(),
                            content_type='application/xml')


plugin = Plugin
