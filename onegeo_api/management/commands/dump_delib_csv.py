# Copyright (c) 2017-2018 Neogeo-Technologies.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from collections import OrderedDict
import csv
import datetime
import dateutil
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from functools import reduce
from onegeo_api.elastic import elastic_conn
from onegeo_api.models import IndexProfile
import urllib.parse


LOCATIONS = settings.DUMPING_CSV.pop('LOCATIONS')
FILENAME = settings.DUMPING_CSV.pop('FILENAME')
BASE_URL = settings.DUMPING_CSV.pop('BASE_URL')

NOW = dateutil.parser.parse(datetime.datetime.now(timezone.utc).isoformat())


class Command(BaseCommand):

    help = 'Update indexes'

    def handle(self, *args, **kwargs):

        with open(FILENAME, 'w') as f:
            writer = csv.writer(f, delimiter=';')

            columns = (
                'COLL_NOM', 'COLL_SIRET', 'COLL_COMMUNE',
                'DELIB_ID', 'DELIB_DATE', 'DELIB_OBJET',
                'BUDGET_ANNEE', 'PREF_ID', 'DELIB_URL')
            writer.writerows([columns])

            for location in LOCATIONS:
                instance = IndexProfile.get_by_location(location)
                if not instance:
                    continue

                index = str(instance.alias.uuid)

                docs = elastic_conn.get_all_documents(
                    elastic_conn.get_indices_by_alias(index, unique=True),
                    _source=['lineage', 'properties'])

                for doc in docs:
                    doc = doc['_source']
                    data = OrderedDict.fromkeys(columns, None)

                    lineage = doc.get('lineage')
                    properties = doc.get('properties')
                    if not properties:
                        continue

                    if 'date_seance' in properties:
                        try:
                            date_now = dateutil.parser.parse(
                                properties['date_seance'], dayfirst=True)
                        except Exception:
                            print('Error format date', properties['date_seance'])
                            continue
                    else:
                        continue

                    data['BUDGET_ANNEE'] = str(date_now.year)
                    data['DELIB_DATE'] = '{}-{}-{}'.format(
                        str(date_now.year),
                        str(date_now.month).zfill(2),
                        str(date_now.day).zfill(2))
                    data['DELIB_OBJET'] = properties.get('titre')
                    data['DELIB_ID'] = properties.get('numero_seance')
                    data['DELIB_URL'] = reduce(
                        urllib.parse.urljoin, [
                            BASE_URL.endswith('/') and BASE_URL or '{}/'.format(BASE_URL),
                            '{}/'.format(lineage['source']['uri'].split('/')[-1]),
                            '{}/'.format(lineage['resource']['name']),
                            lineage['filename']])
                    data['COLL_COMMUNE'] = properties.get('communes', "").replace(',', ' / ')
                    data['COLL_NOM'] = 'Métropole de Lyon'
                    data['COLL_SIRET'] = '20004697700019'
                    data['PREF_ID'] = 'Préfecture du Rhône'

                    writer.writerows([data.values()])
